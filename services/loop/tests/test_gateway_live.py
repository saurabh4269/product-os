"""Gateway + live graph — product-os-v2 patterns."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.agents.graphs import run_live_graph
from loop.gateway import authorize


def test_gateway_denies_exfil():
    gate = authorize("code_agent", "customer_records.dump")
    assert gate.decision == "deny"
    assert "gateway deny" in gate.reason


def test_gateway_allows_analytics_read():
    gate = authorize("analytics_agent", "ga4.read")
    assert gate.decision == "allow"


def test_live_graph_posts_artifacts(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "safari_3ds")
    before = len(engine.store.list_messages(room.id))
    result = run_live_graph(
        engine,
        room.id,
        {
            "metric": "checkout_conversion",
            "delta": -0.22,
            "polarity": "negative",
            "source": "ga4",
            "dimensions": {"browser": "Safari", "hypothesis": "3DS hang after SDK bump"},
        },
        fork="BUG",
    )
    assert result["fork"] == "BUG"
    assert len(result["pipeline"]) >= 5
    after = engine.store.list_messages(room.id)
    assert len(after) > before
    kinds = {m.artifact_type for m in after if m.kind == "artifact"}
    assert "evidence" in kinds or "signal" in kinds
    assert "risk" in kinds or "hypothesis" in kinds


def test_post_signal_runs_graph(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        r = client.post(
            "/api/signals",
            json={
                "metric": "shipping_page_reopen",
                "polarity": "positive",
                "source": "posthog",
                "delta": 0.12,
                "title": "Shipping reopen opportunity",
                "dimensions": {"feature": "earlier delivery date"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["room_id"]
        assert body["fork"] == "FEATURE"
        assert body["steps"] >= 5
        detail = client.get(f"/api/rooms/{body['room_id']}").json()
        assert len(detail["messages"]) >= 3


def test_memory_remember(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        r = client.post(
            "/api/memory",
            json={"type": "engineering", "title": "SDK regressions need browser segments", "body": "Always segment."},
        )
        assert r.status_code == 200
        assert r.json()["title"].startswith("SDK")
        listed = client.get("/api/memory?q=SDK").json()
        assert any("SDK" in str(x.get("title", "")) for x in listed["memory"]["engineering"])


def test_exfil_scenario_denies(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        r = client.post("/api/scenarios/security_exfil/run")
        assert r.status_code == 200
        body = r.json()
        assert body.get("pipeline")
        detail = client.get(f"/api/rooms/{body['room_id']}").json()
        texts = " ".join(m.get("text", "") for m in detail["messages"])
        assert "DENY" in texts or any(m.get("artifact_type") == "deny" for m in detail["messages"])


def test_status_endpoint(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        r = client.get("/api/status")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert "rooms" in body
        assert "funnel" in body
        assert "parallel_fanout" in body["patterns"]


def test_feature_path_critique_output_keys(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "apple_pay")
    result = run_live_graph(
        engine,
        room.id,
        {
            "metric": "apple_pay_requests",
            "polarity": "positive",
            "delta": 0.37,
            "dimensions": {"feature": "Apple Pay", "hypothesis": "Add Apple Pay"},
        },
        fork="FEATURE",
    )
    assert result["fork"] == "FEATURE"
    assert "feedback_agent" in result["pipeline"]
    outputs = result.get("outputs") or {}
    assert outputs.get("proposal") or outputs.get("draft_proposal")
    assert "final_merged_evidence" in outputs or result.get("groups")
