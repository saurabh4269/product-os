"""Design intent pack — generic pipeline contracts from docs/DESIGN_INTENT.md."""

from __future__ import annotations

from loop.engine import LoopEngine
from loop.models import Classification, LoopType
from loop.registry import ENTRIES, by_id, gateway_allows
from loop.world import MEMORY_KINDS

NAMED_SPECIALISTS = {
    "signal_agent",
    "investigator_agent",
    "analytics_agent",
    "logs_agent",
    "deployment_agent",
    "database_agent",
    "customer_voice_agent",
    "feedback_agent",
    "root_cause_agent",
    "code_agent",
    "test_agent",
    "product_agent",
    "risk_agent",
    "learning_agent",
    "orchestrator",
}

CUSTOMER_VOICE_FIELDS = {
    "reason",
    "severity",
    "purchase_intent",
    "friction",
    "competitor_mentioned",
    "feature_request",
    "willing_to_retry",
    "confidence",
}


def test_registry_lists_named_specialists():
    ids = set(by_id())
    assert NAMED_SPECIALISTS <= ids
    for entry in ENTRIES:
        assert entry.owner
        assert entry.capabilities
        assert entry.permissions_allow is not None
        assert entry.permissions_deny is not None
        assert entry.version
        assert entry.risk_level
        assert entry.status
        assert entry.identity


def test_gateway_identity_denies_cross_boundary():
    assert gateway_allows("analytics_agent", "gmail.send") is False
    assert gateway_allows("analytics_agent", "github.write") is False
    assert gateway_allows("code_agent", "customer_data.read") is False
    assert gateway_allows("code_agent", "github.write") is True


def test_customer_voice_structured_evidence_shape(engine: LoopEngine):
    engine.seed_world()
    voice_msgs = [
        m
        for r in engine.store.list_rooms()
        for m in engine.store.list_messages(r.id)
        if m.artifact_type in {"call_evidence", "customer_brief"}
        or (m.artifact and isinstance(m.artifact.get("structured"), dict))
    ]
    structured_found = False
    for m in voice_msgs:
        art = m.artifact if isinstance(m.artifact, dict) else {}
        block = art.get("structured") if isinstance(art.get("structured"), dict) else art
        if not isinstance(block, dict):
            continue
        hits = CUSTOMER_VOICE_FIELDS & set(block.keys())
        if len(hits) >= 3:
            structured_found = True
            assert "reason" in block or "friction" in block
    ev = [
        e
        for inv in [engine.store.get_investigation(r.investigation_id) for r in engine.store.list_rooms() if r.investigation_id]
        if inv
        for e in engine.store.list_evidence(inv.id)
        if e.source_type == "customer_voice"
    ]
    assert structured_found or len(ev) >= 1


def test_four_memory_kinds_seeded(engine: LoopEngine):
    engine.seed_world()
    assert set(MEMORY_KINDS) == {"customer", "product", "engineering", "organizational"}
    kinds_present = set()
    for kind in MEMORY_KINDS:
        if engine.store.list_memory(kind=kind):
            kinds_present.add(kind)
    assert "organizational" in kinds_present
    assert len(kinds_present) >= 2


def test_type_a_vs_type_b_visible_on_rooms(engine: LoopEngine):
    engine.seed_world()
    rooms = [r for r in engine.store.list_rooms() if r.scenario_id and r.investigation_id]
    type_a = [r for r in rooms if r.loop_type == LoopType.TYPE_A]
    type_b = [r for r in rooms if r.loop_type == LoopType.TYPE_B]
    assert len(type_a) >= 2
    assert len(type_b) >= 1

    bug_room = type_a[0]
    feat_room = type_b[0]
    assert bug_room.loop_type == LoopType.TYPE_A
    assert feat_room.loop_type == LoopType.TYPE_B

    bug_inv = engine.store.get_investigation(bug_room.investigation_id)
    feat_inv = engine.store.get_investigation(feat_room.investigation_id)
    assert bug_inv and feat_inv

    bug_hyps = engine.store.list_hypotheses(bug_inv.id)
    feat_hyps = engine.store.list_hypotheses(feat_inv.id)
    assert bug_hyps
    assert feat_hyps
    assert bug_hyps[0].classification == Classification.BUG
    assert feat_hyps[0].classification == Classification.OPPORTUNITY


def test_risk_tiers_assigned_not_prompt_only(engine: LoopEngine):
    engine.seed_world()
    actions = engine.store.list_actions()
    tiers = {a.risk_tier.value for a in actions}
    assert "HIGH" in tiers
    high = next(a for a in actions if a.risk_tier.value == "HIGH")
    assert high.tier_rationale
    assert high.consequence


def test_memory_recall_on_similar_signal(engine: LoopEngine):
    engine.seed_world()
    recalled = []
    for room in engine.store.list_rooms():
        if not room.investigation_id:
            continue
        inv = engine.store.get_investigation(room.investigation_id)
        if inv and inv.recalled_lessons:
            recalled.append(inv)
    assert recalled, "seed world should attach recalled lessons to at least one investigation"
    assert any(
        isinstance(lesson, str) and lesson.strip()
        for inv in recalled
        for lesson in inv.recalled_lessons
    )


def test_gateway_deny_is_identity_not_prompt(engine: LoopEngine):
    engine.seed_world()
    verdicts = engine.store.list_verdicts()
    deny = [v for v in verdicts if v.verdict == "DENY"]
    assert deny
    text = " ".join((v.rationale or "").lower() for v in deny)
    assert "gateway" in text or "identity" in text or "denied" in text
