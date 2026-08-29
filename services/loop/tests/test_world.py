"""Six fixtures through one pipeline. Safari is a fixture, not the product."""

from __future__ import annotations

from loop.engine import LoopEngine
from loop.models import Classification, LoopType, RoomKind
from loop.registry import gateway_allows


def test_seed_world_six_scenarios(engine: LoopEngine):
    world = engine.seed_world()
    ids = {s["id"] for s in world["scenarios"]}
    assert ids >= {
        "safari_3ds",
        "android_sdk",
        "apple_pay",
        "shipping_ux",
        "security_exfil",
        "onboarding_activation",
    }
    kinds = {r.kind for r in engine.store.list_rooms()}
    assert {RoomKind.INCIDENT, RoomKind.OPPORTUNITY, RoomKind.REVIEW, RoomKind.OPS, RoomKind.RESEARCH} <= kinds


def test_type_a_vs_type_b_routing(engine: LoopEngine):
    engine.seed_world()
    rooms = {r.scenario_id: r for r in engine.store.list_rooms() if r.scenario_id}
    assert rooms["safari_3ds"].loop_type == LoopType.TYPE_A
    assert rooms["android_sdk"].loop_type == LoopType.TYPE_A
    assert rooms["onboarding_activation"].loop_type == LoopType.TYPE_A
    assert rooms["apple_pay"].loop_type == LoopType.TYPE_B
    assert rooms["shipping_ux"].loop_type == LoopType.TYPE_B

    apple = engine.store.get_investigation(rooms["apple_pay"].investigation_id)
    assert apple
    hyps = engine.store.list_hypotheses(apple.id)
    assert hyps[0].classification == Classification.OPPORTUNITY

    safari = engine.store.get_investigation(rooms["safari_3ds"].investigation_id)
    assert safari
    assert engine.store.list_hypotheses(safari.id)[0].classification == Classification.BUG


def test_non_checkout_scenario_exists(engine: LoopEngine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "onboarding_activation")
    inv = engine.store.get_investigation(room.investigation_id)
    assert inv
    sig = engine.store.get_signal(inv.originating_signal_ids[0])
    assert sig
    assert sig.funnel_position == "activation"
    assert "purchase" not in sig.metric


def test_security_exfil_denied_by_gateway(engine: LoopEngine):
    engine.seed_world()
    assert gateway_allows("code_agent", "customer_data.read") is False
    assert gateway_allows("code_agent", "github.write") is True
    verdicts = engine.store.list_verdicts()
    assert any(v.finding_type == "exfil_attempt" and v.verdict == "DENY" for v in verdicts)
    review = engine.store.get_room("room_reviews")
    assert review
    texts = " ".join(m.text.lower() for m in engine.store.list_messages(review.id))
    assert "deny" in texts
    assert "customer records" in texts


def test_memory_recalled_on_similar_later_signal(engine: LoopEngine):
    engine.seed_world()
    android = next(r for r in engine.store.list_rooms() if r.scenario_id == "android_sdk")
    inv = engine.store.get_investigation(android.investigation_id)
    assert inv
    assert any("SDK callback" in lesson for lesson in inv.recalled_lessons)
    onboarding = next(r for r in engine.store.list_rooms() if r.scenario_id == "onboarding_activation")
    oinv = engine.store.get_investigation(onboarding.investigation_id)
    assert oinv
    assert any("Activation drops" in lesson for lesson in oinv.recalled_lessons)


def test_seed_world_idempotent(engine: LoopEngine):
    first = engine.seed_world()
    second = engine.seed_world()
    assert second["reused"] is True
    assert len(first["rooms"]) == len(second["rooms"])
