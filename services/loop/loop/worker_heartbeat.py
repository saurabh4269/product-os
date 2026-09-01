"""Worker heartbeat — last tick timestamp for /api/status."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_last: dict[str, Any] = {}


def record_tick(payload: dict[str, Any]) -> None:
    with _lock:
        global _last
        _last = {
            **payload,
            "at": datetime.now(timezone.utc).isoformat(),
        }


def last_tick() -> dict[str, Any]:
    with _lock:
        return dict(_last)
