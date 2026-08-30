"""Generic research infra — any event shape, not the abandon recipe."""

from __future__ import annotations

from loop.customer_research import (
    ResearchEvent,
    extract_structured_evidence,
    run_customer_research,
    run_probes,
    simulate_research_dialogue,
    telephony_capabilities,
)
from loop.models import LoopType, PathKind, RoomKind


def test_probes_read_dimensions_not_hardcoded_user():
    event = ResearchEvent(
        kind="onboarding_drop",
        user_id="u_99",
        dimensions={
            "ga4_events": ["tutorial_begin"],
            "ga4_missing": ["tutorial_complete"],
            "device": {"model": "iPhone"},
            "app_version": "1.0.0",
            "journey": ["install", "tutorial"],
            "technical": {"crash": False},
            "previous_behavior": {"successful_purchases": 0},
        },
        memory_conditions=["funnel=onboarding"],
    )
    sources = {s.source: s for s in run_probes(event)}
    assert "GA4 events" in sources
    assert "tutorial_begin" in sources["GA4 events"].claim
    assert "iPhone" in sources["device"].claim


def test_run_customer_research_generic_event(engine):
    event = ResearchEvent(
        kind="feature_confusion",
        user_id="u_42",
        title="Feature confusion · u_42",
        topic="Repeated help opens on settings",
        metric="help_opens",
        funnel_position="settings",
        memory_conditions=[],
        loop_type=LoopType.TYPE_B,
        path=PathKind.FEATURE,
        room_kind=RoomKind.RESEARCH,
        dimensions={
            "acquisition": {"channel": "organic"},
            "device": {"model": "Pixel"},
            "app_version": "2.1",
            "journey": ["home", "settings", "help"],
            "ga4_claim": "help_open x4 in session",
            "hypothesis": {"statement": "Copy is unclear on settings.", "confidence": 0.6},
            "call_goal": "Confirm which label confused them",
            "call_questions": ["Which setting felt unclear?", "Did you find what you needed?", "Would a tooltip help?"],
            "demo_replies": ["Ok.", "The privacy toggle.", "Not really.", "Yes."],
            "product": "Acme",
        },
    )
    out = run_customer_research(engine, event)
    assert out["scenario"] == "research:feature_confusion"
    assert out["event"]["kind"] == "feature_confusion"
    assert out["structured"] is not None
    room = engine.store.get_room(out["room_id"])
    assert room is not None
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "customer_brief" in kinds
    assert "call_evidence" in kinds


def test_telephony_capabilities_shape():
    caps = telephony_capabilities()
    assert caps["google_telephony"]["outbound"] is False
    assert "inbound" in caps["google_telephony"]
    assert caps["default_mode"] in {"twilio_outbound", "google_inbound_callback", "simulated"}


def test_evidence_from_generic_dialogue():
    turns = simulate_research_dialogue(
        {
            "user_id": "u",
            "event_kind": "x",
            "call_plan": {
                "opening": "Hi",
                "questions": ["Error or loading?", "Try again?", "Finished?"],
            },
            "raw": {
                "dimensions": {
                    "demo_replies": ["Sure", "It kept loading", "Yes twice", "No I gave up"],
                }
            },
        }
    )
    ev = extract_structured_evidence(turns)
    assert ev.reason == "payment_timeout"
    assert ev.friction == "technical"
