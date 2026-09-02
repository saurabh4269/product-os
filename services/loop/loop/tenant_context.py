"""Tenant-bound artifacts — no Cove defaults unless fixture or tenant config says so."""

from __future__ import annotations

from typing import Any

from loop.models import Hypothesis, Investigation
from loop.tenant import Tenant, resolve_tenant


def github_token_for(tenant: Tenant | None) -> str:
    from loop.connectors.github import token_for_tenant

    return token_for_tenant(tenant)


def code_paths_for(tenant: Tenant | None, brief: dict[str, Any] | None = None) -> list[str]:
    if brief and brief.get("likely_files"):
        return [str(p) for p in brief["likely_files"] if p]
    if tenant and tenant.code_paths:
        return list(tenant.code_paths)
    return []


def flag_file_for(tenant: Tenant | None) -> str:
    if tenant and getattr(tenant, "flag_file_path", None):
        return str(tenant.flag_file_path)
    return "config/flags.json"


def safari_action_artifacts(inv: Investigation, hyp: Hypothesis) -> dict[str, Any]:
    return {
        "flag": "pay_sdk_4_3",
        "from": "on",
        "to": "off",
        "code_fix": True,
        "code_brief": {
            "issue": "Safari 3DS callback regression after pay-sdk 4.3",
            "likely_files": [
                "payment/callback.ts",
                "payment/3ds.ts",
                "src/app/(store)/checkout/page.tsx",
                "src/lib/loop.ts",
            ],
            "expected_behavior": "Safari checkout completes; 3DS callback returns within timeout.",
            "regression_test": "Safari checkout does not hang when pay_sdk_4_3 is off.",
            "surface": "payment authorization / 3DS",
            "hypothesis": hyp.statement,
            "fixture_id": "safari_3ds",
        },
        "pr": {
            "title": "Fix Safari 3DS checkout regression (pay-sdk 4.3)",
            "body": f"Investigation {inv.id}. Hypothesis: {hyp.statement}",
            "tests": "tests/regression/safari-3ds-checkout.test.ts",
        },
    }


def github_pr_eligible(artifacts: dict[str, Any], tenant: Tenant | None) -> bool:
    if not tenant or not tenant.repo:
        return False
    if artifacts.get("flag"):
        return True
    pr = artifacts.get("pr") if isinstance(artifacts.get("pr"), dict) else {}
    brief = artifacts.get("code_brief") if isinstance(artifacts.get("code_brief"), dict) else {}
    files = list(brief.get("likely_files") or pr.get("files") or [])
    if files:
        return True
    return artifacts.get("code_fix") is True


def enrich_github_pr_artifacts(
    merged: dict[str, Any],
    inv: Investigation,
    hyp: Hypothesis,
    tenant: Tenant | None,
) -> None:
    if not tenant or not tenant.repo:
        return
    brief = merged.get("code_brief")
    if not isinstance(brief, dict):
        brief = {}
        merged["code_brief"] = brief
    pr = merged.get("pr")
    if not isinstance(pr, dict):
        pr = {}
        merged["pr"] = pr

    pr_files = list(pr.get("files") or []) if isinstance(pr.get("files"), list) else []
    if not brief.get("likely_files"):
        if pr_files:
            brief["likely_files"] = pr_files
        elif tenant.code_paths:
            brief["likely_files"] = list(tenant.code_paths)

    if not merged.get("flag") and tenant.flag_names:
        merged["flag"] = tenant.flag_names[0]
        merged.setdefault("from", "on")
        merged.setdefault("to", "off")

    files = list(brief.get("likely_files") or pr_files)
    wants_pr = bool(merged.get("flag") or files)
    if wants_pr:
        merged["code_fix"] = True
        if files:
            pr.setdefault("files", files)
        issue = brief.get("issue") or inv.title or hyp.statement[:120]
        title = str(pr.get("title") or "")
        generic_titles = {"Fix: tenant_signal", f"Fix: {inv.scenario_id or ''}"}
        if not title or title in generic_titles:
            pr["title"] = f"Fix: {str(issue)[:80]}"


