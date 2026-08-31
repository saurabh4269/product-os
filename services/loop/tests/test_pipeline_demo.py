"""Pipeline board, activity feed, demo runner, unified signals."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod


def test_pipeline_and_activity_endpoints(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        pipe = client.get("/api/pipeline")
        assert pipe.status_code == 200
        assert "columns" in pipe.json()
        assert isinstance(pipe.json()["cards"], list)
        act = client.get("/api/activity")
        assert act.status_code == 200
        assert "events" in act.json()
        cfg = client.get("/api/config")
        assert cfg.status_code == 200
        assert "eval_mode" in cfg.json()


def test_demo_run_opens_room(engine, monkeypatch):
    from loop.tenant import hash_token

    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.store.put_tenant(
        __import__("loop.tenant", fromlist=["Tenant"]).Tenant(
            id="acme",
            name="Demo",
            product="Demo",
            token_hash=hash_token("tok"),
            repo="acme/app",
        )
    )
    with TestClient(api_mod.app) as client:
        res = client.post("/api/demo/run")
        assert res.status_code == 200
        body = res.json()
        assert body["demo"] is True
        assert body["room_id"]


def test_async_finish_returns_room_before_approval(engine, monkeypatch):
    """Demo path opens the room immediately; investigators finish in the background."""
    import time

    from loop.tenant import Tenant, hash_token
    from loop.world import ingest_tenant_signal

    monkeypatch.setenv("LOOP_DEMO_STAGED", "1")
    monkeypatch.setenv("LOOP_DEMO_STAGE_MS", "30")
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="a/b", token_hash=hash_token("x"), connected=True, warehouse_mode="file")
    )
    t0 = time.time()
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.12,
        baseline=0.7,
        async_finish=True,
    )
    assert out["async"] is True
    assert out["room_id"]
    assert time.time() - t0 < 2.5
    # Background should propose an action
    deadline = time.time() + 8
    while time.time() < deadline:
        inv = engine.store.get_investigation(out["investigation_id"])
        acts = engine.store.list_actions(inv.id) if inv else []
        if acts:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("background investigation never proposed an action")
    assert engine.store.list_messages(out["room_id"])


def test_post_signal_uses_investigation_pipeline(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        res = client.post(
            "/api/signals",
            json={
                "metric": "signup_rate",
                "delta": -0.1,
                "polarity": "negative",
                "scenario": "signal:signup_rate",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["room_id"]
        room = engine.store.get_room(body["room_id"])
        assert room and room.investigation_id


def test_pipeline_card_enrichment(engine, monkeypatch):
    from datetime import UTC, datetime

    from loop.models import RoomMessage

    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open")
    engine.store.put_message(
        RoomMessage(
            id="msg-voice",
            room_id=room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text="Safari users abandon at 3DS challenge screen",
            artifact_type="voice",
            artifact={"severity": "high", "phone": "4155550199"},
            created_at=datetime.now(UTC),
        )
    )
    engine.store.put_message(
        RoomMessage(
            id="msg-contact",
            room_id=room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="chat",
            text="Looked up the customer contact in memory. Callback number is +14155550199.",
            artifact_type="contact_lookup",
            artifact={"phone": "+14155550199", "found": True},
            created_at=datetime.now(UTC),
        )
    )
    engine.store.put_message(
        RoomMessage(
            id="msg-feedback",
            room_id=room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="chat",
            text="Customer said: The 3DS screen froze after I entered my card.",
            artifact_type="call_feedback",
            artifact={"status": "completed"},
            created_at=datetime.now(UTC),
        )
    )
    engine.store.put_message(
        RoomMessage(
            id="msg-cal",
            room_id=room.id,
            author="coordination",
            author_kind="agent",
            kind="artifact",
            text="Review hold",
            artifact_type="coordination",
            artifact={"slot": {"start": "2026-09-01T14:00:00+00:00"}},
            created_at=datetime.now(UTC),
        )
    )
    with TestClient(api_mod.app) as client:
        cards = client.get("/api/pipeline").json()["cards"]
        card = next(c for c in cards if c["room_id"] == room.id)
        assert "Safari" in (card.get("voice_snippet") or "")
        assert card.get("calendar_snippet", "").startswith("Hold")
        assert card.get("contact_phone") in {"4155550199", "+14155550199"}
        assert "3DS" in (card.get("call_feedback") or "")
        assert card.get("activity_line")


def test_room_by_scenario(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "safari_3ds")
    with TestClient(api_mod.app) as client:
        res = client.get("/api/rooms/by-scenario/safari_3ds")
        assert res.status_code == 200
        assert res.json()["room_id"] == room.id
