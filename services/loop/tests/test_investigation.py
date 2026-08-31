"""Investigation infra — broad signals, fan-out, evidence, briefs, product intel."""

from __future__ import annotations

from loop.investigation import (
    AnomalyEvent,
    aggregate_evidence,
    assess_risk,
    build_code_brief,
    build_voice_context,
    catalog,
    cluster_feature_requests,
    example_feature_mentions,
    example_segmented_conversion_anomaly,
    run_investigation,
    run_investigators,
    run_product_intelligence,
    voice_system_prompt,
)
from loop.models import RiskTier, RoomKind


def test_signal_catalog_covers_four_families():
    cat = catalog()
    assert set(cat["families"]) >= {"funnel", "technical", "business", "customer"}
    assert "payment_abandoned" in {x["id"] for x in cat["families"]["funnel"]}
    assert "http_5xx" in {x["id"] for x in cat["families"]["technical"]}
    assert len(cat["investigators"]) == 6


def test_parallel_investigators_and_correlation(engine):
    event = example_segmented_conversion_anomaly()
    claims = run_investigators(event)
    assert {c.agent for c in claims} >= {
        "analytics_agent",
        "logs_agent",
        "deployment_agent",
        "database_agent",
        "customer_voice_agent",
        "code_agent",
    }
    pack = aggregate_evidence(event, claims)
    assert "Safari" in pack.correlation_summary
    assert "v2.14" in pack.correlation_summary
    assert pack.confidence >= 0.7
    assert pack.checklist["deployment_timing"]
    assert pack.checklist["segmentation"]


def test_run_investigation_produces_briefs(engine):
    out = run_investigation(engine, example_segmented_conversion_anomaly(), scenario_id="test_seg_conv")
    assert out["hypothesis"] is not None
    assert out["evidence"]["correlation_summary"]
    assert out["voice_context"]["device"]
    assert "callback" in " ".join(out["code_brief"]["likely_files"])
    assert out["risk"]["tier"] == "HIGH"
    assert out["risk"]["human_approval"] is True
    room = engine.store.get_room(out["room_id"])
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "evidence_pack" in kinds
    assert "voice_context" in kinds
    assert "code_brief" in kinds
    assert "hypothesis" in kinds


def test_investigate_accepts_flat_dimension_payload(engine):
    event = AnomalyEvent(
        kind="segmented_conversion_drop",
        metric="purchase_conversion",
        title="Conversion down on Safari mobile after release",
        family="business",
        magnitude=-0.19,
        baseline=0.72,
        funnel_position="checkout",
        polarity="negative",
        dimensions={
            "browser": "Safari",
            "os": "iOS 17",
            "deploy": "v2.14.0",
            "payment_method": "card",
        },
    )
    out = run_investigation(engine, event, propose_action=True, action_type="code_change", surface="checkout")
    assert out["room_id"]
    assert out["evidence"]["checklist"]["segmentation"] is True
    room = engine.store.get_room(out["room_id"])
    assert room is not None


def test_voice_prompt_is_diagnostic_not_survey():
    event = example_segmented_conversion_anomaly()
    pack = aggregate_evidence(event, run_investigators(event))
    ctx = build_voice_context(event, pack, "hyp")
    prompt = voice_system_prompt(ctx)
    assert "not a survey" in prompt.lower() or "diagnostic" in prompt.lower()
    assert ctx.adaptive_questions


def test_risk_policy_docs_vs_payment():
    low = assess_risk("docs / readme typo", "fix typo", "docs")
    high = assess_risk("payment authorization", "rollback pay path", "code_change")
    assert low.tier == RiskTier.LOW
    assert low.auto_test_pr is True
    assert high.tier == RiskTier.HIGH
    assert high.human_approval is True


def test_feature_cluster_not_n_issues(engine):
    mentions = example_feature_mentions()
    clusters = cluster_feature_requests(mentions, theme_override="Apple Pay")
    assert len(clusters) == 1
    assert clusters[0].frequency == 37
    out = run_product_intelligence(
        engine,
        mentions,
        theme="Apple Pay",
        scenario_id="test_apple_cluster",
        revenue_affected_usd=82000,
        competitor_capability=True,
    )
    assert out["proposal"]["cluster"]["frequency"] == 37
    assert "not 37 issues" in out["proposal"]["recommendation"].lower() or "One proposal" in out["proposal"]["recommendation"]
    room = engine.store.get_room(out["room_id"])
    assert room.kind == RoomKind.OPPORTUNITY
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "prd" in kinds


def test_apple_pay_fixture_uses_product_intel(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "apple_pay")
    assert room.loop_type.value == "type_b"
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "prd" in kinds


def test_code_brief_is_structured():
    event = example_segmented_conversion_anomaly()
    pack = aggregate_evidence(event, run_investigators(event))
    brief = build_code_brief(event, pack, "hyp")
    assert brief.likely_files
    assert brief.regression_test
    assert "fix payment bug" not in brief.issue.lower()
