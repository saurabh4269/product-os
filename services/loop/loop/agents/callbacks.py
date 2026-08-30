"""ADK lifecycle hooks — SalesShortcut patterns, ADK 2.0-ready.

SalesShortcut used before_tool_callback for skip-if-done HITL
(e.g. prevent_duplicate_call, _skip_human_creation_if_exists).

ADK 2.0 maps the same idea to:
  - RequestInput pause + resume (HITL gate)
  - before_tool / after_tool on LlmAgent / FunctionNode
  - Idempotent connector replay via store.claim_idempotency

These helpers work without google-adk installed so the hosted
deterministic engine stays the source of truth.
"""

from __future__ import annotations

from typing import Any, Callable


def skip_if_done(state: dict[str, Any] | None, key: str, done_values: set[str] | None = None) -> Any | None:
    """Return a cached result when work already completed; else None (proceed).

    Mirror of SalesShortcut prevent_duplicate_call_callback /
    _skip_human_creation_if_exists. Returning a non-None value skips the tool.
    """
    if not state:
        return None
    existing = state.get(key)
    if existing is None or existing == "":
        return None
    if done_values is None:
        return existing
    if isinstance(existing, dict):
        status = str(existing.get("status") or existing.get("state") or "")
        if status in done_values:
            return existing
        return None
    if str(existing) in done_values:
        return existing
    return None


def before_tool_skip_if_done(
    tool_name: str,
    args: dict[str, Any],
    state: dict[str, Any] | None,
    *,
    key: str,
    tools: set[str] | None = None,
    done_values: set[str] | None = None,
) -> dict[str, Any] | None:
    """ADK before_tool_callback shape: skip matching tools when state says done."""
    if tools is not None and tool_name not in tools:
        return None
    cached = skip_if_done(state, key, done_values)
    if cached is None:
        return None
    return {"result": cached, "reused": True, "tool": tool_name, "args": args}


def after_agent_push(
    push: Callable[[dict[str, Any]], None],
    *,
    room_id: str,
    agent_id: str,
    status: str,
    message: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """SalesShortcut after_agent_callback → UI /agent_callback energy."""
    push(
        {
            "room_id": room_id,
            "agent_id": agent_id,
            "status": status,
            "message": message,
            "kind": "agent_presence",
            "data": data or {},
        }
    )


def hitl_request_input(message: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Document / emit an ADK 2 RequestInput-shaped pause payload."""
    return {
        "type": "RequestInput",
        "message": message,
        "schema": schema or {"decision": {"enum": ["approve", "deny"]}},
        "resume": "POST /api/approvals/{id} (skip-if-done when already executed)",
    }
