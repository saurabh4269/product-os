"""One signal path: investigation pipeline + live WebSocket choreography."""

from __future__ import annotations

from typing import Any

from loop.investigation import AnomalyEvent, run_investigation


def enrich_signal_dict(engine: Any, signal: dict[str, Any], *, tenant_id: str | None = None) -> dict[str, Any]:
    """Merge BQ-backed probe dimensions into a signal before investigators run."""
    dims = dict(signal.get("dimensions") or {})
    tid = tenant_id or str(dims.get("tenant_id") or "")
    if not tid:
        room_id = signal.get("room_id")
        if room_id:
            room = engine.store.get_room(str(room_id))
            tid = room.tenant_id if room else ""
    if tid:
        dims.setdefault("tenant_id", tid)
    tenant = engine.store.get_tenant(tid) if tid else None
    if not tenant:
        return dims
    from loop.connectors.bigquery import enrich_anomaly_dimensions, has_bq, read_metric_window

    if not has_bq(tenant):
        return dims
    dims = enrich_anomaly_dimensions(engine.store, tenant, dims)
    metric = str(signal.get("metric") or signal.get("scenario") or "signal")
    baseline = signal.get("baseline")
    reading = read_metric_window(
        engine,
        tenant,
        metric,
        baseline=float(baseline) if baseline is not None else None,
    )
    if reading:
        dims.setdefault("analytics_claim", reading.get("claim"))
        dims.setdefault("database_claim", reading.get("claim"))
        dims.setdefault("database", {"value": reading.get("value"), "source": reading.get("source")})
    return dims


def signal_to_event(signal: dict[str, Any]) -> AnomalyEvent:
    dims = signal.get("dimensions") if isinstance(signal.get("dimensions"), dict) else {}
    fork = str(signal.get("fork") or "").upper()
    polarity = signal.get("polarity") or ("negative" if fork != "FEATURE" else "positive")
    delta = signal.get("delta")
    magnitude = float(delta) if delta is not None else -0.12
    if polarity == "positive" and magnitude < 0:
        magnitude = abs(magnitude)
    return AnomalyEvent(
        kind=str(signal.get("kind") or "api_signal"),
        metric=str(signal.get("metric") or signal.get("scenario") or "signal"),
        title=str(signal.get("title") or ""),
        family=str(signal.get("domain") or "business"),
        magnitude=magnitude,
        baseline=float(dims.get("baseline") or signal.get("baseline") or 0.5),
        funnel_position=str(dims.get("funnel_position") or signal.get("funnel_position") or "product"),
        confidence=float(dims.get("confidence") or 0.75),
        source=str(signal.get("source") or "api.signals"),
        polarity="negative" if str(polarity).startswith("neg") else "positive",
        dimensions={**dims, "hypothesis": dims.get("hypothesis")},
    )


def run_signal_pipeline(
    engine: Any,
    room_id: str | None,
    signal: dict[str, Any],
    *,
    fork: str | None = None,
    probe_exfil: bool = False,
    tenant_id: str | None = None,
    live_progress: bool = True,
) -> dict[str, Any]:
    """Investigation runner with live presence — replaces synthetic-only graph for API paths."""
    from loop.activity import emit_activity
    from loop.agents.graphs import run_live_graph
    from loop.live import HUB
    from loop.models import LoopType, PathKind, RoomKind

    if probe_exfil or signal.get("scenario") in {"security_exfil", "pii-exfil-deny"}:
        rid = room_id or _room_for_scenario(engine, signal)
        if not rid:
            raise ValueError("room required for security exfil probe")
        return run_live_graph(engine, rid, signal, fork=fork or "BUG", probe_exfil=True)

    tid = tenant_id
    if not tid and room_id:
        room_peek = engine.store.get_room(room_id)
        tid = room_peek.tenant_id if room_peek else None
    if tid:
        signal = {**signal, "dimensions": enrich_signal_dict(engine, signal, tenant_id=tid)}

    forced = (fork or signal.get("fork") or ("FEATURE" if signal.get("polarity") == "positive" else "BUG")).upper()
    event = signal_to_event({**signal, "fork": forced})
    scenario = str(signal.get("scenario") or f"signal:{event.metric}")
    room = engine.store.get_room(room_id) if room_id else None
    if not room:
        room = next((r for r in engine.store.list_rooms() if r.scenario_id == scenario), None)

    if room and room.investigation_id:
        inv = engine.store.get_investigation(room.investigation_id)
        emit_activity(agent_id="orchestrator", message=f"Reusing open work on {event.metric}", room_id=room.id, stage="investigate")
        HUB.publish(room.id, {"type": "funnel_stage", "stage": "investigate", "agentId": "orchestrator"})
        return {
            "trace_id": inv.id if inv else room.investigation_id,
            "room_id": room.id,
            "investigation_id": room.investigation_id,
            "fork": forced,
            "pipeline": ["investigate", "evidence", "hypothesis", "risk", "approve"],
            "reused": True,
        }

    lt = LoopType.TYPE_B if forced == "FEATURE" else LoopType.TYPE_A
    rk = RoomKind.OPPORTUNITY if forced == "FEATURE" else RoomKind.INCIDENT
    pk = PathKind.FEATURE if forced == "FEATURE" else PathKind.BUG

    emit_activity(agent_id="signal_agent", message=f"Signal · {event.metric}", room_id=room_id or "", stage="signal")
    HUB.publish(room_id or "pending", {"type": "funnel_stage", "stage": "signal", "agentId": "signal_agent"})

    out = run_investigation(
        engine,
        event,
        scenario_id=scenario,
        tenant_id=tenant_id or (room.tenant_id if room else None),
        propose_action=forced == "BUG",
        loop_type=lt,
        path=pk,
        room_kind=rk,
        live_progress=live_progress,
    )

    rid = str(out.get("room_id") or "")
    inv_id = out.get("investigation_id")
    if rid:
        HUB.publish(rid, {"type": "funnel_stage", "stage": "evidence", "agentId": "evidence_agent"})
        emit_activity(agent_id="evidence_agent", message="Evidence pack ready", room_id=rid, stage="evidence")
        actions = engine.store.list_actions(inv_id) if inv_id else []
        awaiting = any(a.status in {"proposed", "awaiting_approval"} for a in actions)
        if awaiting:
            HUB.publish(
                rid,
                {
                    "type": "approval_required",
                    "approval": {"investigation_id": inv_id, "status": "pending"},
                },
            )
            emit_activity(agent_id="risk_agent", message="Waiting on human approval", room_id=rid, stage="approve")
            HUB.publish(rid, {"type": "funnel_stage", "stage": "approve", "agentId": "risk_agent"})
        else:
            HUB.publish(rid, {"type": "funnel_stage", "stage": "risk", "agentId": "risk_agent"})

    return {
        **out,
        "trace_id": inv_id or out.get("scenario", scenario),
        "room_id": rid,
        "fork": forced,
        "pipeline": out.get("pipeline") or ["investigate", "evidence", "hypothesis", "risk", "approve"],
        "steps": len(out.get("fan_out") or []),
        "reused": False,
    }


def _room_for_scenario(engine: Any, signal: dict[str, Any]) -> str | None:
    slug = signal.get("scenario")
    if not slug:
        return None
    room = next((r for r in engine.store.list_rooms() if r.scenario_id == slug), None)
    return room.id if room else None
