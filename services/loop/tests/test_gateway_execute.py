"""Gateway enforces identity on execute_approved side effects."""

from __future__ import annotations

import pytest

from loop.gateway import authorize, invoke
from loop.models import RiskTier


def test_gateway_denies_unknown_tool():
    gate = authorize("code_agent", "customer_data.read")
    assert gate.decision == "deny"


def test_gateway_allows_github_write():
    gate = authorize("code_agent", "github.write")
    assert gate.decision == "allow"


def test_execute_approved_routes_github_through_gateway(engine, monkeypatch):
    from loop.tenant import Tenant

    engine.store.put_tenant(Tenant(id="acme", name="Acme", product="Y", repo="acme/y", token_hash="x"))
    inv = engine.run_until_approval()
    inv.tenant_id = "acme"
    engine.store.put_investigation(inv)
    action = engine.store.list_actions(inv.id)[0]
    assert action.risk_tier == RiskTier.HIGH

    gateway_calls: list[tuple[str, str]] = []
    real_invoke = invoke

    def track_invoke(agent_id, tool, fn, *args, **kwargs):
        gateway_calls.append((agent_id, tool))
        if tool == "github.write":
            from loop.tenant import ConnectorReport

            return ConnectorReport(status="skipped", connector="github.pr", detail="test skip")
        return real_invoke(agent_id, tool, fn, *args, **kwargs)

    monkeypatch.setattr("loop.gateway.invoke", track_invoke)
    monkeypatch.setattr("loop.code_fix.resolve_brief", lambda *a, **k: None)
    engine.approve(action.id, "oncall", "approve", "test")
    engine.execute_approved(action.id)
    assert ("code_agent", "github.write") in gateway_calls


def test_invoke_raises_on_deny():
    with pytest.raises(PermissionError):
        invoke("code_agent", "customer_data.read", lambda: None)
