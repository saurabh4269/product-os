from loop.engine import LoopEngine
from loop.office import agent_snapshot, office_snapshot


def test_office_shows_working_agents_and_handoffs(engine: LoopEngine):
    engine.seed_world()
    snap = office_snapshot(engine)
    assert len(snap["desks"]) >= 12
    assert snap["working"] >= 4
    assert snap["handoffs"]
    analytics = next(d for d in snap["desks"] if d["id"] == "analytics_agent")
    assert analytics["status"] == "working"
    assert analytics["room_id"]
    assert analytics["doing"]
    assert any(h["from_agent"] == "orchestrator" for h in snap["handoffs"])


def test_agent_page_has_that_bots_chat_and_handoffs(engine: LoopEngine):
    engine.seed_world()
    snap = agent_snapshot(engine, "analytics")
    assert snap
    assert snap["agent"]["id"] == "analytics_agent"
    assert snap["messages"]
    assert snap["handoffs"]
    assert snap["desk"]["status"] == "working"
    assert any(r["kind"] == "incident" for r in snap["rooms"])


def test_unknown_agent_is_missing(engine: LoopEngine):
    engine.seed_world()
    assert agent_snapshot(engine, "not_a_real_bot") is None
