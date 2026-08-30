"""Typed A2A envelopes — product-os-v2 protocol, durable in AgentCall rows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

A2AKind = Literal[
    "task",
    "evidence",
    "hypothesis",
    "proposal",
    "risk",
    "experiment",
    "memory",
    "presence",
    "tool_request",
    "tool_result",
    "decision",
    "pr",
    "approval",
    "fork",
    "outcome",
    "deny",
    "handoff",
]


class A2AEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = "product-os-a2a/1"
    from_agent: str
    to_agent: str = "broadcast"
    kind: A2AKind = "handoff"
    trace_id: str = ""
    room_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_event(self) -> dict[str, Any]:
        return {
            "type": "a2a",
            "envelope": self.model_dump(),
            "from": self.from_agent,
            "to": self.to_agent,
            "kind": self.kind,
            "summary": self.payload.get("summary") or self.payload.get("text") or self.kind,
        }