def tenant_action_artifacts(
    inv: Investigation,
    hyp: Hypothesis,
    tenant: Tenant | None,
    *,
    code_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    brief = dict(code_brief or {})
    brief.setdefault("hypothesis", hyp.statement)
    brief.setdefault("issue", inv.title or hyp.statement[:120])
    brief.setdefault("likely_files", code_paths_for(tenant, brief))
    brief.setdefault("surface", (tenant.default_surface if tenant else None) or inv.title or "product")
    arts: dict[str, Any] = {
        "code_fix": bool(brief.get("likely_files")),
        "code_brief": brief,
        "pr": {
            "title": f"Fix: {brief.get('issue', 'product regression')[:80]}",
            "body": f"Investigation {inv.id}. Hypothesis: {hyp.statement}",
            "tests": brief.get("regression_test") or "",
        },
    }
    flag_name = None
    if tenant and tenant.flag_names:
        flag_name = str(tenant.flag_names[0])
    if flag_name:
        arts["flag"] = flag_name
        arts["from"] = "on"
        arts["to"] = "off"
    return arts


def effective_action_artifacts(
    store: Any,
    action: Any,
    *,
    inv: Any | None = None,
    tenant: Tenant | None = None,
) -> dict[str, Any]:
    """Re-merge stored artifacts with hydrated tenant config (gate + execute repair)."""
    arts = dict(getattr(action, "artifacts", None) or {})
    inv = inv or store.get_investigation(getattr(action, "investigation_id", ""))
    if not inv:
        return arts
    tenant = tenant or resolve_tenant(store, investigation=inv)
    if not tenant or not tenant.repo:
        return arts
    hyp: Hypothesis | None = None
    hyps = store.list_hypotheses(inv.id)
    if hyps:
        hyp = hyps[0]
    if not hyp:
        return arts
    return merge_proposed_artifacts(inv, hyp, tenant, arts)


def merge_proposed_artifacts(
    inv: Investigation,
    hyp: Hypothesis,
    tenant: Tenant | None,
    passed: dict[str, Any] | None,
) -> dict[str, Any]:
    from .runtime_mode import is_eval_mode

    if inv.scenario_id == "safari_3ds" and is_eval_mode() and not inv.tenant_id:
        base = safari_action_artifacts(inv, hyp)
        if passed:
            base.update(passed)
            if passed.get("code_brief"):
                base["code_brief"] = {**base.get("code_brief", {}), **passed["code_brief"]}
        return base
    if passed:
        merged = tenant_action_artifacts(inv, hyp, tenant, code_brief=passed.get("code_brief"))
        for k, v in passed.items():
            if k == "code_brief" and isinstance(v, dict):
                merged["code_brief"] = {**merged.get("code_brief", {}), **v}
            elif k in {"code_fix", "flag"} and v in (False, "", None):
                continue
            else:
                merged[k] = v
        enrich_github_pr_artifacts(merged, inv, hyp, tenant)
        return merged
    merged = tenant_action_artifacts(inv, hyp, tenant)
    enrich_github_pr_artifacts(merged, inv, hyp, tenant)
    return merged


def consequence_for(tenant: Tenant | None, inv: Investigation, hyp: Hypothesis, *, has_flag: bool) -> str:
    product = tenant.product if tenant else "the product"
    if has_flag and tenant and tenant.flag_names:
        flag = tenant.flag_names[0]
        return (
            f"On approval, LOOP will flip tenant flag {flag} for {product}, "
            f"open a PR on {tenant.repo or 'the connected repo'}, and never merge or deploy."
        )
    return (
        f"On approval, LOOP will open a PR on {tenant.repo if tenant and tenant.repo else 'the tenant repo'} "
        f"for {product}. Human review required — no auto-merge."
    )
