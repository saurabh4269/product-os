"""Classifier + telephony skip paths (no Twilio required in CI)."""

from __future__ import annotations

from datetime import UTC, datetime

from loop.classify import classify_call_outcome, classify_voice
from loop.connectors.voice import place_call
from loop.models import Investigation, InvestigationState, LoopType, PathKind, Room, RoomKind
from loop.outreach import (
    _generic_fallback_brief,
    call_brief_for_outreach,
    contains_spoken_placeholder,
    room_call_context,
    sanitize_call_script,
    sanitize_spoken_line,
)
from loop.telephony import (
    GATHER_TIMEOUT,
    TWILIO_VOICE,
    fix_notify_opening,
    normalize_e164,
    twiml_open,
)


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
    assert normalize_e164("+919508709729") == "+919508709729"
    assert normalize_e164("919508709729") == "+919508709729"
    assert normalize_e164("12") is None
    assert normalize_e164("+123") is None


def test_fix_notify_opening_is_generic():
    text = fix_notify_opening("Cove", "payment timeout regression")
    assert "Lexi" in text
    assert "fix" in text.lower()
    assert "OTP" not in text
    assert "spinner" not in text.lower()


def test_call_brief_fix_notify_distinct_from_feedback():
    fix = call_brief_for_outreach({"purpose": "fix_notify", "product": "Cove"})
    ask = call_brief_for_outreach({"purpose": "feedback_ask", "product": "Cove"})
    assert fix["purpose"] == "fix_notify"
    assert ask["purpose"] == "feedback_ask"
    assert fix["opening"] != ask["opening"]
    assert "OTP" not in fix["opening"]
    assert "spinner" not in fix["opening"].lower()
    assert "otp_verify" not in fix["opening"].lower()
    assert len(fix["questions"]) >= 2


def test_generic_fallback_brief_has_no_scenario_nouns():
    brief = _generic_fallback_brief(
        {"product": "Acme", "metric": "checkout_drop", "hypothesis": "SDK regression"},
        "feedback_ask",
    )
    blob = f"{brief['opening']} {' '.join(brief['questions'])}"
    for banned in ("otp_verify", "spinner", "OTP", "verification code"):
        assert banned not in blob


def test_room_call_context_uses_hypothesis_and_voice_reason(engine):
    inv = Investigation(
        id="inv_ctx",
        originating_signal_ids=[],
        state=InvestigationState.GATHERING,
        opened_at=datetime.now(UTC),
        invocation_id="x",
        scenario_id="t:acme:payment_timeout_q3",
        tenant_id="acme",
        title="Acme: payment_timeout_q3",
        room_id="room_ctx",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_ctx",
            title="Payment timeout",
            topic="payment",
            kind=RoomKind.INCIDENT,
            created_at=datetime.now(UTC),
            investigation_id=inv.id,
            members=["you"],
        )
    )
    from loop.models import Classification, Hypothesis

    engine.store.put_hypothesis(
        Hypothesis(
            id="hyp_ctx",
            investigation_id=inv.id,
            statement="Payment authorize callback stalls on slow networks",
            confidence=0.82,
            classification=Classification.BUG,
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            cited_memory=[],
            rank=1,
            independence_groups=["analytics"],
        )
    )
    from loop.world import post

    post(
        engine,
        "room_ctx",
        author="customer_voice_agent",
        author_kind="agent",
        kind="artifact",
        text="Diagnostic context ready",
        artifact_type="voice_context",
        artifact={
            "failure": "payment_timeout",
            "hypothesis_hint": "Payment authorize callback stalls on slow networks",
        },
    )
    ctx = room_call_context(engine.store, "room_ctx")
    assert ctx["metric"] == "payment_timeout_q3"
    assert "callback" in ctx["hypothesis"].lower()
    assert ctx["voice_reason"] == "payment_timeout"


def test_call_brief_uses_room_context(engine, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LOOP_USE_VERTEX", "0")

    inv = Investigation(
        id="inv_brief",
        originating_signal_ids=[],
        state=InvestigationState.GATHERING,
        opened_at=datetime.now(UTC),
        invocation_id="x",
        scenario_id="t:acme:shipping_delay",
        tenant_id="acme",
        title="Acme: shipping_delay",
        room_id="room_brief",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_brief",
            title="Shipping delay",
            topic="shipping",
            kind=RoomKind.INCIDENT,
            created_at=datetime.now(UTC),
            investigation_id=inv.id,
            members=["you"],
        )
    )
    from loop.models import Classification, Hypothesis

    engine.store.put_hypothesis(
        Hypothesis(
            id="hyp_brief",
            investigation_id=inv.id,
            statement="ETA calculation uses stale warehouse cutoff",
            confidence=0.75,
            classification=Classification.BUG,
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            cited_memory=[],
            rank=1,
            independence_groups=["analytics"],
        )
    )

    brief = call_brief_for_outreach(
        {"purpose": "feedback_ask", "product": "Acme"},
        store=engine.store,
        room_id="room_brief",
    )
    assert brief["hypothesis"] == "ETA calculation uses stale warehouse cutoff"
    assert brief["metric"] == "shipping_delay"
    blob = f"{brief['opening']} {' '.join(brief['questions'])}"
    assert "otp_verify" not in blob.lower()
    assert "spinner" not in blob.lower()


