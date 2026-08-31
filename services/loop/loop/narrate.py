"""Turn agent work into natural group-chat lines for Traces.

Tone: short, like colleagues in a chat — not status reports.
"""

from __future__ import annotations

from typing import Any

_TOPICS: dict[str, str] = {
    "analytics": "the numbers",
    "logs": "the logs",
    "deploy": "what shipped",
    "deployment": "what shipped",
    "database": "the db",
    "customer": "customers",
    "code": "the code",
    "security": "policy",
    "learning": "the metric",
    "risk": "risk",
    "product": "a proposal",
    "feedback": "the customer",
    "coordination": "a review slot",
    "investigator": "the specialists",
    "signal": "this signal",
    "evidence": "evidence",
    "root_cause": "root cause",
    "test": "a quick test",
    "voice": "the call",
    "customer_voice": "customer notes",
}

_ASK: dict[str, str] = {
    "analytics": "can you pull the numbers?",
    "logs": "can you check the logs?",
    "deploy": "what shipped around then?",
    "deployment": "what shipped around then?",
    "database": "anything weird in the db?",
    "customer": "what are customers saying?",
    "customer_voice": "got customer notes?",
    "code": "can you look at the code?",
    "security": "is this allowed?",
    "learning": "can you check the metric after?",
    "risk": "how risky is this?",
    "product": "want to draft a proposal?",
    "feedback": "can you call them back?",
    "coordination": "can you book a review?",
    "investigator": "can you fan this out?",
    "evidence": "can you pack the evidence?",
    "root_cause": "what's the root cause?",
    "test": "someone test this?",
    "orchestrator": "what's next?",
}

_ACK: dict[str, str] = {
    "analytics": "on it",
    "logs": "on it",
    "deploy": "checking",
    "deployment": "checking",
    "database": "looking",
    "customer": "on it",
    "customer_voice": "on it",
    "code": "looking",
    "security": "checking",
    "learning": "watching it",
    "risk": "scoring it",
    "product": "drafting",
    "feedback": "on it",
    "coordination": "finding a slot",
    "investigator": "dispatching",
    "evidence": "packing it",
    "root_cause": "on it",
    "test": "testing",
    "orchestrator": "one sec",
}

# Skip noisy system chatter in the group thread
_SKIP_ARTIFACT = {
    "classification",
    "prd",
}
_SKIP_TEXT_PREFIXES = (
    "dispatching analytics",
    "dispatching specialists",
)


def agent_label(agent_id: str) -> str:
    raw = (agent_id or "agent").removesuffix("_agent").replace("_", " ").strip()
    # First token feels more like a chat name: "Analytics" not "Customer Voice"
    parts = raw.split()
    if not parts:
        return "Agent"
    if parts[0].lower() == "customer" and len(parts) > 1:
        return parts[-1].title()
    return parts[0].title()


def agent_key(agent_id: str) -> str:
    return (agent_id or "").removesuffix("_agent").lower().replace(" ", "_")


def humanize_handoff(src: str, dst: str, summary: str) -> str:
    del src
    s = (summary or "").strip().replace("—", ". ").replace("–", ". ")
    dst_label = agent_label(dst)
    if s and (" " in s or len(s) > 28):
        return s
    key = (s or dst.removesuffix("_agent")).lower().replace(" ", "_")
    topic = _TOPICS.get(key) or _TOPICS.get(dst.removesuffix("_agent")) or (s or dst_label)
    return f"Asked {dst_label} for {topic}"


def ask_line(src: str, dst: str, summary: str = "") -> str:
    name = agent_label(dst)
    s = (summary or "").strip().replace("—", ". ").replace("–", ". ")
    key = agent_key(dst)
    topic_key = (s or key).lower().replace(" ", "_")
    if s and (" " in s or len(s) > 28):
        lower = s[0].lower() + s[1:] if s else s
        if name.lower() in s.lower():
            return _clip(s, 120)
        return _clip(f"{name}, {lower}", 120)
    ask = _ASK.get(topic_key) or _ASK.get(key) or f"can you take {_TOPICS.get(key) or 'this'}?"
    return f"{name}, {ask}"


def ack_line(dst: str, summary: str = "") -> str:
    key = agent_key(dst)
    s = (summary or "").strip()
    if s and (" " in s or len(s) > 28) and not s.lower().startswith("ask"):
        return _clip(s, 100)
    return _ACK.get(key) or "on it"


