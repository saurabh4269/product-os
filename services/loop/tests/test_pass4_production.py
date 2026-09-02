"""Pass 4 — production live path (generic pipeline, not fixture names)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.customer_voice_live import CUSTOMER_VOICE_FIELDS
from loop.engine import LoopEngine
from loop.models import Classification, Hypothesis, Investigation, InvestigationState, RiskTier
from loop.tenant import Tenant, hash_token
from loop.world import MEMORY_KINDS, ensure_standing_world, ingest_tenant_signal


def test_production_memory_four_kinds(engine: LoopEngine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    engine.store._conn.execute("DELETE FROM memory")
    engine.store._conn.commit()
    engine.store.set_flag("world_seeded", "0", "reset")
    ensure_standing_world(engine)
    kinds = {m.get("kind") for m in engine.store.list_memory()}
    assert set(MEMORY_KINDS) <= kinds


def test_tenant_ingest_emits_structured_customer_voice(engine: LoopEngine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Acme Shop", token_hash=hash_token("tok"), repo="acme/shop")
    )
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="signup_rate",
        magnitude=-0.14,
        baseline=0.22,
        note="Signup drop after release",
        async_finish=False,
    )
    room_id = out["room_id"]
    msgs = engine.store.list_messages(room_id)
    call_ev = [
        m
        for m in msgs
        if m.artifact_type == "call_evidence"
        and isinstance(m.artifact, dict)
        and isinstance(m.artifact.get("structured"), dict)
    ]
    assert call_ev, "live ingest must post call_evidence with structured JSON"
    structured = call_ev[0].artifact["structured"]
    assert len(CUSTOMER_VOICE_FIELDS & set(structured.keys())) >= 5
    assert structured.get("reason") or structured.get("friction")


def test_memory_recall_on_similar_tenant_signal(engine: LoopEngine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store._conn.execute("DELETE FROM memory")
    engine.store._conn.commit()
    engine.store.set_flag("world_seeded", "0", "reset")
    ensure_standing_world(engine)
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Acme Shop", token_hash=hash_token("tok"), repo="acme/shop")
    )
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="client_sdk_errors",
        magnitude=-0.2,
        baseline=0.05,
        async_finish=False,
    )
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv and inv.recalled_lessons


def test_gateway_deny_visible_on_execute(engine: LoopEngine):
    from loop.models import Room, RoomKind

    inv = Investigation(
        id="inv_den",
        originating_signal_ids=[],
        state=InvestigationState.APPROVED,
        opened_at=datetime.now(UTC),
        invocation_id="job_den",
        assigned_agents=["analytics_agent"],
        room_id="room_den",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_den",
            kind=RoomKind.INCIDENT,
            title="deny test",
            topic="",
            status="open",
            created_at=datetime.now(UTC),
            members=["analytics_agent"],
            investigation_id=inv.id,
        )
    )
    with pytest.raises(PermissionError):
        engine._gateway_invoke(inv, "analytics_agent", "github.write", lambda: {"ok": True})
    msgs = engine.store.list_messages("room_den")
    deny = [m for m in msgs if m.artifact_type == "risk_decision" and m.artifact.get("verdict") == "DENY"]
    assert deny
    assert "gateway" in deny[0].text.lower() or "identity" in deny[0].text.lower()


def test_verify_posts_honest_outcome_to_room(engine: LoopEngine):
    from loop.models import (
        Direction,
        OutcomeVerdict,
        Room,
        RoomKind,
        Signal,
        SignalFamily,
        SignalStatus,
    )

    sig = Signal(
        id="sig_v",
        family=SignalFamily.BUSINESS,
        direction=Direction.NEGATIVE,
        funnel_position="product",
        metric="activation_rate",
        magnitude=-0.1,
        baseline=0.3,
        affected_segments=[],
        detection_window={"start": "2026-08-26", "end": "2026-08-28"},
        confidence=0.7,
        source="tenant.acme",
        status=SignalStatus.INVESTIGATING,
        detected_at=datetime.now(UTC),
    )
    engine.store.put_signal(sig)
    inv = Investigation(
        id="inv_v",
        originating_signal_ids=[sig.id],
        state=InvestigationState.APPROVED,
        opened_at=datetime.now(UTC),
        invocation_id="job_v",
        assigned_agents=["learning_agent"],
        room_id="room_v",
        scenario_id="t:acme:activation_rate",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_v",
            kind=RoomKind.INCIDENT,
            title="verify",
            topic="",
            status="open",
            created_at=datetime.now(UTC),
            members=["learning_agent"],
            investigation_id=inv.id,
        )
    )
    outcome = engine._verify_generic(inv)
    assert outcome.verdict == OutcomeVerdict.INCONCLUSIVE
    msgs = engine.store.list_messages("room_v")
    outcome_msgs = [m for m in msgs if m.artifact_type == "outcome"]
    assert outcome_msgs
    assert outcome_msgs[0].artifact.get("inconclusive") is True


def test_high_risk_never_auto_executes(engine: LoopEngine):
    inv = Investigation(
        id="inv_hi",
        originating_signal_ids=[],
        state=InvestigationState.OPEN,
        opened_at=datetime.now(UTC),
        invocation_id="job_hi",
        assigned_agents=["risk_agent"],
    )
    engine.store.put_investigation(inv)
    hyp = Hypothesis(
        id="hyp_hi",
        investigation_id=inv.id,
        statement="Payment authorization path needs human review",
        classification=Classification.BUG,
        confidence=0.9,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        cited_memory=[],
        rank=1,
        independence_groups=["analytics", "logs", "customer_voice"],
    )
    engine.store.put_hypothesis(hyp)
    action = engine.propose_action(
        inv,
        hyp,
        surface="payment authorization",
        action_type="code_change",
    )
    assert action.risk_tier == RiskTier.HIGH
    assert action.status == "awaiting_approval"
    assert not engine.auto_execute_low_tier(action)


def test_proof_live_work_require_admin_when_eval_off(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        assert client.get("/api/proof").status_code == 401
        assert client.get("/api/live-work").status_code == 401
        headers = {"Authorization": "Bearer secret"}
        assert client.get("/api/proof", headers=headers).status_code == 200
        assert client.get("/api/live-work", headers=headers).status_code == 200


def test_live_checkout_hang_pipeline(engine: LoopEngine, monkeypatch):
    """Product Y checkout hang → ingest → room → voice → Type A HIGH → approval gate."""
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store._conn.execute("DELETE FROM memory")
    engine.store._conn.commit()
    engine.store.set_flag("world_seeded", "0", "reset")
    ensure_standing_world(engine)
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Acme",
            product="Product Y",
            token_hash=hash_token("tok"),
            repo="saurabh4269/cove",
            deploy_url="https://cove.example",
            flag_names=["new_checkout_flow"],
        )
    )
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_completion_rate",
        magnitude=-0.22,
        baseline=0.41,
        note="Checkout hang after deploy",
        async_finish=False,
    )
    assert not out.get("joined")
    room = engine.store.get_room(out["room_id"])
    inv = engine.store.get_investigation(out["investigation_id"])
    assert room and inv
    assert room.loop_type.value == "type_a"
    msgs = engine.store.list_messages(room.id)
    assert any(m.artifact_type == "call_evidence" for m in msgs)
    assert any(m.kind == "chat" and m.author == "customer_voice_agent" for m in msgs)
    actions = engine.store.list_actions(inv.id)
    assert actions
    assert actions[0].risk_tier == RiskTier.HIGH
    assert actions[0].status == "awaiting_approval"
    assert not engine.auto_execute_low_tier(actions[0])


def test_async_ingest_stalled_finished_by_worker(engine: LoopEngine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "1")
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Y", token_hash=hash_token("tok"), repo="acme/y")
    )
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="signup_rate",
        magnitude=-0.1,
        baseline=0.2,
        async_finish=True,
    )
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv
    assert not engine.store.list_hypotheses(inv.id)
    from loop.auto_investigate import finish_stalled_investigations

    results = finish_stalled_investigations(engine)
    assert any(r.get("status") == "applied" for r in results)
    assert engine.store.list_hypotheses(inv.id)


def test_firestore_warm_client(monkeypatch):
    from loop import firestore_memory

    monkeypatch.setenv("LOOP_FIRESTORE_MEMORY", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    firestore_memory.reset_client()
    monkeypatch.setattr("loop.firestore_memory._get_client", lambda: object())
    assert firestore_memory.warm_client() is True


def test_pass4_live_pipeline_e2e(engine: LoopEngine, monkeypatch):
    """Ingest → room → evidence → hypothesis → risk — generic metric only."""
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store._conn.execute("DELETE FROM memory")
    engine.store._conn.commit()
    engine.store.set_flag("world_seeded", "0", "reset")
    ensure_standing_world(engine)
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Acme Shop", token_hash=hash_token("tok"), repo="acme/shop")
    )
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="weekly_active_users",
        magnitude=-0.12,
        baseline=0.4,
        async_finish=False,
    )
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv
    groups = {e.independence_group for e in engine.store.list_evidence(inv.id)}
    assert len(groups) >= 3
    hyps = engine.store.list_hypotheses(inv.id)
    assert hyps
    actions = engine.store.list_actions(inv.id)
    if actions:
        assert actions[0].risk_tier in {RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH}
    a2a = engine.store.list_agent_calls(inv.id)
    assert a2a
