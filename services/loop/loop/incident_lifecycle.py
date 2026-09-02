"""Tenant-scoped incident lifecycle — poll real store state, no fixture scripts."""

from __future__ import annotations

from typing import Any

from .models import InvestigationState
from .tenant import Tenant, flag_key

CHECKOUT_METRIC = "checkout_conversion"
REGRESSION_FLAG = "pay_sdk_4_3"

_TERMINAL_INVESTIGATION = {
    InvestigationState.RESOLVED,
    InvestigationState.NOT_RESOLVED,
    InvestigationState.INCONCLUSIVE,
    InvestigationState.PARTIALLY_RESOLVED,
}


def publish_incident_lifecycle(
    engine: Any,
    tenant_id: str,
    *,
    metric: str = CHECKOUT_METRIC,
) -> dict[str, Any] | None:
    """Push lifecycle snapshot to the campus WebSocket (Connect incident panel)."""
    store = engine.store
    if not store.get_tenant(tenant_id):
        return None
    payload = incident_lifecycle(engine, tenant_id, metric=metric)
    try:
        from .live import HUB

        HUB.publish_global(
            {
                "type": "incident_lifecycle",
                "tenant_id": tenant_id,
                "metric": metric,
                "lifecycle": payload,
            }
        )
    except Exception:
        pass
    return payload


def _scenario(tenant_id: str, metric: str = CHECKOUT_METRIC) -> str:
    return f"t:{tenant_id}:{metric}"


def _tenant_flags(store: Any, tenant: Tenant) -> dict[str, str]:
    raw = store.list_flags() if hasattr(store, "list_flags") else {}
    out: dict[str, str] = {}
    prefix = f"t:{tenant.id}:"
    for key, val in raw.items():
        if key.startswith(prefix):
            out[key.split(":", 2)[-1]] = str(val)
    for name in tenant.flag_names or []:
        out.setdefault(name, str(raw.get(flag_key(tenant.id, name), raw.get(name, ""))))
    return out


def _find_room(store: Any, tenant_id: str, metric: str = CHECKOUT_METRIC):
    scenario = _scenario(tenant_id, metric)
    rooms = [r for r in store.list_rooms() if r.tenant_id == tenant_id or r.scenario_id == scenario]
    open_rooms = [r for r in rooms if r.status == "open" and r.scenario_id == scenario]
    if open_rooms:
        return sorted(open_rooms, key=lambda r: r.created_at, reverse=True)[0]
    if rooms:
        return sorted(rooms, key=lambda r: r.created_at, reverse=True)[0]
    return None


def _pending_action(store: Any, inv_id: str | None):
    if not inv_id:
        return None
    for act in store.list_actions(inv_id):
        if act.status in {"proposed", "awaiting_approval"}:
            return act
    return None


def _execution(store: Any, inv_id: str | None) -> dict[str, Any]:
    if not inv_id:
        return {}
    for act in store.list_actions(inv_id):
        if act.status not in {"executed", "approved"}:
            continue
        art = act.artifacts or {}
        exe = art.get("execution") if isinstance(art.get("execution"), dict) else {}
        if exe or art.get("flag"):
            return {
                "action_id": act.id,
                "status": act.status,
                "flag": art.get("flag"),
                "from": art.get("from"),
                "to": art.get("to"),
                "pr_url": (exe or {}).get("pr_url") or (exe or {}).get("code_pr_url"),
                "execution": exe,
            }
    return {}


def sync_regression_from_product(engine: Any, tenant_id: str) -> dict[str, Any]:
    """Observe Product Y flag state — default pay-sdk 4.3 ON when unset (matches Cove config/flags.json)."""
    from .engine import idempotency_key

    store = engine.store
    tenant = store.get_tenant(tenant_id)
    if not tenant or not (tenant.deploy_url or "").strip():
        return {"status": "skipped", "detail": "no deploy URL"}
    names = tenant.flag_names or [REGRESSION_FLAG]
    if REGRESSION_FLAG not in names and names:
        name = names[0]
    else:
        name = REGRESSION_FLAG
    scoped = store.get_flag(flag_key(tenant_id, name))
    if scoped is not None:
        return {"status": "observed", "tenant_id": tenant_id, "flag": name, "value": scoped}
    key = idempotency_key("incident", f"sync:{tenant_id}:{name}", "v1")
    store.set_flag(flag_key(tenant_id, name), "on", key)
    store.set_flag(name, "on", key + ":global")
    return {"status": "synced", "tenant_id": tenant_id, "flag": name, "value": "on"}


