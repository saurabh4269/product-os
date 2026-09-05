"""Classifier + telephony skip paths (no Twilio required in CI)."""

from __future__ import annotations

from loop.classify import classify_call_outcome, classify_voice
from loop.connectors.voice import place_call
from loop.models import LoopType, PathKind
from loop.telephony import normalize_e164, twiml_open


def test_classify_checkout_hang_is_type_a():
    out = classify_voice("Checkout hung on payment authorize screen")
    assert out["loop_type"] == LoopType.TYPE_A
    assert out["path"] == PathKind.BUG


def test_classify_apple_pay_wish_is_type_b():
    out = classify_voice("I wish you supported Apple Pay at checkout")
    assert out["loop_type"] == LoopType.TYPE_B
    assert out["path"] == PathKind.FEATURE


def test_classify_call_transcript():
    out = classify_call_outcome(
        [
            {"role": "agent", "message": "Did checkout hang?"},
            {"role": "user", "message": "Yes it timed out, please send a fix"},
        ]
    )
    assert out["interested"] is True
    assert out["kind"] in {"bug", "mixed"}


def test_normalize_phone():
    assert normalize_e164("5551234567") == "+15551234567"
    assert normalize_e164("+1 (555) 123-4567") == "+15551234567"
    assert normalize_e164("12") is None


def test_place_call_skips_without_twilio(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)
    report = place_call("tok", "checkout hung", to_number="+15551234567", room_id="room_x")
    assert report.status == "skipped"
    assert "Twilio" in report.detail


def test_place_call_skips_without_number():
    report = place_call("tok", "reason")
    assert report.status == "skipped"
    assert "phone" in report.detail.lower()


def test_finalize_call_uses_room_metric_for_otp_hang(engine, monkeypatch):
    from datetime import UTC, datetime

    from loop.models import Investigation, InvestigationState, Room, RoomKind
    from loop.telephony import finalize_call, put_session

    inv = Investigation(
        id="inv_otp_call",
        originating_signal_ids=[],
        state=InvestigationState.GATHERING,
        opened_at=datetime.now(UTC),
        invocation_id="x",
        scenario_id="t:acme:otp_verify_hang_0904",
        tenant_id="acme",
        title="Cove: otp_verify_hang_0904",
        room_id="room_otp_call",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_otp_call",
            title="OTP hang",
            topic="otp",
            kind=RoomKind.INCIDENT,
            created_at=datetime.now(UTC),
            investigation_id=inv.id,
            members=["you"],
        )
    )
    monkeypatch.setattr("loop.api.get_engine", lambda: engine)
    put_session(
        "CA_otp_test",
        {
            "room_id": "room_otp_call",
            "transcript": [
                {"role": "user", "message": "It kept loading after the code."},
                {"role": "agent", "message": "Did you try again?"},
                {"role": "user", "message": "Yes twice. I gave up."},
            ],
        },
    )
    out = finalize_call("CA_otp_test")
    assert out["ok"] is True
    assert out["structured"]["reason"] == "otp_verify_timeout"
    assert out["structured"]["reason"] != "payment_timeout"


def test_twiml_open_contains_gather(monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    xml = twiml_open("room1", "checkout hung", "Cove")
    assert "Gather" in xml
    assert "Say" in xml
    assert "/api/twilio/gather" in xml
