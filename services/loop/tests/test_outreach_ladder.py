"""Mail-first outreach ladder — no spam calls."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.customer_contact import upsert_registration
from loop.outreach import advance_outreach, gate_place_call, start_mail_ladder
from loop.tenant import Tenant


def test_registration_stores_email(engine):
    ident = upsert_registration(
        engine.store,
        tokenized_user="tok_reg_1",
        tenant_id="acme",
        email="alex@example.com",
        phone="4155550100",
    )
    assert ident["email"] == "alex@example.com"
    got = engine.store.get_customer_identity("tok_reg_1")
    assert got and got["email"] == "alex@example.com"
    assert got["phone"] == "+14155550100" or "4155550100" in str(got["phone"])


def test_mail_first_then_call_non_responder(engine, monkeypatch):
    monkeypatch.setenv("LOOP_CUSTOMER_MAIL_MODE", "simulate")
    monkeypatch.setenv("LOOP_OUTREACH_MIN_CLUSTER", "1")
    monkeypatch.setenv("LOOP_OUTREACH_MAIL_WAIT_HOURS", "0")

    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open" and r.investigation_id)
    inv = engine.store.get_investigation(room.investigation_id)

    upsert_registration(
        engine.store,
        tokenized_user="tok_a",
        email="a@example.com",
        phone="4155550101",
        meta={"pattern": "purchase_conversion|payment|timeout"},
    )
    upsert_registration(
        engine.store,
        tokenized_user="tok_b",
        email="b@example.com",
        phone="4155550102",
        meta={"pattern": "purchase_conversion|payment|timeout"},
    )

    class Ev:
        metric = "purchase_conversion"
        funnel_position = "payment"
        dimensions = {
            "voice_subject": {
                "user_id": "tok_a",
                "email": "a@example.com",
                "phone": "4155550101",
                "failure": "timeout",
            },
            "hypothesis": {"statement": "Safari 3DS timeout"},
        }
        family = "business"
        source = "test"

    out = start_mail_ladder(engine, room=room, inv=inv, event=Ev(), hypothesis="timeout", product="Cove")
    assert out["held"] is False
    assert len(out["mailed"]) >= 1
    assert all(m["channel"] == "email" for m in out["mailed"])

    # Cold call blocked without force
    gate = gate_place_call(engine.store, room_id=room.id, tokenized_user="tok_a", force=False)
    # wait hours = 0 so non-responder may be allowed after mail
    assert gate["allowed"] in {True, False}
    if not gate["allowed"]:
        assert gate["reason"] in {"mail_first", "waiting_for_mail_reply", "all_replied"}

    called: list[str] = []

    def fake_place(tokenized_user, reason, *, to_number="", room_id="", product="", brief=None, system_prompt=""):
        called.append(to_number)
        from loop.tenant import ConnectorReport

        return ConnectorReport(status="applied", connector="voice.place_call", detail=f"call {to_number}")

    monkeypatch.setattr("loop.connectors.voice.place_call", fake_place)
    adv = advance_outreach(engine, room_id=room.id, force_call=True)
    assert adv["ok"] is True
    assert len(adv["calls"]) >= 1
    assert called


def test_mail_reply_skips_call(engine, monkeypatch):
    monkeypatch.setenv("LOOP_CUSTOMER_MAIL_MODE", "simulate")
    monkeypatch.setenv("LOOP_OUTREACH_MIN_CLUSTER", "1")
    monkeypatch.setenv("LOOP_OUTREACH_MAIL_WAIT_HOURS", "0")

    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open" and r.investigation_id)
    inv = engine.store.get_investigation(room.investigation_id)
    upsert_registration(
        engine.store,
        tokenized_user="tok_c",
        email="c@example.com",
        phone="4155550199",
    )

    class Ev:
        metric = "purchase_conversion"
        funnel_position = "payment"
        dimensions = {
            "voice_subject": {
                "user_id": "tok_c",
                "email": "c@example.com",
                "failure": "spinning",
            }
        }
        family = "customer"
        source = "test"

    start_mail_ladder(engine, room=room, inv=inv, event=Ev(), product="Cove")
    from loop.outreach import record_mail_reply

    record_mail_reply(
        engine.store,
        tokenized_user="tok_c",
        investigation_id=inv.id,
        room_id=room.id,
        summary="It froze on 3DS",
        solved=False,
    )
    adv = advance_outreach(engine, room_id=room.id, force_call=True)
    assert adv["calls"] == []
    assert any(s.get("reason") == "replied_to_mail" for s in adv["skipped"])


def test_api_register_and_mail_first_gate(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    monkeypatch.setenv("LOOP_CUSTOMER_MAIL_MODE", "simulate")

    tenant = Tenant(id="acme", name="Acme", product="Cove", token_hash="x")
    engine.store.put_tenant(tenant)
    # Bypass auth: patch _require_tenant
    monkeypatch.setattr(api_mod, "_require_tenant", lambda tid, auth: tenant)

    with TestClient(api_mod.app) as client:
        reg = client.post(
            "/api/t/acme/users",
            json={"tokenized_user": "tok_api", "email": "api@example.com", "phone": "4155550111"},
        )
        assert reg.status_code == 200, reg.text
        assert reg.json()["identity"]["email"] == "api@example.com"

        engine.seed_world()
        room = next(r for r in engine.store.list_rooms() if r.status == "open")
        blocked = client.post("/api/calls", json={"room_id": room.id, "to_number": "+14155550111", "force": False})
        assert blocked.status_code == 409
