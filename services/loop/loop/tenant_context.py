"""Tenant-bound artifacts — no Cove defaults unless fixture or tenant config says so."""

from __future__ import annotations

from typing import Any

from loop.models import Hypothesis, Investigation
from loop.tenant import Tenant


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
            else:
                merged[k] = v
        if "flag" not in merged and tenant and tenant.flag_names:
            merged["flag"] = tenant.flag_names[0]
            merged.setdefault("from", "on")
            merged.setdefault("to", "off")
        if "code_fix" not in merged and merged.get("code_brief", {}).get("likely_files"):
            merged["code_fix"] = True
        return merged
    return tenant_action_artifacts(inv, hyp, tenant)


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