def test_sanitize_spoken_line_strips_bracket_placeholders():
    raw = (
        "Hi [Customer Name], this is Lexi from the Cove product team. "
        "I'm calling about the feedback you shared – do you have about 30 seconds?"
    )
    cleaned = sanitize_spoken_line(raw)
    assert "[" not in cleaned
    assert "]" not in cleaned
    assert "Customer Name" not in cleaned
    assert contains_spoken_placeholder(cleaned) is False


def test_sanitize_spoken_line_strips_curly_name():
    cleaned = sanitize_spoken_line("Hi {name}, quick question from Lexi.")
    assert "{" not in cleaned
    assert "}" not in cleaned
    assert contains_spoken_placeholder(cleaned) is False


def test_sanitize_call_script_rejects_vague_feedback_and_placeholders():
    ctx = {"product": "Cove", "voice_reason": "otp_verify_timeout", "metric": "otp_verify_hang"}
    plan = {
        "opening": (
            "Hi [Customer Name], this is Lexi from the Cove product team. "
            "I'm calling about the feedback you shared – do you have about 30 seconds?"
        ),
        "questions": ["What happened?"],
        "listen_prompt": "Go ahead.",
    }
    cleaned = sanitize_call_script(plan, ctx, purpose="feedback_ask")
    assert "[" not in cleaned["opening"]
    assert "]" not in cleaned["opening"]
    assert "feedback you shared" not in cleaned["opening"].lower()
    blob = f"{cleaned['opening']} {' '.join(cleaned['questions'])}".lower()
    assert "otp" in blob or "verify" in blob or "timeout" in blob


def test_call_brief_gemini_placeholder_stripped(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    def _fake_generate(prompt: str, *, timeout: float = 90.0) -> str:
        assert "NEVER use placeholder names" in prompt
        return (
            '{"opening": "Hi [Customer Name], this is Lexi from Cove. '
            'Calling about the feedback you shared.", '
            '"questions": ["What did you see?"], '
            '"listen_prompt": "Tell me what happened."}'
        )

    monkeypatch.setattr("loop.vertex_gemini.generate_content", _fake_generate)
    monkeypatch.setattr("loop.vertex_gemini.gemini_configured", lambda: True)

    brief = call_brief_for_outreach(
        {
            "purpose": "feedback_ask",
            "product": "Cove",
            "metric": "otp_verify_hang",
            "voice_reason": "otp_verify_timeout",
        },
    )
    assert brief["gemini_generated"] is True
    assert "[" not in brief["opening"]
    assert "]" not in brief["opening"]
    assert "feedback you shared" not in brief["opening"].lower()
    blob = f"{brief['opening']} {' '.join(brief['questions'])}".lower()
    assert "otp" in blob or "verify" in blob or "timeout" in blob


def test_call_brief_fallback_reflects_voice_reason():
    brief = call_brief_for_outreach(
        {
            "purpose": "feedback_ask",
            "product": "Cove",
            "voice_reason": "payment_timeout",
        },
    )
    blob = f"{brief['opening']} {' '.join(brief['questions'])}".lower()
    assert "[" not in brief["opening"]
    assert "payment" in blob and "timeout" in blob


def test_call_brief_gemini_generated_when_available(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    def _fake_generate(prompt: str, *, timeout: float = 90.0) -> str:
        return (
            '{"opening": "Hi, Lexi from Acme. Quick question about your session?", '
            '"questions": ["What did you see?", "Did you retry?"], '
            '"listen_prompt": "Tell me what happened."}'
        )

    monkeypatch.setattr("loop.vertex_gemini.generate_content", _fake_generate)
    monkeypatch.setattr("loop.vertex_gemini.gemini_configured", lambda: True)

    brief = call_brief_for_outreach(
        {
            "purpose": "feedback_ask",
            "product": "Acme",
            "metric": "onboarding_drop",
            "hypothesis": "Step 3 form validation blocks mobile users",
            "voice_reason": "form_validation_error",
        },
    )
    assert brief["gemini_generated"] is True
    assert "Lexi" in brief["opening"]
    assert len(brief["questions"]) == 2
    assert "[" not in brief["opening"]
    assert "]" not in brief["opening"]


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
    assert f'voice="{TWILIO_VOICE}"' in xml
    assert f'timeout="{GATHER_TIMEOUT}"' in xml
    assert "After the tone" in xml
    assert "/api/twilio/gather" in xml
    assert "spinner" not in xml.lower()
    assert "OTP" not in xml


def test_twiml_open_uses_context_brief(monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    brief = call_brief_for_outreach(
        {
            "purpose": "fix_notify",
            "product": "Cove",
            "hypothesis": "Payment gateway timeout on slow networks",
            "fix_summary": "gateway timeout handling",
        },
    )
    xml = twiml_open("room1", "payment issue", "Cove", brief=brief)
    assert "Lexi" in xml
    assert "OTP verification" not in xml
    assert "spinner" not in xml.lower()