def _clip(text: str, n: int = 140) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def narrate_artifact_text(author: str, text: str, artifact_type: str | None) -> str:
    """Short colleague-style line for an artifact."""
    del author
    t = (text or "").strip().replace("—", ". ").replace("–", ". ")
    if not t:
        return "done"
    low = t.lower()
    for prefix in _SKIP_TEXT_PREFIXES:
        if low.startswith(prefix):
            return ""
    at = (artifact_type or "").lower()
    if at in _SKIP_ARTIFACT:
        return ""
    if at in {"warehouse", "bq", "analytics", "metric"}:
        # Keep the number, drop the lecture
        return _clip(t if len(t) < 110 else f"got the numbers. {t}", 120)
    if at in {"evidence", "evidence_pack"}:
        return _clip(t, 120)
    if at in {"pr", "code", "code_brief", "patch"}:
        if "http" in low or "/pull/" in low:
            return "pr is up"
        return _clip(t, 100)
    if at in {"mail", "gmail"}:
        if "sent" in low:
            return "mail sent"
        if "draft" in low:
            return "draft ready"
        return _clip(t, 100)
    if at == "coordination":
        return _clip(t, 100)
    if at in {"call_feedback", "call_evidence"}:
        return _clip(t, 140)
    if at in {"call", "contact", "contact_lookup", "voice"}:
        return _clip(t, 120)
    if at == "signal":
        return _clip(t if "picked" in low else f"saw this: {t}", 110)
    if at in {"hypothesis", "root_cause"}:
        return _clip(t, 120)
    if at in {"risk_decision", "approval"}:
        return _clip(t, 100)
    if at in {"voice_context"}:
        return _clip(t, 100)
    return _clip(t, 140)


def _iso(ts: Any) -> str:
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts or "")


def build_workflow_chat(
    *,
    investigation_id: str,
    room: Any | None,
    agent_calls: list[Any],
    messages: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """End-to-end group chat for one workflow (not handoff pairs)."""
    events: list[dict[str, Any]] = []
    room_id = getattr(room, "id", None) if room else None
    room_title = getattr(room, "title", None) if room else None

    msgs = list(messages or [])
    msg_times = [_iso(m.created_at) for m in msgs]

    def _has_reply_soon(agent: str, after: str) -> bool:
        key = agent_key(agent)
        for m, at in zip(msgs, msg_times, strict=True):
            if at > after and agent_key(getattr(m, "author", "")) == key:
                return True
        return False

    for c in agent_calls:
        at = _iso(c.started_at)
        events.append(
            {
                "kind": "chat",
                "id": f"ask:{c.id}",
                "at": at,
                "author": c.from_agent,
                "author_kind": "agent",
                "text": ask_line(c.from_agent, c.to_agent, c.summary),
                "role": "ask",
                "to_agent": c.to_agent,
            }
        )
        if not _has_reply_soon(c.to_agent, at):
            events.append(
                {
                    "kind": "chat",
                    "id": f"ack:{c.id}",
                    "at": at,
                    "author": c.to_agent,
                    "author_kind": "agent",
                    "text": ack_line(c.to_agent, c.summary),
                    "role": "ack",
                }
            )

    for m in msgs:
        at = _iso(m.created_at)
        kind = getattr(m.kind, "value", m.kind)
        art_type = m.artifact_type
        text = narrate_artifact_text(m.author, m.text or "", art_type)
        if not text:
            continue
        if art_type in {"approval"} or kind == "system":
            events.append({"kind": "system", "id": m.id, "at": at, "text": text})
            continue
        if art_type == "pr":
            events.append({"kind": "system", "id": f"sys:{m.id}", "at": at, "text": "PR opened"})
            continue
        if art_type in {"mail", "gmail"} and "sent" in text.lower():
            events.append({"kind": "system", "id": f"sys:{m.id}", "at": at, "text": "mail sent"})
            continue
        events.append(
            {
                "kind": "chat",
                "id": m.id,
                "at": at,
                "author": m.author,
                "author_kind": getattr(m.author_kind, "value", m.author_kind),
                "text": text,
                "msg_kind": kind,
                "artifact_type": art_type,
                "artifact": m.artifact if isinstance(m.artifact, dict) else {},
                "room_id": room_id,
                "room_title": room_title,
                "role": "message",
            }
        )

    events.sort(key=lambda e: str(e.get("at") or ""))
    deduped: list[dict[str, Any]] = []
    for e in events:
        if deduped:
            prev = deduped[-1]
            if (
                prev.get("kind") == e.get("kind") == "chat"
                and prev.get("author") == e.get("author")
                and (prev.get("text") or "").strip().lower() == (e.get("text") or "").strip().lower()
            ):
                continue
            if (
                prev.get("role") == "ack"
                and e.get("role") == "message"
                and prev.get("author") == e.get("author")
            ):
                deduped.pop()
        deduped.append(e)

    if deduped:
        deduped.insert(
            0,
            {
                "kind": "system",
                "id": f"day:{investigation_id}",
                "at": deduped[0].get("at"),
                "text": "Today",
            },
        )
    return deduped
