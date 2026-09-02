from __future__ import annotations

from datetime import datetime

from loop import api as api_mod
from loop.models import Classification, Hypothesis, Investigation, InvestigationState, RiskTier
from loop.tenant import Tenant, hydrate_tenant_config
from loop.tenant_context import github_pr_eligible, merge_proposed_artifacts


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


def test_action_gate_github_pr_for_hydrated_tenant_action(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Cove", repo="org/shop", connected=True)
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
    gate = api_mod._action_gate(engine, action)
    assert gate["mode"] == "github_pr"
    assert gate["tenant_repo"] == tenant.repo
    assert action.artifacts.get("flag") == "pay_sdk_4_3"
    assert action.artifacts.get("code_fix") is True
    assert action.risk_tier == RiskTier.HIGH


def test_execute_code_change_without_flag_still_queues_pr(engine, monkeypatch):
    pr_url = "https://github.com/org/shop/pull/9"

    def sync_enqueue(engine, **kwargs):
        from loop.code_fix import run_code_fix_job
        from loop.jobs import enqueue_code_fix

        job = enqueue_code_fix(
            engine.store,
            action_id=kwargs["action_id"],
            investigation_id=kwargs["inv"].id,
            tenant_id=kwargs["tenant"].id,
            brief=kwargs["brief"],
            flag_patch=kwargs["flag_patch"],
            pr_title=kwargs["pr_title"],
            pr_body=kwargs["pr_body"],
        )
        run_code_fix_job(engine, job)

    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: __import__("loop.tenant", fromlist=["ConnectorReport"]).ConnectorReport(
            status="applied",
            connector="github.pr",
            detail="pull request opened",
            url=pr_url,
        ),
    )
    monkeypatch.setattr("loop.code_fix.enqueue_code_fix_job", sync_enqueue)

    tenant = Tenant(
        id="brandx",
        name="Brand X",
        product="Brand X",
        repo="org/shop",
        connected=True,
        code_paths=["src/checkout.ts"],
        flag_names=[],
    )
    engine.store.put_tenant(tenant)
    inv, hyp = _tenant_inv(tenant_id="brandx", scenario="t:brandx:checkout_drop")
    inv.tenant_id = "brandx"
    engine.store.put_investigation(inv)
    action = engine.propose_action(
        inv,
        hyp,
        action_type="code_change",
        artifacts={
            "code_brief": {"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
            "pr": {"title": "Fix checkout timeout", "body": hyp.statement, "files": ["src/checkout.ts"]},
            "code_fix": True,
        },
    )
    # Simulate a tenant with no flags but explicit code paths.
    action.artifacts.pop("flag", None)
    engine.store.put_action(action)
    engine.approve(action.id, "oncall", "approve", "ship it")
    out = engine.execute_approved(action.id)
    assert out.get("code_fix") == "queued" or out.get("pr_opened") is True
    exe = engine.store.get_action(action.id).artifacts["execution"]
    assert exe.get("pr_opened") is True
    assert exe["pr_url"] == pr_url
    assert exe.get("merged") is False
