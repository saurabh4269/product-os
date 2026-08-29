"""Seeded regression detected unprompted; HIGH approval survives restart; verifies once."""

from __future__ import annotations

from loop.engine import LoopEngine
from loop.models import InvestigationState, RiskTier
from loop.store import Store
from loop.warehouse import Warehouse


def test_unprompted_safari_regression(engine: LoopEngine):
    signals = engine.detect_signals()
    assert signals, "seeded conversion regression must fire without a human hint"
    safari = [s for s in signals if any(seg.browser == "Safari" for seg in s.affected_segments)]
    assert safari, "G-3: a 3% aggregate drop concealing Safari must fire as a Safari signal"
    assert safari[0].direction.value == "negative"
    assert safari[0].magnitude < -0.12
    chrome = [s for s in signals if any(seg.browser == "Chrome" for seg in s.affected_segments)]
    assert not chrome


def test_full_loop_three_source_high_tier_verify(engine: LoopEngine):
    inv = engine.run_until_approval()
    assert inv.state == InvestigationState.AWAITING_APPROVAL
    evidence = engine.store.list_evidence(inv.id)
    groups = {e.independence_group for e in evidence if e.trust_level.value == "trusted"}
    assert {"analytics_ga4", "logs_errors", "deploy_timeline"} <= groups
    assert any(e.source_type == "customer_voice" for e in evidence)
    hyps = engine.store.list_hypotheses(inv.id)
    assert hyps
    assert len(hyps[0].independence_groups) >= 3
    verdicts = engine.store.list_verdicts()
    assert any(v.finding_type == "prompt_injection" and v.verdict == "BLOCK" for v in verdicts)
    actions = engine.store.list_actions(inv.id)
    assert actions[0].risk_tier == RiskTier.HIGH
    assert actions[0].status == "awaiting_approval"


def test_high_tier_blocks_survives_restart_resumes_once(tmp_path, warehouse_dir):
    db = tmp_path / "loop.db"
    eng = LoopEngine(Store(db), Warehouse(warehouse_dir))
    inv = eng.run_until_approval()
    action = eng.store.list_actions(inv.id)[0]
    assert action.status == "awaiting_approval"
    inv_id, action_id, key = inv.id, action.id, action.idempotency_key
    eng.store.close()

    eng2 = LoopEngine(Store(db), Warehouse(warehouse_dir))
    restored = eng2.store.get_investigation(inv_id)
    assert restored is not None
    assert restored.state == InvestigationState.AWAITING_APPROVAL
    action2 = eng2.store.get_action(action_id)
    assert action2 is not None
    assert action2.status == "awaiting_approval"

    try:
        eng2.execute_approved(action_id)
        raise AssertionError("HIGH-tier must not execute without approval")
    except PermissionError:
        pass

    out = eng2.resume_after_approval(action_id, "oncall@northstar")
    assert out.verdict.value == "RESOLVED"
    first = eng2.execute_approved(action_id)
    assert first["reused"] is True
    assert eng2.store.get_flag("pay_sdk_4_3") == "off"
    lessons = eng2.store.list_lessons()
    assert lessons
    assert "Safari" in lessons[0].statement or "3DS" in lessons[0].statement
    assert eng2.store.get_investigation(inv_id).state.value == "RESOLVED"
    _ = key
