"""Background signal watch — Signal agent polls; auto-investigates when something moves."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

_last_seen: set[str] = set()
_lock = threading.Lock()
_last_tick: dict[str, Any] = {}


def last_tick_summary() -> dict[str, Any]:
    with _lock:
        return dict(_last_tick)


def reset_watch_state(engine: Any | None = None) -> None:
    """Test/dev helper — avoid cross-test pollution of _last_seen."""
    global _last_seen
    with _lock:
        _last_seen = _signal_ids(engine) if engine is not None else set()


def _signal_ids(engine: Any) -> set[str]:
    if not hasattr(engine.store, "list_signals"):
        return set()
    return {s.id for s in engine.store.list_signals()}


def tick_signal_watch(engine: Any) -> dict[str, Any]:
    """One poll cycle. Returns summary; publishes WS on new signals; auto-investigates."""
    global _last_seen, _last_tick
    from .live import HUB
    from .runtime_mode import use_file_warehouse

    if use_file_warehouse():
        use_all = os.environ.get("LOOP_SIGNAL_WATCH_ALL", "1") == "1"
        found = engine.detect_all_signals() if use_all else engine.detect_signals()
    else:
        found = engine.detect_all_signals()
    current = _signal_ids(engine)
    with _lock:
        new_ids = current - _last_seen
        _last_seen = current

    auto_results: list[dict[str, Any]] = []
    if os.environ.get("LOOP_AUTO_INVESTIGATE", "1") == "1":
        from .auto_investigate import (
            auto_investigate_new_signals,
            count_applied,
            finish_stalled_investigations,
        )

        stalled = finish_stalled_investigations(engine)
        if new_ids:
            auto_results = stalled + auto_investigate_new_signals(engine, sorted(new_ids))
        else:
            auto_results = stalled

    payload = {
        "type": "orchestration",
        "mode": "watching",
        "at": datetime.now(timezone.utc).isoformat(),
        "signals_open": len([s for s in found if getattr(s, "status", None) != "suppressed"]),
        "new_signal_ids": sorted(new_ids),
        "auto_investigated": count_applied(auto_results),
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

    payload["auto_results"] = auto_results
    with _lock:
        _last_tick = payload
    return payload


def start_signal_watch(engine: Any, *, interval_sec: float | None = None) -> threading.Thread:
    """Daemon thread — Signal agent background poll."""
    interval = interval_sec or float(os.environ.get("LOOP_SIGNAL_WATCH_SEC", "45"))

    def _loop() -> None:
        import time

        from .audit import record

        with _lock:
            global _last_seen
            _last_seen = _signal_ids(engine)
        while True:
            try:
                tick_signal_watch(engine)
            except Exception as exc:
                try:
                    record(
                        engine.store,
                        actor="signal_watch",
                        action="tick.error",
                        resource="signal_watch",
                        detail={"error": str(exc)[:240]},
                    )
                except Exception:
                    pass
            time.sleep(max(10.0, interval))

    t = threading.Thread(target=_loop, name="signal-watch", daemon=True)
    t.start()
    return t
