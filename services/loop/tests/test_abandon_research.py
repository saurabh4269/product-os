"""Checkout abandon → brief → simulated research call → structured evidence."""

from __future__ import annotations

from loop.abandon_research import (
    build_customer_context_brief,
    extract_structured_evidence,
    run_abandon_research,
    simulate_research_dialogue,
)


def test_brief_has_hypothesis_and_call_plan():
    brief = build_customer_context_brief("8472")
    assert brief["user_id"] == "8472"
    assert brief["hypothesis"]["confidence"] == 0.78
    assert "loading" in brief["call_plan"]["questions"][0].lower() or "error" in brief["call_plan"]["questions"][0].lower()
    assert brief["memory_applied"]["returned"] is False


def test_structured_evidence_from_demo_dialogue():
    brief = build_customer_context_brief()
    turns = simulate_research_dialogue(brief)
    ev = extract_structured_evidence(turns)
    assert ev["reason"] == "payment_timeout"
    assert ev["purchase_intent"] == "high"
    assert ev["friction"] == "technical"
    assert ev["willing_to_retry"] is True
    assert ev["confidence"] >= 0.9
    assert ev["competitor_mentioned"] is False
    assert ev["feature_request"] is None


def test_run_abandon_research_room(engine):
    out = run_abandon_research(engine, user_id="8472")
    assert out["scenario"] == "checkout_abandon"
    room = engine.store.get_room(out["room_id"])
    assert room is not None
    assert room.scenario_id == "checkout_abandon"
    msgs = engine.store.list_messages(room.id)
    kinds = {m.artifact_type for m in msgs if m.artifact_type}
    assert "customer_brief" in kinds
    assert "call_evidence" in kinds
    assert "memory" in kinds
    assert out["structured"]["reason"] == "payment_timeout"
