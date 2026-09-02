"""Pass 2 — one runner, many realistic recipes through the same pipeline."""

from __future__ import annotations

import pytest

from loop.jobs import enqueue_verify, process_job
from loop.models import InvestigationState, OutcomeVerdict, RiskTier
from loop.scenario_pack import RECIPES, assert_recipe_outcome, recipe_by_id, run_recipe
from loop.tenant import Tenant, hash_token


@pytest.mark.parametrize("recipe_id", [r.id for r in RECIPES])
def test_pass2_recipe_pipeline(engine, recipe_id: str):
    recipe = recipe_by_id(recipe_id)
    assert recipe is not None
    result = run_recipe(engine, recipe)
    assert_recipe_outcome(engine, recipe, result)


def test_pass2_memory_recall_on_similar_signal(engine):
    engine.seed_world()
    android = next(r for r in engine.store.list_rooms() if r.scenario_id == "android_sdk")
    inv = engine.store.get_investigation(android.investigation_id)
    assert inv and any("SDK callback" in x for x in inv.recalled_lessons)

    from loop.investigation import run_investigation
    from loop.models import LoopType, PathKind, RoomKind
    from loop.scenario_pack import recipe_checkout_sdk_deploy

    out = run_investigation(
        engine,
        recipe_checkout_sdk_deploy(),
        scenario_id="eval:memory_recall_sdk",
        propose_action=True,
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.INCIDENT,
    )
    inv2 = engine.store.get_investigation(out["investigation_id"])
    assert inv2
    assert any("SDK callback" in lesson for lesson in inv2.recalled_lessons)


def test_verify_job_inconclusive_not_marked_resolved(engine):
    from datetime import datetime

    from loop.models import Direction, Signal, SignalFamily, SignalStatus

    sig = Signal(
        id="sig_incon",
        family=SignalFamily.BUSINESS,
        direction=Direction.NEGATIVE,
        funnel_position="product",
        metric="dau",
        magnitude=-0.1,
        baseline=0.4,
        affected_segments=[],
        detection_window={"start": "2026-08-01", "end": "2026-08-02"},
        confidence=0.6,
        source="tenant.contoso",
        status=SignalStatus.OPEN,
        detected_at=datetime.utcnow(),
    )
    engine.store.put_signal(sig)
    inv = engine.open_investigation(sig)
    assert inv
    inv.scenario_id = "t:contoso:dau"
    inv.tenant_id = "contoso"
    engine.store.put_investigation(inv)
    job = enqueue_verify(engine.store, inv.id, delay_hours=0)
    result = process_job(engine.store, engine, job.id)
    assert result
    assert result["verdict"] == OutcomeVerdict.INCONCLUSIVE.value
    assert result["status"] == "inconclusive"
    assert engine.store.get_investigation(inv.id).state == InvestigationState.INCONCLUSIVE


def test_worker_auto_investigates_tenant_ingest_signal(engine, monkeypatch):
    monkeypatch.setenv("LOOP_AUTO_INVESTIGATE", "1")
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Y", token_hash=hash_token("tok"), repo="acme/y")
    )
    from loop.world import ingest_tenant_signal

    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="signup_rate",
        magnitude=-0.18,
        baseline=0.22,
        note="signup drop",
        source="tenant.acme",
        async_finish=False,
    )
    sig = next(s for s in engine.store.list_signals() if s.metric == "signup_rate")
    from loop.auto_investigate import open_signal_ids_for_auto_investigate

    # Signal is already on an investigation from ingest — should not re-queue.
    assert sig.id not in open_signal_ids_for_auto_investigate(engine, [])

    # Stuck signal with no investigation fan-out should be picked up.
    orphan = sig.model_copy(update={"id": "sig_orphan"})
    engine.store.put_signal(orphan)
    assert orphan.id in open_signal_ids_for_auto_investigate(engine, [])


def test_low_risk_docs_typo_auto_executes(engine):
    recipe = recipe_by_id("docs_typo_low")
    assert recipe
    out = run_recipe(engine, recipe)
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv
    actions = engine.store.list_actions(inv.id)
    assert actions
    assert actions[0].risk_tier == RiskTier.LOW
    assert actions[0].status == "executed"


def test_security_exfil_gateway_deny(engine):
    recipe = recipe_by_id("security_exfil")
    assert recipe
    result = run_recipe(engine, recipe)
    assert result.get("gateway_deny") is True
