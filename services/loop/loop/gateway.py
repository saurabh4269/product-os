"""Agent Gateway — allow / deny / approval BEFORE any tool runs.

Identity is not a prompt. product-os-v2 pattern: authorize() then invoke().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from . import registry

Decision = Literal["allow", "deny", "approval"]

FORBIDDEN = {
    "customer.export",
    "customer.export.pii",
    "customer_records.dump",
    "customer_data.export",
    "db.dump.customers",
    "send_customer_records",
}

HIGH_RISK = {
    "prod.deploy",
    "deploy.production",
    "gmail.send",
    "workspace.send",
    "db.write.prod",
    "prod.db.write",
    "auth.change",
    "payments.authorize",
    "github.merge",
}


@dataclass
class GateResult:
    decision: Decision
    tool: str
    agent_id: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "tool": self.tool,
            "agentId": self.agent_id,
            "reason": self.reason,
        }


def authorize(agent_id: str, tool: str) -> GateResult:
    entry = registry.by_id().get(agent_id)
    if entry is None:
        return GateResult("deny", tool, agent_id, "unknown agent identity")

    deny = set(entry.permissions_deny) | FORBIDDEN
    if tool in deny:
        return GateResult(
            "deny",
            tool,
            agent_id,
            f"gateway deny: {agent_id} must not call {tool} (identity + policy)",
        )

    if tool in HIGH_RISK:
        return GateResult(
            "approval",
            tool,
            agent_id,
            f"high-risk tool {tool} requires human approval",
        )

    allow = set(entry.permissions_allow)
    if tool in allow:
        return GateResult("allow", tool, agent_id, "allow-list match")

    for allowed in allow:
        if tool.startswith(allowed + ".") or allowed.endswith("*"):
            return GateResult("allow", tool, agent_id, f"allow-list prefix {allowed}")

    # Soft allow for known read tools when agent is analysis-tier and tool not denied.
    if tool.endswith(".read") or tool.startswith("warehouse.") or tool.startswith("ga4."):
        if "warehouse.read" in allow or "ga4.read" in allow or "logs.read" in allow:
            return GateResult("allow", tool, agent_id, "analysis read family")

    return GateResult(
        "deny",
        tool,
        agent_id,
        f"gateway deny: {tool} is not in {agent_id} allow-list",
    )


def invoke(agent_id: str, tool: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    gate = authorize(agent_id, tool)
    if gate.decision == "deny":
        raise PermissionError(gate.reason)
    if gate.decision == "approval":
        raise PermissionError(gate.reason + " (pending approval)")
    return fn(*args, **kwargs)