def arm_checkout_regression(engine: Any, tenant_id: str) -> dict[str, Any]:
    """Admin reset — re-enable pay-sdk 4.3 on Product Y for another checkout repro."""
    from .engine import idempotency_key

    store = engine.store
    tenant = store.get_tenant(tenant_id)
    if not tenant:
        return {"status": "missing", "detail": "tenant not found"}
    name = REGRESSION_FLAG if REGRESSION_FLAG in (tenant.flag_names or [REGRESSION_FLAG]) else (tenant.flag_names[0] if tenant.flag_names else REGRESSION_FLAG)
    key = idempotency_key("incident", f"arm:{tenant_id}:{name}", "v1")
    store.set_flag(flag_key(tenant_id, name), "on", key)
    store.set_flag(name, "on", key + ":global")
    return {"status": "applied", "tenant_id": tenant_id, "flag": name, "value": "on"}


def _diagnosis_detail(inv: Any | None, *, investigating: bool) -> str:
    if not inv:
        return "Waiting for checkout signal"
    state = getattr(inv.state, "value", inv.state)
    if investigating:
        labels = {
            "OPEN": "Product OS opened an investigation room",
            "GATHERING": "Gathering evidence from warehouse and connectors",
            "HYPOTHESIS": "Testing hypotheses against the signal",
            "ACTION_PROPOSED": "Drafting proposed rollback and PR",
        }
        return labels.get(str(state), f"Diagnosing · {state}")
    return str(state)


def _incident_phase(
    *,
    regression_on: bool,
    triggered: bool,
    investigating: bool,
    awaiting: bool,
    executed: dict,
    verified: bool,
    flag_after: bool,
    inv: Any | None,
) -> tuple[str, str, str, str]:
    """Return phase, headline, subtitle, product_status."""
    if verified or (flag_after and not regression_on):
        return (
            "recovered",
            "Checkout recovered",
            "Product OS measured recovery and wrote a lesson.",
            "healthy",
        )
    if executed:
        return (
            "verifying",
            "Rollback applied",
            "Measuring whether checkout conversion recovered.",
            "recovering",
        )
    if awaiting:
        return (
            "awaiting_approval",
            "Diagnosis complete — your call",
            "Review evidence in the room, then approve the proposed fix.",
            "degraded",
        )
    if investigating and inv:
        return (
            "diagnosing",
            "Product OS is diagnosing",
            _diagnosis_detail(inv, investigating=True),
            "degraded",
        )
    if triggered:
        return (
            "signal_received",
            "Signal received from Product Y",
            "Product OS is opening the investigation pipeline.",
            "degraded",
        )
    if regression_on:
        return (
            "degraded",
            "Checkout failing on Product Y",
            "pay-sdk 4.3 is live — payment authorization times out after Pay now.",
            "degraded",
        )
    return (
        "idle",
        "Checkout stable",
        "No active regression on Product Y.",
        "healthy",
    )


