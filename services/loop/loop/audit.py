"""Append-only audit trail for control-plane actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    id: str
    at: str
    actor: str
    action: str
    resource: str
    detail: dict[str, Any] = Field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return f"aud_{uuid.uuid4().hex[:12]}"


def record(store: Any, *, actor: str, action: str, resource: str, detail: dict | None = None) -> AuditEvent:
    event = AuditEvent(
        id=_id(),
        at=_now(),
        actor=actor,
        action=action,
        resource=resource,
        detail=detail or {},
    )
    store.put_audit(event)
    try:
        from loop.state_persist import schedule_snapshot

        schedule_snapshot(store.path)
    except Exception:
        pass
    return event
