"""Background signal watch — Signal agent polls; homepage wakes when something moves."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

_last_seen: set[str] = set()
_lock = threading.Lock()


def _signal_ids(engine: Any) -> set[str]:
    if not hasattr(engine.store, "list_signals"):
        return set()
    return {s.id for s in engine.store.list_signals()}


def tick_signal_watch(engine: Any) -> dict[str, Any]:
    """One poll cycle. Returns summary; publishes WS on new signals."""
    global _last_seen
    from .live import HUB

    found = engine.detect_signals()
    current = _signal_ids(engine)
    with _lock:
        new_ids = current - _last_seen
        _last_seen = current

    payload = {
        "type": "orchestration",
        "mode": "watching",
        "at": datetime.now(timezone.utc).isoformat(),
        "signals_open": len([s for s in found if getattr(s, "status", None) != "suppressed"]),
        "new_signal_ids": sorted(new_ids),
    }

    if new_ids:
        payload["mode"] = "active"
        payload["watch_line"] = "Signal agent detected movement"
        for sid in sorted(new_ids):
            sig = engine.store.get_signal(sid)
            if not sig:
                continue
            HUB.publish_global(
                {
                    "type": "signal_detected",
                    "signal_id": sid,
                    "metric": sig.metric,
                    "magnitude": sig.magnitude,
                    "family": getattr(sig.family, "value", str(sig.family)),
                }
            )
        HUB.publish_global(payload)
    return payload


def start_signal_watch(engine: Any, *, interval_sec: float | None = None) -> threading.Thread:
    """Daemon thread — Signal agent background poll."""
    interval = interval_sec or float(os.environ.get("LOOP_SIGNAL_WATCH_SEC", "45"))

    def _loop() -> None:
        import time

        # Seed so boot doesn't flood "new" for existing signals.
        with _lock:
            global _last_seen
            _last_seen = _signal_ids(engine)
        while True:
            try:
                tick_signal_watch(engine)
            except Exception:
                pass
            time.sleep(max(10.0, interval))

    t = threading.Thread(target=_loop, name="signal-watch", daemon=True)
    t.start()
    return t
