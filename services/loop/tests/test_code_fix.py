"""Code fix patch generation."""

from __future__ import annotations

from datetime import datetime

from loop.code_fix import (
    _deterministic_safari_patch,
    _expand_files,
    resolve_brief,
    run_code_fix_job,
)
from loop.jobs import enqueue_code_fix
from loop.models import (
    Classification,
    Hypothesis,
    Investigation,
    InvestigationState,
    ProposedAction,
    RiskTier,
)
from loop.tenant import ConnectorReport, Tenant


def test_expand_files_maps_payment_paths():
    out = _expand_files(["payment/3ds.ts", "src/lib/loop.ts"])
    assert "src/app/(store)/checkout/page.tsx" in out
    assert "src/lib/loop.ts" in out


def test_deterministic_patch_adds_regression_test():
    brief = {"issue": "Safari 3DS hang", "hypothesis": "callback timeout", "fixture_id": "safari_3ds"}
    files = {
        "src/app/(store)/checkout/page.tsx": 'await new Promise((r) => setTimeout(r, 2200))\n',
        "src/lib/loop.ts": 'return flags.pay_sdk_4_3 === "on" || flags.pay_sdk === "4.3.0"\n',
    }
    patched = _deterministic_safari_patch(brief, files)
    assert "tests/regression/safari-3ds-checkout.test.ts" in patched
    assert "800" in patched["src/app/(store)/checkout/page.tsx"]
    assert "4.2.1" in patched["src/lib/loop.ts"]


def test_resolve_brief_from_action_artifacts():
    class A:
        artifacts = {"code_brief": {"issue": "x", "likely_files": ["a.ts"]}}

    class Inv:
        room_id = None

    class S:
        def list_messages(self, _):
            return []

    assert resolve_brief(A(), Inv(), S())["issue"] == "x"


def _action_bundle(engine):
    tenant = Tenant(
        id="brandx",
        name="Brand X",
        product="Brand X",
        repo="org/shop",
        connected=True,
        stack="nextjs",
        flag_names=["checkout_v2"],
        code_paths=["src/checkout.ts"],
    )
    engine.store.put_tenant(tenant)
    inv = Investigation(
        id="inv_cf",
        originating_signal_ids=[],
        state=InvestigationState.AWAITING_APPROVAL,
        opened_at=datetime.utcnow(),
        invocation_id="x",
        scenario_id="t:brandx:checkout_drop",
        tenant_id="brandx",
        title="Brand X: checkout_drop",
    )
    hyp = Hypothesis(
        id="hyp_cf",
        investigation_id=inv.id,
        statement="Checkout times out after deploy",
        classification=Classification.BUG,
        confidence=0.8,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
        cited_memory=[],
        rank=1,
        independence_groups=["analytics"],
    )
    engine.store.put_investigation(inv)
    engine.store.put_hypothesis(hyp)
    inv.linked_hypothesis_ids = [hyp.id]
    engine.store.put_investigation(inv)
    action = ProposedAction(
        id="act_cf",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={
            "flag": "checkout_v2",
            "from": "on",
            "to": "off",
            "code_fix": True,
            "code_brief": {"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
            "pr": {"title": "Fix checkout timeout", "body": hyp.statement},
        },
        idempotency_key="idem_cf",
        status="approved",
        consequence="Open PR on org/shop",
    )
    engine.store.put_action(action)
    return tenant, inv, action


def test_execute_opens_flag_pr_when_code_fix_queued(engine, monkeypatch):
    monkeypatch.setattr("loop.connectors.github._token", lambda: "tok")
    queued: list[dict] = []
    monkeypatch.setattr(
        "loop.code_fix.enqueue_code_fix_job",
        lambda eng, **kwargs: queued.append(kwargs) or "job_test",
    )
    monkeypatch.setattr(
        "loop.connectors.open_pr",
        lambda *a, **k: ConnectorReport(
            status="applied",
            connector="github.pr",
            detail="flags.json",
            url="https://github.com/org/shop/pull/7",
        ),
    )

    tenant, inv, action = _action_bundle(engine)
    engine.approve(action.id, "oncall", "approve", "go")
    out = engine.execute_approved(action.id)
    assert out["pr_opened"] is True
    assert out["pr_url"].endswith("/pull/7")
    assert out.get("code_fix") == "queued"
    assert queued and queued[0]["flag_pr_opened"] is True
    exe = engine.store.get_action(action.id).artifacts["execution"]
    assert exe["pr_opened"] is True


def test_code_fix_failure_preserves_flag_pr(engine, monkeypatch):
    monkeypatch.setattr("loop.connectors.github._token", lambda: "tok")
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: ConnectorReport(
            status="failed",
            connector="code_fix",
            detail="gemini: code-fix prompt blocked by Model Armor: screening_failure",
        ),
    )

    tenant, inv, action = _action_bundle(engine)
    action.artifacts["execution"] = {
        "pr_opened": True,
        "pr_url": "https://github.com/org/shop/pull/7",
        "flag": "checkout_v2",
        "value": "off",
    }
    engine.store.put_action(action)
    job = enqueue_code_fix(
        engine.store,
        action_id=action.id,
        investigation_id=inv.id,
        tenant_id=tenant.id,
        brief={"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
        flag_patch={"checkout_v2": "off"},
        pr_title="Fix checkout timeout",
        pr_body="body",
        flag_pr_opened=True,
    )
    run_code_fix_job(engine, job)
    exe = engine.store.get_action(action.id).artifacts["execution"]
    assert exe["pr_opened"] is True
    assert exe["pr_url"].endswith("/pull/7")
    assert "code_fix_failed" in exe


def test_code_fix_failure_opens_flag_pr_fallback(engine, monkeypatch):
    monkeypatch.setattr("loop.connectors.github._token", lambda: "tok")
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: ConnectorReport(
            status="failed",
            connector="code_fix",
            detail="gemini: code-fix prompt blocked by Model Armor: screening_failure",
        ),
    )
    monkeypatch.setattr(
        "loop.code_fix.open_flag_pr",
        lambda tenant, **kwargs: ConnectorReport(
            status="applied",
            connector="github.pr",
            detail="flags.json fallback",
            url="https://github.com/org/shop/pull/8",
        ),
    )

    tenant, inv, action = _action_bundle(engine)
    job = enqueue_code_fix(
        engine.store,
        action_id=action.id,
        investigation_id=inv.id,
        tenant_id=tenant.id,
        brief={"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
        flag_patch={"checkout_v2": "off"},
        pr_title="Fix checkout timeout",
        pr_body="body",
        flag_pr_opened=False,
    )
    run_code_fix_job(engine, job)
    exe = engine.store.get_action(action.id).artifacts["execution"]
    assert exe["pr_opened"] is True
    assert exe["pr_url"].endswith("/pull/8")
    assert exe.get("flag_pr_fallback", {}).get("status") == "applied"

