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
from .workflow import (
    NODE_LABEL,
    workflow_for,
)

# Re-exported for callers that imported these from live.
PIPELINE_LABEL = NODE_LABEL


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


def funnel_for(
    loop_type: LoopType | str | None,
    state: InvestigationState | str | None,
    awaiting: bool = False,
    *,
    path: Any = None,
    room_kind: Any = None,
    scenario_id: str | None = None,
    dimensions: dict[str, Any] | None = None,
    artifact_types: list[str] | None = None,
    action_types: list[str] | None = None,
    action_statuses: list[str] | None = None,
    propose_action: bool | None = None,
    signal_family: str | None = None,
    signal_source: str | None = None,
) -> dict[str, Any]:
    """Per-room funnel chips. Steps are composed from case needs, not a fixed list."""
    wf = workflow_for(
        loop_type=loop_type,
        path=path,
        room_kind=room_kind,
        scenario_id=scenario_id,
        state=state,
        awaiting=awaiting,
        dimensions=dimensions,
        artifact_types=artifact_types,
        action_types=action_types,
        action_statuses=action_statuses,
        propose_action=propose_action,
        signal_family=signal_family,
        signal_source=signal_source,
    )
    return {
        "steps": [{"id": s["id"], "label": s["label"], "on": s["on"]} for s in wf["steps"]],
        "current": wf["current"],
        "kind": wf["kind"],
        "nodes": wf["nodes"],
        "needs": wf["needs"],
        "tags": wf["tags"],
    }


def room_id_for_investigation(store: Any, inv_id: str) -> str | None:
    for room in store.list_rooms():
        if room.investigation_id == inv_id:
            return room.id
    return None
