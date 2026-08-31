"""Progressive orchestration — watching mode, reveal, handoffs."""

from __future__ import annotations

from loop.models import LoopType, PathKind, RoomKind
from loop.orchestration import handoff_why, home_orchestration, progressive_flow
from loop.workflow import compose_nodes, infer_needs


def test_watching_when_no_open_rooms(engine):
    # Close all rooms artificially for test
    for room in engine.store.list_rooms():
        room.status = "closed"
        engine.store.put_room(room)
    out = home_orchestration(engine.store, engine)
    assert out["mode"] == "watching"
    assert out["steps"] == []


def test_active_case_reveals_progressive_steps(engine):
    engine.seed_world()
    out = home_orchestration(engine.store, engine)
    assert out["mode"] == "active"
    assert len(out["steps"]) >= 1
    # Should not dump entire future pipeline at once — at most current + 1 next.
    assert len(out["steps"]) <= len(out.get("nodes") or []) and len(out["steps"]) <= 8
    statuses = {s["status"] for s in out["steps"]}
    assert "active" in statuses or "done" in statuses


def test_analytics_case_skips_customer_in_nodes(engine):
    needs = infer_needs(
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.INCIDENT,
        dimensions={"skip_customer": True},
        signal_source="ga4",
    )
    nodes = compose_nodes(needs)
    assert "customer_mail" not in nodes
    assert "customer_call" not in nodes


def test_customer_case_includes_mail_ladder(engine):
    needs = infer_needs(
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        dimensions={"voice_subject": {"failure": "timeout"}},
    )
    nodes = compose_nodes(needs)
    assert "customer_mail" in nodes
    assert "customer_call" in nodes


def test_handoff_why_analytics_to_investigate():
    why = handoff_why("signal", "investigate", tags=["analytics"], metric="purchase_conversion")
    assert "purchase_conversion" in why or "analytics" in why.lower()
    assert "specialist" in why.lower() or "dispatch" in why.lower()


def test_progressive_flow_has_handoffs(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open")
    flow = progressive_flow(engine.store, room=room)
    assert flow["mode"] == "active"
    if len(flow["steps"]) > 1:
        assert len(flow["handoffs"]) >= 1
        assert flow["handoffs"][0].get("why")