def incident_lifecycle(
    engine: Any,
    tenant_id: str,
    *,
    metric: str = CHECKOUT_METRIC,
) -> dict[str, Any]:
    """Describe one checkout-regression incident end-to-end from live store rows."""
    sync_regression_from_product(engine, tenant_id)
    store = engine.store
    tenant = store.get_tenant(tenant_id)
    if not tenant:
        return {"status": "missing", "detail": "tenant not found", "steps": []}

    flags = _tenant_flags(store, tenant)
    regression_on = flags.get(REGRESSION_FLAG, "").lower() == "on"
    room = _find_room(store, tenant_id, metric)
    inv = store.get_investigation(room.investigation_id) if room and room.investigation_id else None
    pending = _pending_action(store, inv.id if inv else None)
    executed = _execution(store, inv.id if inv else None)
    flag_after = flags.get(REGRESSION_FLAG, "").lower() == "off"
    outcomes = [o for o in store.list_outcomes() if o.investigation_id == inv.id] if inv and hasattr(store, "list_outcomes") else []
    verified = bool(outcomes) or (
        inv is not None
        and inv.state
        in {
            InvestigationState.RESOLVED,
            InvestigationState.PARTIALLY_RESOLVED,
            InvestigationState.NOT_RESOLVED,
            InvestigationState.INCONCLUSIVE,
        }
    )

    triggered = bool(
        tenant.last_ingest_at
        and (
            room is not None
            or any(
                inv2.tenant_id == tenant_id and metric in (inv2.title or "")
                for inv2 in store.list_investigations()
            )
        )
    )
    investigating = inv is not None and inv.state in {
        InvestigationState.OPEN,
        InvestigationState.GATHERING,
        InvestigationState.HYPOTHESIS,
        InvestigationState.ACTION_PROPOSED,
    }
    investigation_done = inv is not None and not investigating
    awaiting = inv is not None and inv.state == InvestigationState.AWAITING_APPROVAL and pending is not None

    deploy = (tenant.deploy_url or "").rstrip("/")
    checkout_url = f"{deploy}/checkout" if deploy else None
    sdk_label = flags.get("pay_sdk") or ("4.3.0" if regression_on else "4.2.x")
    phase, headline, subtitle, product_status = _incident_phase(
        regression_on=regression_on,
        triggered=triggered,
        investigating=investigating,
        awaiting=awaiting,
        executed=executed,
        verified=verified,
        flag_after=flag_after,
        inv=inv,
    )

    steps = [
        {
            "id": "degraded",
            "label": "Checkout degraded on Product Y",
            "detail": f"pay-sdk {sdk_label} · authorization times out at payment",
            "done": regression_on or triggered,
            "active": phase == "degraded",
            "href": checkout_url,
        },
        {
            "id": "trigger",
            "label": "Shopper hits hang · signal ingested",
            "detail": tenant.last_ingest_at or "Reproduce at checkout — Pay now with items in cart",
            "done": triggered,
            "active": phase == "signal_received",
            "href": checkout_url,
        },
        {
            "id": "investigate",
            "label": "Product OS diagnoses",
            "detail": _diagnosis_detail(inv, investigating=investigating),
            "done": investigation_done,
            "active": phase == "diagnosing",
            "href": f"/rooms/{room.id}" if room else None,
            "room_id": room.id if room else None,
        },
        {
            "id": "approve",
            "label": "You approve the proposed fix",
            "detail": pending.risk_tier.value if pending and hasattr(pending.risk_tier, "value") else ("Review in Approvals" if awaiting else "—"),
            "done": executed != {} or inv is not None and inv.state == InvestigationState.APPROVED,
            "active": phase == "awaiting_approval",
            "href": pending and f"/approvals?focus={pending.id}" or "/approvals",
            "action_id": pending.id if pending else None,
        },
        {
            "id": "execute",
            "label": "Rollback applied · PR opened (no merge)",
            "detail": executed.get("pr_url") or executed.get("flag") or "Pending approval",
            "done": bool(executed) or flag_after,
            "active": phase == "verifying" and bool(executed),
            "href": executed.get("pr_url"),
        },
        {
            "id": "verify",
            "label": "Recovery measured · lesson written",
            "detail": outcomes[0].verdict.value if outcomes and hasattr(outcomes[0].verdict, "value") else (str(getattr(inv.state, "value", "")) if inv else "—"),
            "done": verified,
            "active": phase == "verifying" and not verified,
            "href": f"/rooms/{room.id}" if room else None,
        },
    ]

    done_count = sum(1 for s in steps if s["done"])
    out = {
        "status": "ok",
        "tenant_id": tenant_id,
        "metric": metric,
        "scenario_id": _scenario(tenant_id, metric),
        "regression_flag": REGRESSION_FLAG,
        "flags": flags,
        "deploy_url": deploy or None,
        "checkout_url": checkout_url,
        "room_id": room.id if room else None,
        "investigation_id": inv.id if inv else None,
        "investigation_state": getattr(inv.state, "value", inv.state) if inv else None,
        "pending_action_id": pending.id if pending else None,
        "execution": executed or None,
        "steps": steps,
        "progress": {"done": done_count, "total": len(steps)},
        "ready_for_checkout": bool(deploy),
        "pay_sdk_active": sdk_label,
        "regression_active": regression_on,
        "phase": phase,
        "headline": headline,
        "subtitle": subtitle,
        "product_status": product_status,
        "last_ingest_at": tenant.last_ingest_at or None,
    }
    return out
