"""Live office snapshot: who is working, on what, and who handed work to whom."""

from __future__ import annotations

from .engine import LoopEngine
from .registry import ENTRIES, by_id

_ALIASES = {
    "orchestrator_agent": "orchestrator",
    "analytics": "analytics_agent",
    "logs": "logs_agent",
    "deployment": "deployment_agent",
    "customer_voice": "customer_voice_agent",
    "feedback": "feedback_agent",
    "product": "product_agent",
    "risk": "risk_agent",
    "code": "code_agent",
    "learning": "learning_agent",
    "security": "security_policy_agent",
    "security_policy": "security_policy_agent",
    "coordinator": "coordination_agent",
    "coordination": "coordination_agent",
}

# Caps for GET /api/office — never load full message/call tables on 2Gi poll.
_OFFICE_CALL_SCAN = 80
_OFFICE_HANDOFF_CAP = 40


def canonical_agent(raw: str) -> str:
    if raw in by_id() or raw in {"you", "system"}:
        return raw
    if raw in _ALIASES:
        return _ALIASES[raw]
    guessed = f"{raw}_agent"
    if guessed in by_id():
        return guessed
    return raw


def _district(kind: str | None) -> str:
    if kind == "incident":
        return "Incidents"
    if kind == "opportunity":
        return "Ideas"
    if kind == "review":
        return "Reviews"
    if kind == "research":
        return "Research"
    if kind == "ops":
        return "Ops"
    return "Office"


def office_snapshot(eng: LoopEngine) -> dict:
    rooms = eng.store.list_rooms()
    inv_to_room = {r.investigation_id: r for r in rooms if r.investigation_id}
    author_stats_raw = eng.store.message_stats_by_author()
    author_stats: dict[str, tuple[int, object | None]] = {}
    for author, (cnt, msg) in author_stats_raw.items():
        canon = canonical_agent(author)
        prev_cnt, prev_msg = author_stats.get(canon, (0, None))
        merged_msg = prev_msg
        if msg and (not merged_msg or msg.created_at > merged_msg.created_at):
            merged_msg = msg
        author_stats[canon] = (prev_cnt + cnt, merged_msg)
    calls = eng.store.recent_agent_calls(limit=_OFFICE_CALL_SCAN)

    rooms_by_member: dict[str, list] = {}
    for room in rooms:
        for member in room.members:
            rooms_by_member.setdefault(canonical_agent(member), []).append(room)

    handoffs = []
    incoming: dict[str, list] = {}
    outgoing: dict[str, list] = {}
    for call in calls:
        src = canonical_agent(call.from_agent)
        dst = canonical_agent(call.to_agent)
        room = inv_to_room.get(call.investigation_id)
        row = {
            **call.model_dump(mode="json"),
            "from_agent": src,
            "to_agent": dst,
            "room_id": room.id if room else None,
            "room_title": room.title if room else None,
        }
        handoffs.append(row)
        incoming.setdefault(dst, []).append(row)
        outgoing.setdefault(src, []).append(row)

    desks = []
    for entry in ENTRIES:
        agent_id = entry.id
        msg_count, last_msg = author_stats.get(agent_id, (0, None))
        last_in = incoming.get(agent_id, [])[-1] if incoming.get(agent_id) else None
        last_out = outgoing.get(agent_id, [])[-1] if outgoing.get(agent_id) else None
        member_rooms = rooms_by_member.get(agent_id, [])
        room = None
        if last_msg:
            room = eng.store.get_room(last_msg.room_id)
        elif last_in and last_in.get("room_id"):
            room = eng.store.get_room(last_in["room_id"])
        elif member_rooms:
            room = member_rooms[0]

        if last_msg:
            status = "working"
            doing = last_msg.text
        elif last_in:
            status = "working"
            doing = last_in.get("summary") or entry.role
        elif last_out:
            status = "handing_off"
            doing = last_out.get("summary") or "Handing work to a teammate"
        else:
            status = "idle"
            doing = entry.role

        desks.append(
            {
                "id": entry.id,
                "display_name": entry.display_name,
                "role": entry.role,
                "identity": entry.identity,
                "status": status,
                "doing": doing,
                "room_id": room.id if room else None,
                "room_title": room.title if room else None,
                "district": _district(room.kind.value if room else None),
                "last_at": (last_msg.created_at if last_msg else None)
                or (last_in.get("started_at") if last_in else None),
                "handed_from": last_in["from_agent"] if last_in else None,
                "handed_to": last_out["to_agent"] if last_out else None,
                "message_count": msg_count,
                "handoff_count": len(incoming.get(agent_id, [])) + len(outgoing.get(agent_id, [])),
            }
        )

    working = sum(1 for d in desks if d["status"] != "idle")
    return {
        "desks": desks,
        "handoffs": handoffs[-_OFFICE_HANDOFF_CAP:],
        "working": working,
        "idle": len(desks) - working,
    }


def agent_snapshot(eng: LoopEngine, agent_id: str) -> dict | None:
    from .narrate import humanize_handoff

    agent_id = canonical_agent(agent_id)
    entry = by_id().get(agent_id)
    if not entry:
        return None
    office = office_snapshot(eng)
    desk = next((d for d in office["desks"] if d["id"] == agent_id), None)
    rooms = []
    messages = []
    for room in eng.store.list_rooms():
        if agent_id in {canonical_agent(m) for m in room.members}:
            rooms.append(
                {
                    "id": room.id,
                    "title": room.title,
                    "kind": room.kind.value,
                    "topic": room.topic,
                }
            )
        for msg in eng.store.list_messages(room.id):
            if canonical_agent(msg.author) != agent_id:
                continue
            messages.append({**msg.model_dump(mode="json"), "room_title": room.title})
    messages.sort(key=lambda m: m["created_at"])
    handoffs = []
    for h in office["handoffs"]:
        if h["from_agent"] != agent_id and h["to_agent"] != agent_id:
            continue
        handoffs.append(
            {
                **h,
                "summary": humanize_handoff(h["from_agent"], h["to_agent"], h.get("summary") or ""),
            }
        )
    return {
        "agent": entry.model_dump(mode="json"),
        "desk": desk,
        "rooms": rooms,
        "messages": messages[-40:],
        "handoffs": handoffs[-30:],
        "resources": _agent_resources(eng, agent_id),
    }


def _agent_resources(eng: LoopEngine, agent_id: str) -> list:
    try:
        from .proof import agent_resources

        return agent_resources(eng, agent_id)
    except Exception:
        return []
