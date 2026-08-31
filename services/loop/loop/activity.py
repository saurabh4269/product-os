"""Global activity feed — SalesShortcut-style scrolling log on campus."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any

_ACTIVITY: deque[dict[str, Any]] = deque(maxlen=300)


def emit_activity(
    *,
    agent_id: str,
    message: str,
    room_id: str = "",
    stage: str = "",
    tenant_id: str = "",
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "agent_id": agent_id,
        "message": message,
        "room_id": room_id,
        "stage": stage,
        "tenant_id": tenant_id,
    }
    if artifact:
        row["artifact"] = artifact
    _ACTIVITY.appendleft(row)
    try:
        from loop.live import HUB

        HUB.publish_global({"type": "activity", **row})
        if room_id:
            HUB.publish(room_id, {"type": "activity", **row})
    except Exception:
        pass
    return row


def list_activity(limit: int = 80) -> list[dict[str, Any]]:
    n = max(1, min(limit, 200))
    return list(_ACTIVITY)[:n]
