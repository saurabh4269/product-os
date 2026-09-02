from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.models import Classification, Hypothesis, Investigation, InvestigationState, RiskTier
from loop.tenant import Tenant, hydrate_all_tenants, hydrate_tenant_config
from loop.tenant_context import (
    effective_action_artifacts,
    github_pr_eligible,
    merge_proposed_artifacts,
)


def _tenant_inv(tenant_id: str = "acme", scenario: str = "t:acme:purchase_conversion") -> tuple[Investigation, Hypothesis]:
    inv = Investigation(
        id="inv_hydrate",
        originating_signal_ids=[],
        state=InvestigationState.AWAITING_APPROVAL,
        opened_at=datetime.utcnow(),
        invocation_id="x",
        scenario_id=scenario,
        tenant_id=tenant_id,
        title="Cove: purchase_conversion",
    )
    hyp = Hypothesis(
        id="hyp_hydrate",
        investigation_id=inv.id,
        statement="Checkout conversion dropped after deploy",
        classification=Classification.BUG,
        confidence=0.82,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        cited_memory=[],
        rank=1,
        independence_groups=["analytics", "logs", "customer"],
    )
    return inv, hyp


def test_hydrate_tenant_fills_empty_flag_names_from_bootstrap(engine, monkeypatch):
    monkeypatch.delenv("LOOP_TENANT_FLAG_NAMES", raising=False)
    tenant = Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", stack="nextjs")
    hydrated = hydrate_tenant_config(tenant, engine.store)
    assert hydrated.flag_names == ["pay_sdk_4_3"]
    assert hydrated.code_paths == ["src/app/(store)/checkout/page.tsx", "src/lib/loop.ts"]
    stored = engine.store.get_tenant("acme")
    assert stored and stored.flag_names == ["pay_sdk_4_3"]


def test_hydrate_all_tenants_persists_on_cold_start(engine, monkeypatch):
    monkeypatch.delenv("LOOP_TENANT_FLAG_NAMES", raising=False)
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="saurabh4269/cove", deploy_url="https://cove.test")
    )
    assert engine.store.get_tenant("acme").flag_names == []
    assert hydrate_all_tenants(engine.store) == 1
    stored = engine.store.get_tenant("acme")
    assert stored.flag_names == ["pay_sdk_4_3"]
    assert stored.code_paths


def test_hydrate_tenant_fills_flag_names_from_store(engine):
    engine.store.set_flag("t:acme:checkout_v2", "on", "seed")
    tenant = Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", stack="rails")
    hydrated = hydrate_tenant_config(tenant, engine.store)
    assert hydrated.flag_names == ["checkout_v2"]


def test_hydrate_tenant_respects_env_overrides(engine, monkeypatch):
    monkeypatch.setenv("LOOP_TENANT_FLAG_NAMES", "alpha,beta")
    monkeypatch.setenv("LOOP_TENANT_CODE_PATHS", "lib/a.rb,lib/b.rb")
    tenant = Tenant(id="acme", name="Cove", product="Cove", repo="org/shop")
    hydrated = hydrate_tenant_config(tenant, engine.store)
    assert hydrated.flag_names == ["alpha", "beta"]
    assert hydrated.code_paths == ["lib/a.rb", "lib/b.rb"]


def test_merge_proposed_artifacts_attaches_flag_for_repo_tenant(engine):
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", stack="nextjs")
    )
    tenant = hydrate_tenant_config(engine.store.get_tenant("acme"), engine.store)
    inv, hyp = _tenant_inv()
    passed = {
        "code_brief": {"issue": "checkout hang"},
        "pr": {"title": "Fix: tenant_signal", "body": hyp.statement, "files": []},
        "code_fix": False,
    }
    merged = merge_proposed_artifacts(inv, hyp, tenant, passed)
    assert merged["flag"] == "pay_sdk_4_3"
    assert merged["code_fix"] is True
    assert merged["code_brief"]["likely_files"]
    assert merged["pr"]["title"].startswith("Fix: checkout hang")
    assert github_pr_eligible(merged, tenant)


