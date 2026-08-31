"""Workflow link aggregation from coordination artifacts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.coordination import CoordinationRequest, run_coordination


def test_workflow_links_lists_calendar_compose(engine, monkeypatch):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "android_sdk")
    run_coordination(
        engine,
        CoordinationRequest(
            kind="review_request",
            title="Test review",
            room_id=room.id,
            risk_tier="HIGH",
            notify_channels=["room"],
            dimensions={
                "forced_slot": {
                    "start": "2026-08-29T16:00:00Z",
                    "end": "2026-08-29T16:45:00Z",
                }
            },
        ),
    )
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/api/workflows/links")
        assert res.status_code == 200
        body = res.json()
        assert "shortcuts" in body
        assert any(link["kind"] == "calendar" for link in body["links"])
