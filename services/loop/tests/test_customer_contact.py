from __future__ import annotations

from datetime import datetime, timezone

from loop.customer_contact import feedback_summary_from_transcript, resolve_callback_phone
from loop.models import RoomMessage
from loop.tenant import ConnectorReport, Tenant
from loop.world import ingest_tenant_voice


def test_resolve_phone_from_room_message(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms())
    engine.store.put_message(
        RoomMessage(
            id="msg_phone_1",
            room_id=room.id,
            author="customer_voice",
            author_kind="agent",
            kind="chat",
            text="Checkout hung on 3DS",
            artifact_type="voice",
            artifact={"phone": "4155550199", "text": "Checkout hung on 3DS"},
            created_at=datetime.now(timezone.utc),
        )
    )
    out = resolve_callback_phone(engine.store, room.id)
    assert out["found"] is True
    assert out["phone"] == "+14155550199"


def test_place_call_resolves_cove_number(engine, monkeypatch):
    from loop import api as api_mod

    engine.seed_world()
    tenant = Tenant(id="acme", name="Acme", product="Cove", token_hash="x")
    engine.store.put_tenant(tenant)
    out = ingest_tenant_voice(
        engine,
        tenant,
        text="Pay button spun forever",
        phone="415-555-0100",
    )
    room_id = out["room_id"]
    captured: dict = {}

    def fake_place(tokenized_user, reason, *, to_number="", room_id="", product="", brief=None, system_prompt=""):
        captured["to_number"] = to_number
        return ConnectorReport(
            status="applied",
            connector="voice.place_call",
            detail=f"Outbound call started to {to_number}",
        )

    monkeypatch.setattr("loop.connectors.voice.place_call", fake_place)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)

    from fastapi.testclient import TestClient

    client = TestClient(api_mod.app)
    res = client.post("/api/calls", json={"room_id": room_id, "reason": "checkout", "to_number": "", "force": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["to_number"] == "+14155550100"
    assert captured["to_number"] == "+14155550100"
    assert body["resolved"]["found"] is True

    contact = client.get(f"/api/rooms/{room_id}/contact").json()
    assert contact["found"] is True
    assert contact["phone"] == "+14155550100"

    msgs = engine.store.list_messages(room_id)
    assert any("callback" in (m.text or "").lower() or "email" in (m.text or "").lower() for m in msgs)


def test_feedback_summary_natural_language():
    line = feedback_summary_from_transcript(
        [
            {"role": "agent", "text": "What happened at checkout?"},
            {"role": "customer", "text": "The 3DS screen froze after I entered my card."},
        ]
    )
    assert line.startswith("Customer said:")
    assert "3DS" in line
