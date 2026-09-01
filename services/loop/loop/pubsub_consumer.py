"""Pub/Sub push handler — tenant signals drive investigations without manual POST."""

from __future__ import annotations

import base64
import json
from typing import Any


def decode_push(body: dict[str, Any]) -> dict[str, Any] | None:
    msg = body.get("message") if isinstance(body.get("message"), dict) else {}
    raw = msg.get("data")
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        payload = json.loads(decoded)
        return payload if isinstance(payload, dict) else None
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def handle_signal_push(engine: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Pub/Sub payload → tenant ingest or auto-investigate."""
    from .audit import record

    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not tenant_id:
        return {"status": "skipped", "reason": "missing tenant_id"}

    tenant = engine.store.get_tenant(tenant_id)
    if not tenant:
        return {"status": "skipped", "reason": "unknown tenant"}

    metric = str(payload.get("metric") or "purchase_conversion")
    magnitude = float(payload.get("magnitude") or 0)
    baseline = float(payload.get("baseline") or 0)
    note = str(payload.get("note") or payload.get("detail") or "")
    signal_id = str(payload.get("signal_id") or "")

    if signal_id:
        from .auto_investigate import auto_investigate_signal

        result = auto_investigate_signal(engine, signal_id)
        record(
            engine.store,
            actor="pubsub",
            action="signal.push",
            resource=f"tenant:{tenant_id}",
            detail=result,
        )
        return result

    from .world import ingest_tenant_signal

    out = ingest_tenant_signal(
        engine,
        tenant,
        metric=metric,
        magnitude=magnitude,
        baseline=baseline,
        note=note,
        source="pubsub.push",
        async_finish=True,
    )
    record(
        engine.store,
        actor="pubsub",
        action="signal.ingest",
        resource=f"tenant:{tenant_id}",
        detail={"room_id": out.get("room_id"), "joined": out.get("joined")},
    )
    return {"status": "applied", **out}
