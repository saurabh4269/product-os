"""Live office snapshot: who is working, on what, and who handed work to whom."""

from __future__ import annotations

from .engine import LoopEngine
from .registry import ENTRIES, by_id


_ALIASES = {
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
    messages = eng.store.list_all_messages()
    calls = eng.store.list_all_agent_calls()

    msgs_by_author: dict[str, list] = {}
    rooms_by_member: dict[str, list] = {}
    for room in rooms:
        for member in room.members:
            rooms_by_member.setdefault(canonical_agent(member), []).append(room)
    for msg in messages:
        msgs_by_author.setdefault(canonical_agent(msg.author), []).append(msg)

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
        own_msgs = msgs_by_author.get(entry.id, [])
        last_msg = own_msgs[-1] if own_msgs else None
        last_in = incoming.get(entry.id, [])[-1] if incoming.get(entry.id) else None
        last_out = outgoing.get(entry.id, [])[-1] if outgoing.get(entry.id) else None
        member_rooms = rooms_by_member.get(entry.id, [])
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
                "message_count": len(own_msgs),
                "handoff_count": len(incoming.get(entry.id, [])) + len(outgoing.get(entry.id, [])),
            }
        )

    working = sum(1 for d in desks if d["status"] != "idle")
    return {
        "desks": desks,
        "handoffs": handoffs[-40:],
        "working": working,
        "idle": len(desks) - working,
    }


def agent_snapshot(eng: LoopEngine, agent_id: str) -> dict | None:
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
    handoffs = [
        h
        for h in office["handoffs"]
        if h["from_agent"] == agent_id or h["to_agent"] == agent_id
    ]
    return {
        "agent": entry.model_dump(mode="json"),
        "desk": desk,
        "rooms": rooms,
        "messages": messages[-40:],
        "handoffs": handoffs[-30:],
    }
