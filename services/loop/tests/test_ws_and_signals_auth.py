"""WebSocket HTTP probes and production auth on /api/signals."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod


def test_ws_http_get_not_spa_html(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/ws")
        assert res.status_code == 405
        assert "<!DOCTYPE" not in res.text
        assert "WebSocket" in res.text


def test_ws_room_http_get_not_spa_html(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/ws/rooms/room_test")
        assert res.status_code == 405
        assert "<!DOCTYPE" not in res.text


def test_post_signals_requires_admin_when_not_eval(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        denied = client.post(
            "/api/signals",
            json={"metric": "signup_rate", "polarity": "negative", "domain": "business"},
        )
        assert denied.status_code == 401
        ok = client.post(
            "/api/signals",
            headers={"Authorization": "Bearer secret"},
            json={"metric": "signup_rate", "polarity": "negative", "domain": "business"},
        )
        assert ok.status_code == 200


def test_approval_invalid_decision_422(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "1")
    engine.seed_world()
    action = engine.store.pending_approvals()[0]
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        bad = client.post(
            f"/api/approvals/{action.id}",
            json={"decision": "maybe", "approver": "oncall@test", "rationale": "hmm"},
        )
        assert bad.status_code == 422
