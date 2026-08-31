from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.live_work import build_live_work, card_from_message
from loop.models import RoomMessage
from loop.world import post


def test_live_work_endpoint_piles_receipts(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open")
    post(
        engine,
        room.id,
        author="analytics_agent",
        author_kind="agent",
        kind="artifact",
        text="BigQuery read checkout_conversion · Chrome · last 7d",
        artifact_type="warehouse",
        artifact={"metric": "checkout_conversion", "source": "bigquery"},
    )
    post(
        engine,
        room.id,
        author="code_agent",
        author_kind="agent",
        kind="artifact",
        text="Opened draft PR for SDK rollback",
        artifact_type="pr",
        artifact={"pr_url": "https://github.com/saurabh4269/cove/pull/9"},
    )
    post(
        engine,
        room.id,
        author="coordination_agent",
        author_kind="agent",
        kind="artifact",
        text="Mail sent to you@example.com: [LOOP] review",
        artifact_type="mail",
        artifact={
            "channel": "gmail",
            "gmail_url": "https://mail.google.com/mail/u/0/#inbox/abc",
            "report": {"status": "applied", "connector": "mail.send"},
        },
    )
    with TestClient(api_mod.app) as client:
        res = client.get("/api/live-work")
        assert res.status_code == 200
        body = res.json()
        assert [c["id"] for c in body["columns"]]
        assert set(c["id"] for c in body["columns"]).issubset(
            {"signal", "evidence", "customer", "code", "experiment", "approve", "verify"}
        )
        cards = body["cards"]
        assert any(c["badge"] == "BigQuery" and c["column"] == "evidence" for c in cards)
        assert any(c["badge"] == "PR open" and c["column"] == "code" and c.get("pr_url") for c in cards)
        assert any(c["badge"] == "Mail sent" and c["column"] == "verify" for c in cards)


def test_card_from_message_contact_phone():
    msg = RoomMessage(
        id="m1",
        room_id="r1",
        author="customer_voice_agent",
        author_kind="agent",
        kind="chat",
        text="Saved callback number +14155550100 from Cove feedback.",
        artifact_type="contact",
        artifact={"phone": "+14155550100"},
        created_at=datetime.now(UTC),
    )
    card = card_from_message(msg, room_title="Cove feedback")
    assert card is not None
    assert card["column"] == "customer"
    assert card["phone"] == "+14155550100"


def test_build_live_work_empty_store(engine):
    out = build_live_work(engine.store)
    assert out["columns"]
    assert isinstance(out["cards"], list)
