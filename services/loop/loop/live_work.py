"""Live work board — discrete receipts that pile into columns (not a black-box log).

Columns are derived from active room workflows + artifact types — not a fixed five-step strip.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loop.store import Store
from loop.workflow import (
    LIVE_LABEL,
    LIVE_ORDER,
    live_columns_from_workflows,
    to_live_column,
    workflow_from_store,
)

# Back-compat for tests that still import the old constant.
LIVE_COLUMNS = list(LIVE_ORDER)
LIVE_LABELS = dict(LIVE_LABEL)

# artifact_type → fine node (then collapsed via to_live_column)
_ARTIFACT_NODE: dict[str, str] = {
    "signal": "signal",
    "voice": "customer",
    "contact": "customer",
    "contact_lookup": "customer",
    "mail_outreach": "customer",
    "mail_reply": "customer",
    "user_cluster": "customer",
    "call": "customer",
    "call_feedback": "customer",
    "call_transcript": "customer",
    "call_evidence": "customer",
    "evidence": "evidence",
    "evidence_pack": "evidence",
    "analytics": "evidence",
    "warehouse": "evidence",
    "bq": "evidence",
    "metric": "evidence",
    "hypothesis": "evidence",
    "classification": "evidence",
    "voice_context": "evidence",
    "code": "code",
    "code_brief": "code",
    "pr": "code",
    "patch": "code",
    "product": "product",
    "experiment": "experiment",
    "prd": "product",
    "risk_decision": "risk",
    "approval": "approve",
    "coordination": "coordinate",
    "mail": "verify",
    "gmail": "verify",
    "verify": "verify",
    "learning": "learn",
    "outcome": "verify",
}

_BADGE: dict[str, str] = {
    "signal": "Found",
    "voice": "Voice",
    "contact": "Contact",
    "evidence": "Queried",
    "evidence_pack": "Packed",
    "warehouse": "BigQuery",
    "bq": "BigQuery",
    "analytics": "Queried",
    "hypothesis": "Claim",
    "contact_lookup": "Lookup",
    "code": "Patch",
    "code_brief": "Brief",
    "pr": "PR open",
    "patch": "Patch",
    "product": "Proposal",
    "experiment": "Experiment",
    "risk_decision": "Risk",
    "approval": "Waiting",
    "coordination": "Notify",
    "call": "Calling",
    "call_feedback": "Feedback",
    "call_transcript": "Call",
    "mail": "Mail sent",
    "gmail": "Mail sent",
    "verify": "Verified",
    "learning": "Lesson",
}


def column_for_artifact(artifact_type: str | None, *, stage: str = "", awaiting: bool = False) -> str | None:
    if awaiting:
        return "approve"
    if artifact_type and artifact_type in _ARTIFACT_NODE:
        return to_live_column(_ARTIFACT_NODE[artifact_type])
    if stage:
        return to_live_column(stage)
    return None


def _links_from_artifact(art: dict[str, Any]) -> dict[str, str | None]:
    pr = art.get("pr_url") if isinstance(art.get("pr_url"), str) else None
    if not pr and isinstance(art.get("url"), str) and "github.com" in art["url"]:
        pr = art["url"]
    if not pr and isinstance(art.get("report"), dict):
        url = art["report"].get("url")
        conn = str(art["report"].get("connector") or "")
        if isinstance(url, str) and ("github" in conn or "github.com" in url):
            pr = url
    gmail = art.get("gmail_url") if isinstance(art.get("gmail_url"), str) else None
    if not gmail and isinstance(art.get("report"), dict):
        rep = art["report"]
        conn = str(rep.get("connector") or "")
        url = rep.get("url")
        if isinstance(url, str) and ("mail" in conn or "gmail" in conn or "mail.google" in url):
            gmail = url
    calendar = None
    meet = None
    slot = art.get("slot") if isinstance(art.get("slot"), dict) else {}
    if slot.get("event_url"):
        url = str(slot["event_url"])
        if "meet.google" in url:
            meet = url
        else:
            calendar = url
    bq = art.get("bq_url") or art.get("console_url")
    return {
        "pr_url": pr,
        "gmail_url": gmail,
        "calendar_url": calendar,
        "meet_url": meet,
        "bq_url": bq if isinstance(bq, str) else None,
    }


def card_from_message(
    msg: Any,
    *,
    room_title: str = "",
    tenant_product: str | None = None,
) -> dict[str, Any] | None:
    art_type = msg.artifact_type or (msg.kind if msg.kind != "chat" else None)
    # Skip pure chatter unless it's a contact lookup / feedback chat with typed artifact
    if msg.kind == "chat" and art_type not in {
        "contact",
        "contact_lookup",
        "call_feedback",
        "warehouse",
        "mail",
        "gmail",
    }:
        if not art_type:
            return None
    col = column_for_artifact(art_type)
    if not col:
        return None
    art = msg.artifact if isinstance(msg.artifact, dict) else {}
    links = _links_from_artifact(art)
    # PR artifacts often stash url on report
    if art_type in {"pr", "code", "code_brief"} and not links["pr_url"]:
        for key in ("url", "pr_url", "html_url"):
            if isinstance(art.get(key), str) and "github.com" in art[key]:
                links["pr_url"] = art[key]
                break
        exe = art.get("execution") if isinstance(art.get("execution"), dict) else {}
        if exe.get("pr_url"):
            links["pr_url"] = str(exe["pr_url"])
    phone = None
    for key in ("phone", "callback_phone", "to_number"):
        if isinstance(art.get(key), str) and art[key].strip():
            phone = art[key].strip()
            break
    badge = _BADGE.get(art_type or "", LIVE_LABELS.get(col, col))
    if links["pr_url"]:
        badge = "PR open"
        col = "code"
    if art_type in {"mail", "gmail"} or (isinstance(art.get("channel"), str) and "gmail" in art["channel"]):
        if art.get("report", {}).get("status") == "applied" if isinstance(art.get("report"), dict) else False:
            badge = "Mail sent"
            col = "verify"
        elif links["gmail_url"]:
            badge = "Draft" if "draft" in str(art.get("channel") or "") else "Mail"
    text = (msg.text or "").strip()
    if not text:
        return None
    created = msg.created_at
    if hasattr(created, "isoformat"):
        created_s = created.isoformat()
    else:
        created_s = str(created)
    return {
        "id": msg.id,
        "column": col,
        "badge": badge,
        "text": text[:180],
        "agent": msg.author,
        "room_id": msg.room_id,
        "room_title": room_title,
        "tenant_product": tenant_product,
        "artifact_type": art_type,
        "phone": phone,
        "metric": art.get("metric"),
        "source": art.get("source") or art.get("connector"),
        "created_at": created_s,
        "proof": art.get("proof") if isinstance(art.get("proof"), dict) else None,
        **links,
    }


def card_from_action(action: Any, *, room_id: str, room_title: str = "") -> dict[str, Any] | None:
    if action.status not in {"proposed", "awaiting_approval"}:
        return None
    arts = action.artifacts or {}
    exe = arts.get("execution") if isinstance(arts.get("execution"), dict) else {}
    pr = exe.get("pr_url") or exe.get("code_pr_url")
    text = (
        getattr(action, "consequence", None)
        or getattr(action, "tier_rationale", None)
        or f"{getattr(action, 'type', 'change')} waiting for approval"
    )
    return {
        "id": f"action:{action.id}",
        "column": "approve",
        "badge": "Waiting",
        "text": str(text)[:180],
        "agent": "risk_agent",
        "room_id": room_id,
        "room_title": room_title,
        "tenant_product": None,
        "artifact_type": "approval",
        "phone": None,
        "metric": None,
        "source": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pr_url": pr,
        "gmail_url": None,
        "calendar_url": None,
        "meet_url": None,
        "bq_url": None,
        "action_id": action.id,
    }


def build_live_work(store: Store, *, limit: int = 80) -> dict[str, Any]:
    """Pile work receipts into columns derived from active room workflows."""
    cards: list[dict[str, Any]] = []
    workflows: list[dict[str, Any]] = []
    for room in store.list_rooms():
        if room.status != "open":
            continue
        inv = store.get_investigation(room.investigation_id) if room.investigation_id else None
        workflows.append(workflow_from_store(store, room, inv))
        tenant = store.get_tenant(room.tenant_id) if room.tenant_id else None
        product = tenant.product if tenant else None
        for msg in store.list_messages(room.id):
            card = card_from_message(msg, room_title=room.title, tenant_product=product)
            if card:
                cards.append(card)
        if room.investigation_id:
            from loop.room_ui import visible_pending_actions

            for act in visible_pending_actions(store, room.investigation_id):
                ac = card_from_action(act, room_id=room.id, room_title=room.title)
                if ac:
                    cards.append(ac)

    def _key(c: dict[str, Any]) -> str:
        return str(c.get("created_at") or "")

    cards.sort(key=_key, reverse=True)
    cards = cards[:limit]

    columns = live_columns_from_workflows(workflows, card_columns=[c["column"] for c in cards])
    by_col: dict[str, int] = {c["id"]: 0 for c in columns}
    for c in cards:
        col = c["column"]
        if col not in by_col:
            by_col[col] = 0
            columns.append({"id": col, "label": LIVE_LABELS.get(col, col.title()), "count": 0})
        by_col[col] = by_col.get(col, 0) + 1
    for col in columns:
        col["count"] = by_col.get(col["id"], 0)

    return {
        "columns": columns,
        "cards": cards,
        "stats": {
            "total": len(cards),
            "evidence": by_col.get("evidence", 0),
            "customer": by_col.get("customer", 0),
            "code": by_col.get("code", 0),
            "experiment": by_col.get("experiment", 0),
            "approve": by_col.get("approve", 0),
            "verify": by_col.get("verify", 0),
            "with_pr": sum(1 for c in cards if c.get("pr_url")),
            "with_mail": sum(1 for c in cards if c.get("gmail_url")),
            "with_phone": sum(1 for c in cards if c.get("phone")),
        },
    }


def publish_work_card(card: dict[str, Any], *, room_id: str = "") -> None:
    """Push a work receipt to WS clients so the board fills without refresh."""
    try:
        from loop.live import HUB

        event = {"type": "work_card", "card": card}
        HUB.publish_global(event)
        rid = room_id or card.get("room_id") or ""
        if rid:
            HUB.publish(rid, event)
    except Exception:
        pass


def emit_work_from_message(msg: Any, *, room_title: str = "", tenant_product: str | None = None) -> dict[str, Any] | None:
    card = card_from_message(msg, room_title=room_title, tenant_product=tenant_product)
    if card:
        publish_work_card(card, room_id=msg.room_id)
    return card
