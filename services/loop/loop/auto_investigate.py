"""Close the loop: ambient detect → unified investigate → propose without human ingest."""

from __future__ import annotations

from typing import Any

from .models import InvestigationState, SignalStatus

_STALLED_STATES = {
    InvestigationState.OPEN,
    InvestigationState.GATHERING,
}


def tenant_id_from_signal(signal: Any) -> str | None:
    src = str(getattr(signal, "source", "") or "")
    if src.startswith("tenant."):
        return src.split(".", 1)[1] or None
    for seg in getattr(signal, "affected_segments", []) or []:
        ch = getattr(seg, "channel", None) or (seg.get("channel") if isinstance(seg, dict) else None)
        if ch and str(ch).startswith("tenant."):
            return str(ch).split(".", 1)[1] or None
    return None


def _terminal_states() -> set[InvestigationState]:
    return {
        InvestigationState.RESOLVED,
        InvestigationState.NOT_RESOLVED,
        InvestigationState.INCONCLUSIVE,
        InvestigationState.PARTIALLY_RESOLVED,
    }


def investigation_is_stalled(engine: Any, inv: Any) -> bool:
    if inv.state in _terminal_states():
        return False
    if engine.store.list_hypotheses(inv.id):
        return False
    if inv.state in _STALLED_STATES:
        return True
    # Async ingest opened a room but never reached hypothesis.
    return bool(inv.room_id) and inv.state not in {
        InvestigationState.AWAITING_APPROVAL,
        InvestigationState.APPROVED,
        InvestigationState.ACTING,
        InvestigationState.VERIFYING,
    }


def stalled_investigations(engine: Any) -> list[Any]:
    return [inv for inv in engine.store.list_investigations() if investigation_is_stalled(engine, inv)]


def signal_has_open_investigation(engine: Any, signal_id: str) -> bool:
    terminal = _terminal_states()
    for inv in engine.store.list_investigations():
        if signal_id not in inv.originating_signal_ids:
            continue
        if inv.state not in terminal and not investigation_is_stalled(engine, inv):
            return True
    return False


def finish_stalled_investigation(engine: Any, inv: Any) -> dict[str, Any]:
    """Complete a pipeline that opened a room but never reached hypothesis (async ingest)."""
    from .audit import record
    from .investigation import (
        _finish_investigation_after_open,
        aggregate_evidence,
        resolve_loop,
        run_investigators,
    )
    from .investigation_signal import anomaly_event_from_signal

    sig_id = inv.originating_signal_ids[0] if inv.originating_signal_ids else None
    sig = engine.store.get_signal(sig_id) if sig_id else None
    if not sig or not inv.room_id:
        return {"investigation_id": inv.id, "status": "skipped", "reason": "missing_signal_or_room"}
    room = engine.store.get_room(inv.room_id)
    if not room:
        return {"investigation_id": inv.id, "status": "skipped", "reason": "missing_room"}

    event = anomaly_event_from_signal(sig, tenant_id=inv.tenant_id)
    claims = run_investigators(event)
    pack = aggregate_evidence(event, claims)
    lt, pth, rk, clas, _ = resolve_loop(event)
    tenant = engine.store.get_tenant(inv.tenant_id) if inv.tenant_id else None
    propose = float(sig.magnitude) < 0
    _finish_investigation_after_open(
        engine,
        room=room,
        inv=inv,
        event=event,
        claims=claims,
        pack=pack,
        tenant=tenant,
        bound_tenant=inv.tenant_id,
        clas=clas,
        propose_action=propose,
        action_type="code_change",
        surface=None,
        extra_artifacts=None,
        live_progress=True,
    )
    hyp = engine.store.list_hypotheses(inv.id)
    if not hyp:
        record(
            engine.store,
            actor="signal_agent",
            action="auto_investigate.gate_failed",
            resource=f"investigation:{inv.id}",
            detail={"signal_id": sig.id},
        )
        return {
            "investigation_id": inv.id,
            "signal_id": sig.id,
            "status": "failed",
            "reason": "three_source_gate",
        }
    action = engine.store.list_actions(inv.id)
    record(
        engine.store,
        actor="signal_agent",
        action="auto_investigate.stalled_finished",
        resource=f"investigation:{inv.id}",
        detail={"signal_id": sig.id, "room_id": room.id},
    )
    return {
        "investigation_id": inv.id,
        "signal_id": sig.id,
        "room_id": room.id,
        "status": "applied",
        "awaiting_approval": bool(action and action[0].status == "awaiting_approval"),
        "stalled": True,
    }


