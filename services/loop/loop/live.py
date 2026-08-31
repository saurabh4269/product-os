"""Live room bus — agent_callback push + product-os-v2 Hub.

Agents and the engine push events; the console WebSocket fans them out.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from .models import InvestigationState, LoopType

# Visible pipeline chips (Type A BUG vs Type B FEATURE).
PIPELINE_BUG = [
    "signal",
    "investigate",
    "evidence",
    "root_cause",
    "code",
    "risk",
    "approve",
    "verify",
    "learn",
]
PIPELINE_FEATURE = [
    "signal",
    "investigate",
    "evidence",
    "product",
    "experiment",
    "risk",
    "approve",
    "verify",
    "learn",
]

PIPELINE_LABEL = {
    "signal": "Signal",
    "investigate": "Investigate",
    "evidence": "Evidence",
    "root_cause": "Root cause",
    "code": "Code",
    "product": "Product",
    "experiment": "Experiment",
    "risk": "Risk",
    "approve": "Approve",
    "verify": "Verify",
    "learn": "Learn",
}

_STATE_STAGE = {
    InvestigationState.OPEN: "signal",
    InvestigationState.GATHERING: "investigate",
    InvestigationState.HYPOTHESIS: "evidence",
    InvestigationState.ACTION_PROPOSED: "risk",
    InvestigationState.AWAITING_APPROVAL: "approve",
    InvestigationState.APPROVED: "approve",
    InvestigationState.ACTING: "approve",
    InvestigationState.VERIFYING: "verify",
    InvestigationState.RESOLVED: "learn",
    InvestigationState.PARTIALLY_RESOLVED: "learn",
    InvestigationState.NOT_RESOLVED: "learn",
    InvestigationState.INCONCLUSIVE: "learn",
}


class Hub:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self.global_clients: set[WebSocket] = set()
        self.presence: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.buffer: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.rooms[room_id].add(ws)
        for event in self.buffer.get(room_id, [])[-40:]:
            try:
                await ws.send_text(json.dumps(event, default=str))
            except Exception:
                break
        for event in self.presence.get(room_id, {}).values():
            try:
                await ws.send_text(json.dumps(event, default=str))
            except Exception:
                break

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        self.rooms[room_id].discard(ws)
        self.global_clients.discard(ws)

    async def connect_global(self, ws: WebSocket) -> None:
        await ws.accept()
        self.global_clients.add(ws)

    def publish(self, room_id: str, event: dict[str, Any]) -> None:
        event = {**event, "roomId": room_id}
        self.buffer[room_id].append(event)
        if len(self.buffer[room_id]) > 200:
            self.buffer[room_id] = self.buffer[room_id][-200:]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(room_id, event))
        except RuntimeError:
            pass

    async def _broadcast(self, room_id: str, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        dead: list[tuple[str, WebSocket]] = []
        for ws in list(self.rooms.get(room_id, set())):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(("room", ws))
        for ws in list(self.global_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(("global", ws))
        for kind, ws in dead:
            if kind == "room":
                self.rooms[room_id].discard(ws)
            else:
                self.global_clients.discard(ws)

    def publish_global(self, event: dict[str, Any]) -> None:
        """Campus-wide feed (activity log, counters) — no room required."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_global(event))
        except RuntimeError:
            pass

    async def _broadcast_global(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        dead: list[WebSocket] = []
        for ws in list(self.global_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.global_clients.discard(ws)

    def set_presence(self, room_id: str, agent_id: str, status: str, pixel: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "type": "agent_presence",
            "agentId": agent_id,
            "status": status,
            "pixel": pixel or {"label": agent_id, "hue": abs(hash(agent_id)) % 360},
            "roomId": room_id,
        }
        self.presence[room_id][agent_id] = event
        self.publish(room_id, event)
        return event

    def agents_in(self, room_id: str) -> list[dict[str, Any]]:
        return list(self.presence.get(room_id, {}).values())


HUB = Hub()


def funnel_for(loop_type: LoopType | str | None, state: InvestigationState | str | None, awaiting: bool = False) -> dict[str, Any]:
    if isinstance(loop_type, LoopType):
        raw = loop_type.value
    else:
        raw = str(loop_type or "")
    is_feature = raw.lower() in {"type_b", "b", "feature"}
    steps = list(PIPELINE_FEATURE if is_feature else PIPELINE_BUG)
    stage = "signal"
    if state is not None:
        if isinstance(state, str):
            try:
                state = InvestigationState(state)
            except ValueError:
                state = None
        if isinstance(state, InvestigationState):
            stage = _STATE_STAGE.get(state, "signal")
            if state == InvestigationState.HYPOTHESIS:
                stage = "product" if is_feature else "root_cause"
            if state == InvestigationState.ACTION_PROPOSED and not awaiting:
                stage = "risk"
    if awaiting:
        stage = "approve"
    current = stage if stage in steps else steps[0]
    idx = steps.index(current)
    return {
        "steps": [{"id": s, "label": PIPELINE_LABEL[s], "on": i <= idx} for i, s in enumerate(steps)],
        "current": current,
        "kind": "feature" if is_feature else "bug",
    }


def room_id_for_investigation(store: Any, inv_id: str) -> str | None:
    for room in store.list_rooms():
        if room.investigation_id == inv_id:
            return room.id
    return None