def test_action_gate_github_pr_for_stored_action_without_flag(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", connected=True)
    )
    hydrate_tenant_config(engine.store.get_tenant("acme"), engine.store)
    inv, hyp = _tenant_inv()
    engine.store.put_investigation(inv)
    engine.store.put_hypothesis(hyp)
    inv.linked_hypothesis_ids = [hyp.id]
    engine.store.put_investigation(inv)
    action = engine.propose_action(
        inv,
        hyp,
        action_type="code_change",
        artifacts={
            "code_brief": {"issue": "checkout hang"},
            "pr": {"title": "Fix: tenant_signal", "body": hyp.statement, "files": []},
            "code_fix": False,
        },
    )
    action.artifacts.pop("flag", None)
    action.artifacts["code_fix"] = False
    engine.store.put_action(action)
    gate = api_mod._action_gate(engine, action)
    assert gate["mode"] == "github_pr"
    effective = effective_action_artifacts(engine.store, action)
    assert effective.get("flag") == "pay_sdk_4_3"
    assert effective.get("code_fix") is True


def test_get_tenants_lists_hydrated_flag_names(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="saurabh4269/cove", deploy_url="https://cove.test")
    )
    with TestClient(api_mod.app) as client:
        rows = client.get("/api/tenants").json()["tenants"]
    acme = next(t for t in rows if t["id"] == "acme")
    assert acme["flag_names"] == ["pay_sdk_4_3"]
    assert acme["code_paths"]


def test_execute_repairs_flag_and_does_not_open_issue(engine, monkeypatch):
    monkeypatch.setattr("loop.connectors.github._token", lambda: "tok")
    monkeypatch.setattr("loop.code_fix.resolve_brief", lambda *a, **k: None)
    calls: list[str] = []

    def fake_open_pr(*args, **kwargs):
        calls.append("pr")
        from loop.tenant import ConnectorReport

        return ConnectorReport(status="applied", connector="github.pr", detail="ok", url="https://github.com/org/shop/pull/2")

    def fake_issue(*args, **kwargs):
        calls.append("issue")
        from loop.tenant import ConnectorReport

        return ConnectorReport(status="applied", connector="github.issue", detail="no", url="https://github.com/org/shop/issues/99")

    monkeypatch.setattr("loop.connectors.open_pr", fake_open_pr)
    monkeypatch.setattr("loop.connectors.create_issue", fake_issue)
    monkeypatch.setattr(
        "loop.connectors.github._request",
        lambda method, url, token, body=None: (
            (200, {"default_branch": "main"})
            if method == "GET" and url.endswith("/repos/org/shop")
            else (200, {"object": {"sha": "abc"}})
            if "git/ref" in url
            else (201, {})
            if url.endswith("/git/refs") or "/contents/" in url or url.endswith("/pulls")
            else (404, {})
        ),
    )

    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", connected=True, stack="nextjs")
    )
    hydrate_tenant_config(engine.store.get_tenant("acme"), engine.store)
    inv, hyp = _tenant_inv()
    engine.store.put_investigation(inv)
    engine.store.put_hypothesis(hyp)
    inv.linked_hypothesis_ids = [hyp.id]
    engine.store.put_investigation(inv)
    action = engine.propose_action(
        inv,
        hyp,
        action_type="code_change",
        artifacts={
            "code_brief": {"issue": "checkout hang"},
            "pr": {"title": "Fix: tenant_signal", "body": hyp.statement, "files": []},
            "code_fix": False,
        },
    )
    action.artifacts.pop("flag", None)
    action.artifacts["code_fix"] = False
    engine.store.put_action(action)
    engine.approve(action.id, "oncall", "approve", "ship it")
    out = engine.execute_approved(action.id)
    assert "issue" not in calls
    assert calls == ["pr"]
    assert out.get("pr_opened") is True
    assert out.get("flag") == "pay_sdk_4_3"
    assert engine.store.get_action(action.id).artifacts.get("flag") == "pay_sdk_4_3"


def test_propose_action_high_attaches_flag(engine):
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", stack="nextjs")
    )
    tenant = hydrate_tenant_config(engine.store.get_tenant("acme"), engine.store)
    inv, hyp = _tenant_inv()
    engine.store.put_investigation(inv)
    action = engine.propose_action(
        inv,
        hyp,
        action_type="code_change",
        artifacts={
            "code_brief": {"issue": "checkout hang"},
            "pr": {"title": "Fix: tenant_signal", "body": hyp.statement, "files": []},
            "code_fix": False,
        },
    )
    assert action.artifacts.get("flag") == "pay_sdk_4_3"
    assert action.artifacts.get("code_fix") is True
    assert action.risk_tier == RiskTier.HIGH
    assert tenant.repo