def finish_stalled_investigations(engine: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for inv in stalled_investigations(engine):
        try:
            results.append(finish_stalled_investigation(engine, inv))
        except Exception as exc:
            from .audit import record

            record(
                engine.store,
                actor="signal_agent",
                action="auto_investigate.stalled_error",
                resource=f"investigation:{inv.id}",
                detail={"error": str(exc)[:240]},
            )
            results.append({"investigation_id": inv.id, "status": "error", "error": str(exc)[:240]})
    return results


def auto_investigate_signal(engine: Any, signal_id: str) -> dict[str, Any]:
    """Run the unified investigation pipeline for one signal."""
    from .audit import record
    from .investigation import run_investigation
    from .investigation_signal import anomaly_event_from_signal
    from .models import LoopType, PathKind, RoomKind
    from .runtime_mode import is_eval_mode

    sig = engine.store.get_signal(signal_id)
    if not sig:
        return {"signal_id": signal_id, "status": "skipped", "reason": "missing"}
    if sig.status == SignalStatus.SUPPRESSED:
        return {"signal_id": signal_id, "status": "skipped", "reason": "suppressed"}

    for inv in engine.store.list_investigations():
        if signal_id in inv.originating_signal_ids and investigation_is_stalled(engine, inv):
            return finish_stalled_investigation(engine, inv)

    if signal_has_open_investigation(engine, signal_id):
        return {"signal_id": signal_id, "status": "skipped", "reason": "already_investigating"}

    tenant_id = tenant_id_from_signal(sig)
    event = anomaly_event_from_signal(sig, tenant_id=tenant_id)
    scenario = f"t:{tenant_id}:{sig.metric}" if tenant_id else f"auto:{sig.metric}:{signal_id[:8]}"
    loop_type = LoopType.TYPE_A if float(sig.magnitude) < 0 else LoopType.TYPE_B
    path = PathKind.BUG if float(sig.magnitude) < 0 else PathKind.FEATURE
    room_kind = RoomKind.INCIDENT if float(sig.magnitude) < 0 else RoomKind.OPPORTUNITY

    out = run_investigation(
        engine,
        event,
        scenario_id=scenario,
        tenant_id=tenant_id,
        propose_action=float(sig.magnitude) < 0,
        loop_type=loop_type,
        path=path,
        room_kind=room_kind,
        live_progress=True,
        async_finish=False,
        existing_signal=sig,
    )
    if out.get("reused"):
        return {"signal_id": signal_id, "status": "skipped", "reason": "room_reused"}

    inv = engine.store.get_investigation(out["investigation_id"])
    if not inv:
        return {"signal_id": signal_id, "status": "failed", "reason": "no_investigation"}

    hyp = engine.store.list_hypotheses(inv.id)
    if not hyp:
        record(
            engine.store,
            actor="signal_agent",
            action="auto_investigate.gate_failed",
            resource=f"signal:{signal_id}",
            detail={"investigation_id": inv.id},
        )
        return {
            "signal_id": signal_id,
            "status": "failed",
            "reason": "three_source_gate",
            "investigation_id": inv.id,
            "room_id": out.get("room_id"),
        }

    actions = engine.store.list_actions(inv.id)
    action = actions[0] if actions else None
    low_exec = False
    if action:
        low_exec = engine.auto_execute_low_tier(action) if action.risk_tier.value == "LOW" else False

    if is_eval_mode() and inv.scenario_id == "safari_3ds":
        from .world import publish_safari_room

        publish_safari_room(engine, inv)

    record(
        engine.store,
        actor="signal_agent",
        action="auto_investigate.completed",
        resource=f"investigation:{inv.id}",
        detail={
            "signal_id": signal_id,
            "action_id": action.id if action else None,
            "risk_tier": action.risk_tier.value if action else None,
            "low_auto_executed": low_exec,
        },
    )
    return {
        "signal_id": signal_id,
        "status": "applied",
        "investigation_id": inv.id,
        "room_id": out.get("room_id"),
        "action_id": action.id if action else None,
        "awaiting_approval": bool(action and action.status == "awaiting_approval"),
        "low_auto_executed": low_exec,
    }


def open_signal_ids_for_auto_investigate(engine: Any, detected: list[Any] | None = None) -> list[str]:
    """Signals that still need the unified pipeline — warehouse detect + tenant ingest orphans."""
    if detected is None:
        detected = engine.detect_all_signals()
    investigated_ids = {
        sid
        for inv in engine.store.list_investigations()
        for sid in inv.originating_signal_ids
        if not investigation_is_stalled(engine, inv)
    }
    open_ids: list[str] = []
    seen: set[str] = set()
    for s in detected:
        if getattr(s, "status", None) == "suppressed":
            continue
        if s.id in investigated_ids or s.id in seen:
            continue
        open_ids.append(s.id)
        seen.add(s.id)
    for s in engine.store.list_signals():
        if getattr(s, "status", None) == "suppressed":
            continue
        if s.id in investigated_ids or s.id in seen:
            continue
        src = str(getattr(s, "source", "") or "")
        if src.startswith("tenant.") or src.startswith("onboard."):
            open_ids.append(s.id)
            seen.add(s.id)
    return open_ids


def auto_investigate_new_signals(engine: Any, signal_ids: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    results.extend(finish_stalled_investigations(engine))
    for sid in sorted(signal_ids):
        try:
            results.append(auto_investigate_signal(engine, sid))
        except Exception as exc:
            from .audit import record

            record(
                engine.store,
                actor="signal_agent",
                action="auto_investigate.error",
                resource=f"signal:{sid}",
                detail={"error": str(exc)[:240]},
            )
            results.append({"signal_id": sid, "status": "error", "error": str(exc)[:240]})
    return results


def count_applied(results: list[dict[str, Any]]) -> int:
    return len([r for r in results if r.get("status") == "applied"])
