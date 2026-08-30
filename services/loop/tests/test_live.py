"""Live hub, agent_callback, skip-if-done HITL, scenario run, ADK 2 workflows catalog."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.agents.workflows import build_hitl_gate_spec, workflow_catalog
from loop.live import HUB, funnel_for
from loop.models import InvestigationState, LoopType, RiskTier


def test_funnel_type_a_and_b():
    bug = funnel_for(LoopType.TYPE_A, InvestigationState.HYPOTHESIS)
    feat = funnel_for(LoopType.TYPE_B, InvestigationState.HYPOTHESIS)
    assert bug["kind"] == "bug"
    assert feat["kind"] == "feature"
    assert bug["current"] == "root_cause"
    assert feat["current"] == "product"
    assert bug["steps"][0]["on"] is True


def test_workflow_catalog_soft_fails_without_adk():
    cat = workflow_catalog()
    assert cat["adk_version"] == "2.x"
    assert "investigation_fanout" in cat
    assert build_hitl_gate_spec()["pattern"] == "RequestInput"


def test_agent_callback_sets_presence(engine, monkeypatch):
    engine.seed_world()
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    room = engine.store.list_rooms()[0]
    HUB.presence.clear()
    HUB.buffer.clear()
    with TestClient(api_mod.app) as client:
        assert api_mod.get_engine() is engine
        assert engine.store.get_room(room.id) is not None
        r = client.post(
            "/api/agent_callback",
            json={
                "room_id": room.id,
                "agent_id": "analytics_agent",
                "status": "thinking",
                "kind": "agent_presence",
                "message": "pulling GA4",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        agents = {p["agentId"]: p["status"] for p in body["presence"]}
        # Message path ends speaking (SalesShortcut push + world.post).
        assert agents.get("analytics_agent") in {"thinking", "speaking"}
        listed = client.get("/api/rooms").json()["rooms"]
        assert any(x["id"] == room.id for x in listed), (room.id, [x["id"] for x in listed[:3]])
        detail = client.get(f"/api/rooms/{room.id}").json()
        assert "funnel" in detail, detail
        assert "presence" in detail
        assert any(m.get("text") == "pulling GA4" for m in detail.get("messages") or [])


def test_scenario_run(engine, monkeypatch):
    engine.seed_world()
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        r = client.post("/api/scenarios/safari_3ds/run")
        assert r.status_code == 200
        body = r.json()
        assert body["scenario"] == "safari_3ds"
        assert body["room_id"]
        assert body["funnel"]["kind"] == "bug"
        assert len(body.get("pipeline") or []) >= 5
        assert "presence" in body
        bad = client.post("/api/scenarios/nope/run")
        assert bad.status_code == 404


def test_skip_if_done_approve(engine, monkeypatch):
    engine.seed_world()
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    engine.resume_after_approval(high.id, "oncall@acme")
    action = engine.store.get_action(high.id)
    assert action and action.status == "executed"
    with TestClient(api_mod.app) as client:
        again = client.post(
            f"/api/approvals/{high.id}",
            json={"decision": "approve", "approver": "oncall@acme", "rationale": "retry"},
        )
        assert again.status_code == 200
        body = again.json()
        assert body.get("reused") is True
        assert body.get("approval") == "approve"


def test_workflows_endpoint(monkeypatch, engine):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        r = client.get("/api/workflows")
        assert r.status_code == 200
        body = r.json()
        assert body["adk_version"] == "2.x"
        assert "JoinNode" in body["preferred_2x"]
        assert body["enterprise"]["mail_send"].startswith("denied")


def test_skip_if_done_helper():
    from loop.agents.callbacks import before_tool_skip_if_done, skip_if_done

    assert skip_if_done({"preview": "https://x"}, "preview") == "https://x"
    assert skip_if_done({}, "preview") is None
    reused = before_tool_skip_if_done(
        "phone_call_tool",
        {},
        {"call_result": {"status": "done"}},
        key="call_result",
        tools={"phone_call_tool"},
        done_values={"done", "completed"},
    )
    assert reused and reused["reused"] is True
