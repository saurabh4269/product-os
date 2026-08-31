"""Tier-1 production: tenant binding, ingest pipeline, honest verify, auth."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.auth import admin_required, require_admin
from loop.models import InvestigationState, OutcomeVerdict, RiskTier
from loop.tenant import Tenant, ConnectorReport, flag_key, hash_token, resolve_tenant, tenant_id_from_scenario


def test_tenant_id_from_scenario():
    assert tenant_id_from_scenario("t:acme:purchase_conversion") == "acme"
    assert tenant_id_from_scenario("safari_3ds") is None


def test_resolve_tenant_from_investigation(engine):
    from loop.models import Investigation

    inv = Investigation(
        id="inv_x",
        originating_signal_ids=[],
        state=InvestigationState.OPEN,
        opened_at=engine.store.list_investigations()[0].opened_at if engine.store.list_investigations() else __import__("datetime").datetime.utcnow(),
        invocation_id="x",
        scenario_id="t:contoso:checkout_cr",
        tenant_id="contoso",
    )
    engine.store.put_tenant(Tenant(id="contoso", name="Contoso", product="Shop"))
    assert resolve_tenant(engine.store, investigation=inv).id == "contoso"


def test_execute_uses_bound_tenant_not_first_connected(engine, monkeypatch):
    engine.store.put_tenant(Tenant(id="acme", name="A", product="A", repo="acme/a", connected=True))
    engine.store.put_tenant(Tenant(id="beta", name="B", product="B", repo="beta/b", connected=True))
    engine.seed_world()
    inv = next(i for i in engine.store.list_investigations() if i.scenario_id == "safari_3ds")
    inv.tenant_id = "beta"
    engine.store.put_investigation(inv)
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "safari_3ds")
    room.tenant_id = "beta"
    engine.store.put_room(room)

    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    pr_calls: list[str] = []

    def fake_open_pr(tenant, *a, **k):
        pr_calls.append(tenant.id)
        return ConnectorReport(status="skipped", connector="github.pr", detail="skip")

    monkeypatch.setattr("loop.connectors.github.open_pr", fake_open_pr)
    monkeypatch.setattr("loop.code_fix.enqueue_code_fix_job", lambda *a, **k: None)
    engine.resume_after_approval(high.id, "oncall@beta")
    assert engine.store.get_flag(flag_key("acme", "pay_sdk_4_3")) is None
    mirrored = engine.store.get_flag(flag_key("beta", "pay_sdk_4_3"))
    assert mirrored == "off" or engine.store.get_flag("pay_sdk_4_3") == "off"


def test_verify_generic_is_inconclusive(engine):
    from loop.models import Investigation, Signal, SignalFamily, Direction, SignalStatus
    from datetime import datetime

    sig = Signal(
        id="sig_g",
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
    inv.scenario_id = "t:contoso:dau"
    inv.tenant_id = "contoso"
    engine.store.put_investigation(inv)
    out = engine._verify_generic(inv)
    assert out.verdict == OutcomeVerdict.INCONCLUSIVE
    assert engine.store.get_investigation(inv.id).state == InvestigationState.INCONCLUSIVE


def test_ingest_runs_investigation_pipeline(engine, monkeypatch):
    engine.store.put_tenant(
        Tenant(id="acme", name="Northstar", product="Y", token_hash=hash_token("tok"), repo="acme/y")
    )
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.post(
            "/api/t/acme/signals",
            headers={"Authorization": "Bearer tok"},
            json={"metric": "signup_rate", "magnitude": -0.18, "baseline": 0.22},
        )
        assert res.status_code == 200
        room_id = res.json()["room_id"]
        room = engine.store.get_room(room_id)
        assert room and room.tenant_id == "acme"
        inv = engine.store.get_investigation(room.investigation_id)
        assert inv and inv.tenant_id == "acme"
        assert engine.store.list_evidence(inv.id)


def test_approval_requires_admin_when_token_set(engine, monkeypatch):
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    engine.seed_world()
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    with TestClient(api_mod.app) as client:
        denied = client.post(
            f"/api/approvals/{high.id}",
            json={"decision": "approve", "approver": "oncall@acme", "rationale": "nope"},
        )
        assert denied.status_code == 401
        ok = client.post(
            f"/api/approvals/{high.id}",
            headers={"Authorization": "Bearer secret"},
            json={"decision": "approve", "approver": "oncall@acme", "rationale": "ok"},
        )
        assert ok.status_code == 200


def test_admin_not_required_on_hosted_without_token(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.delenv("LOOP_ADMIN_TOKEN", raising=False)
    assert admin_required() is False
    assert require_admin(None, actor="dev") == "dev"


def test_visible_flags_tenant_scoped_only(engine):
    engine.store.set_flag("pay_sdk_4_3", "on", "g")
    engine.store.set_flag(flag_key("acme", "pay_sdk_4_3"), "off", "t")
    flags = api_mod._visible_flags(engine, "acme")
    assert flags == {"pay_sdk_4_3": "off"}
    assert "onboarding_copy_exp_b" not in flags


def test_propose_action_uses_tenant_flag_not_safari_default(engine):
    from datetime import datetime

    from loop.models import Classification, Hypothesis, Investigation, InvestigationState

    engine.store.put_tenant(
        Tenant(
            id="contoso",
            name="Contoso",
            product="Shop",
            repo="contoso/shop",
            flag_names=["new_checkout_flow"],
            code_paths=["app/checkout.rb"],
        )
    )
    inv = Investigation(
        id="inv_t",
        originating_signal_ids=[],
        state=InvestigationState.OPEN,
        opened_at=datetime.utcnow(),
        invocation_id="x",
        scenario_id="t:contoso:checkout",
        tenant_id="contoso",
    )
    hyp = Hypothesis(
        id="hyp_t",
        investigation_id=inv.id,
        statement="Checkout drop after deploy",
        classification=Classification.BUG,
        confidence=0.8,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        cited_memory=[],
        rank=1,
        independence_groups=["logs"],
    )
    action = engine.propose_action(inv, hyp, artifacts={"code_brief": {"issue": "checkout broke"}})
    assert action.artifacts.get("flag") == "new_checkout_flow"
    assert "pay_sdk_4_3" not in str(action.artifacts)
    assert "app/checkout.rb" in str(action.artifacts.get("code_brief", {}).get("likely_files", []))


def test_github_token_per_tenant(monkeypatch):
    from loop.connectors.github import token_for_tenant

    monkeypatch.setenv("LOOP_GITHUB_TOKEN", "global")
    monkeypatch.setenv("LOOP_GITHUB_TOKEN_CONTOSO", "scoped")
    t = Tenant(id="contoso", name="C", product="C", repo="c/c")
    assert token_for_tenant(t) == "scoped"
    assert token_for_tenant(Tenant(id="other", name="O", product="O")) == "global"


def test_recall_lessons_scoped_to_tenant(engine):
    from loop.models import Lesson

    engine.store.put_lesson(
        Lesson(
            id="les_a",
            investigation_id="inv_a",
            statement="Checkout SDK callback broke on Android",
            root_cause_family="sdk",
            applicable_conditions=["checkout"],
            confidence=0.8,
            author_agent="learning_agent",
            tenant_id="acme",
        )
    )
    engine.store.put_lesson(
        Lesson(
            id="les_b",
            investigation_id="inv_b",
            statement="Checkout SDK callback broke on Android for beta shop",
            root_cause_family="sdk",
            applicable_conditions=["checkout"],
            confidence=0.8,
            author_agent="learning_agent",
            tenant_id="beta",
        )
    )
    acme_hits = engine.recall_lessons("checkout", "sdk", tenant_id="acme")
    assert any("Android" in h for h in acme_hits)
    assert not any("beta shop" in h for h in acme_hits)
