"""Customer Voice live path — adaptive questions in simulated dialogue."""

from __future__ import annotations

from datetime import datetime, timezone

from loop.customer_research import extract_structured_evidence, simulate_research_dialogue
from loop.investigation import aggregate_evidence, build_voice_context, example_segmented_conversion_anomaly, run_investigators


def test_live_brief_shape_runs_adaptive_diagnostic_dialogue():
    """Mirrors customer_voice_live brief wiring — empty call_plan.questions must not 2-turn stub."""
    event = example_segmented_conversion_anomaly()
    pack = aggregate_evidence(event, run_investigators(event))
    voice_ctx = build_voice_context(event, pack, "pay-sdk callback regression")
    dims = event.dimensions
    voice_sub = dict(dims.get("voice_subject") or {})
    brief = {
        "title": f"Diagnostic · {event.metric}",
        "user_id": "customer",
        "event_kind": event.kind,
        "device": {"label": voice_ctx.device},
        "hypothesis": {"statement": voice_ctx.hypothesis_hint},
        "journey": [event.funnel_position],
        "raw": {"dimensions": {"voice_subject": voice_sub, **voice_sub}},
        "observed": {
            "metric": event.metric,
            "magnitude": event.magnitude,
            "failure": voice_ctx.failure,
            "attempt_summary": voice_ctx.attempt_summary,
        },
        "call_plan": {
            "opening": voice_ctx.opening,
            "questions": list(voice_ctx.adaptive_questions),
            "adaptive_questions": list(voice_ctx.adaptive_questions),
        },
    }
    turns = simulate_research_dialogue(brief)
    agent_msgs = [t["message"] for t in turns if t["role"] == "agent"]
    assert len(agent_msgs) >= 3
    assert any("loading" in m.lower() or "error" in m.lower() for m in agent_msgs[1:])
    ev = extract_structured_evidence(turns)
    assert ev.reason in {"payment_timeout", "card_not_detected"}
    assert ev.reason != "unknown_friction"
