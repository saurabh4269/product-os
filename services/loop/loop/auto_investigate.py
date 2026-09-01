"""Close the loop: ambient signal detect → investigate → propose without human ingest."""

from __future__ import annotations

from typing import Any

from .models import InvestigationState, SignalStatus


def tenant_id_from_signal(signal: Any) -> str | None:
    src = str(getattr(signal, "source", "") or "")
    if src.startswith("tenant."):
        return src.split(".", 1)[1] or None
    for seg in getattr(signal, "affected_segments", []) or []:
        ch = getattr(seg, "channel", None) or (seg.get("channel") if isinstance(seg, dict) else None)
        if ch and str(ch).startswith("tenant."):
            return str(ch).split(".", 1)[1] or None
    return None


def signal_has_open_investigation(engine: Any, signal_id: str) -> bool:
    terminal = {
        InvestigationState.RESOLVED,
        InvestigationState.NOT_RESOLVED,
        InvestigationState.INCONCLUSIVE,
        InvestigationState.PARTIALLY_RESOLVED,
    }
    for inv in engine.store.list_investigations():
        if signal_id not in inv.originating_signal_ids:
            continue
        if inv.state not in terminal:
            return True
    return False


def auto_investigate_signal(engine: Any, signal_id: str) -> dict[str, Any]:
    """Run the full deterministic pipeline for one new signal."""
    from .audit import record
    from .engine import SAFARI
    from .runtime_mode import is_eval_mode

    sig = engine.store.get_signal(signal_id)
    if not sig:
        return {"signal_id": signal_id, "status": "skipped", "reason": "missing"}
    if sig.status == SignalStatus.SUPPRESSED:
        return {"signal_id": signal_id, "status": "skipped", "reason": "suppressed"}
    if signal_has_open_investigation(engine, signal_id):
        return {"signal_id": signal_id, "status": "skipped", "reason": "already_investigating"}

    tenant_id = tenant_id_from_signal(sig)
    inv = engine.open_investigation(sig, tenant_id=tenant_id)
    if not inv:
        return {"signal_id": signal_id, "status": "skipped", "reason": "open_blocked"}

    engine.gather_evidence(inv)
    hyp = engine.form_hypothesis(inv)
    if not hyp:
        record(
            engine.store,
            actor="signal_agent",
            action="auto_investigate.gate_failed",
            resource=f"signal:{signal_id}",
            detail={"investigation_id": inv.id},
        )
        return {
            "signal_id": signal_id,
            "status": "failed",
            "reason": "three_source_gate",
            "investigation_id": inv.id,
        }

    if is_eval_mode() and any(seg.browser == SAFARI for seg in sig.affected_segments) and "purchase" in (sig.metric or ""):
        inv.scenario_id = inv.scenario_id or "safari_3ds"
        engine.store.put_investigation(inv)

    action = engine.propose_action(inv, hyp)
    low_exec = engine.auto_execute_low_tier(action)

    if is_eval_mode() and inv.scenario_id == "safari_3ds":
        from .world import publish_safari_room

        publish_safari_room(engine, inv)

    record(
        engine.store,
        actor="signal_agent",
        action="auto_investigate.completed",
        resource=f"investigation:{inv.id}",
        detail={
            "signal_id": signal_id,
            "action_id": action.id,
            "risk_tier": action.risk_tier.value,
            "low_auto_executed": low_exec,
        },
    )
    return {
        "signal_id": signal_id,
        "status": "applied",
        "investigation_id": inv.id,
        "action_id": action.id,
        "awaiting_approval": action.status == "awaiting_approval",
        "low_auto_executed": low_exec,
    }


def auto_investigate_new_signals(engine: Any, signal_ids: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sid in sorted(signal_ids):
        try:
            results.append(auto_investigate_signal(engine, sid))
        except Exception as exc:
            from .audit import record

            record(
                engine.store,
                actor="signal_agent",
                action="auto_investigate.error",
                resource=f"signal:{sid}",
                detail={"error": str(exc)[:240]},
            )
            results.append({"signal_id": sid, "status": "error", "error": str(exc)[:240]})
    return results
