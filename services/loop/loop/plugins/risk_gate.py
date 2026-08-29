"""before_tool: HIGH-tier side effects require a durable approval. Limits live here (L-4)."""

from __future__ import annotations

from typing import Any

from ..engine import log_verdict
from ..models import RiskTier
from ..store import Store

try:
    from google.adk.plugins.base_plugin import BasePlugin as _Base
except Exception:  # pragma: no cover
    class _Base:  # type: ignore[no-redef]
        def __init__(self, name: str | None = None):
            self.name = name or "plugin"

HIGH_TOOLS = {
    "execute_flag_rollback",
    "open_pull_request",
    "place_call",
    "write_memory_bank",
    "toggle_feature_flag",
}


class RiskGatePlugin(_Base):
    name = "risk_gate"

    def __init__(self, store: Store):
        super().__init__(name="risk_gate")
        self.store = store

    async def before_tool_callback(
        self,
        *,
        tool: Any = None,
        tool_args: dict | None = None,
        tool_context: Any = None,
        **kwargs: Any,
    ) -> dict | None:
        tool_name = getattr(tool, "name", None) or kwargs.get("tool_name") or ""
        args = tool_args or {}
        if tool_name not in HIGH_TOOLS:
            return None
        action_id = args.get("action_id")
        if not action_id:
            log_verdict(
                self.store,
                agent="loop-code",
                tool=tool_name,
                args=str(args),
                verdict="DENY",
                rationale="HIGH-tier tool missing action_id — denied in tool code (L-4).",
            )
            return {"error": "HIGH_TIER_REQUIRES_ACTION_ID"}
        action = self.store.get_action(action_id)
        if action is None or action.status != "approved":
            log_verdict(
                self.store,
                agent="loop-code",
                tool=tool_name,
                args=str(args),
                verdict="DENY",
                rationale="HIGH-tier action has no recorded human approval.",
            )
            return {"error": "HIGH_TIER_REQUIRES_APPROVAL", "tier": RiskTier.HIGH.value}
        if "idempotency_key" not in args:
            args["idempotency_key"] = action.idempotency_key
        return None
