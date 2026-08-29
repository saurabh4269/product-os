"""M-10: ADK ModelArmorPlugin does not screen tool output. This plugin does, on after_tool_callback."""

from __future__ import annotations

from typing import Any

from ..engine import log_verdict, screen_tool_output
from ..store import Store

try:
    from google.adk.plugins.base_plugin import BasePlugin as _Base
except Exception:  # pragma: no cover
    class _Base:  # type: ignore[no-redef]
        def __init__(self, name: str | None = None):
            self.name = name or "plugin"


class ToolOutputArmorPlugin(_Base):
    """Registered on the ADK App. Also usable without ADK in tests."""

    name = "tool_output_armor"

    def __init__(self, store: Store, *, block_on_screening_failure: bool = True):
        super().__init__(name="tool_output_armor")
        self.store = store
        self.block_on_screening_failure = block_on_screening_failure

    async def after_tool_callback(
        self,
        *,
        tool: Any = None,
        tool_args: dict | None = None,
        tool_context: Any = None,
        result: Any = None,
        **kwargs: Any,
    ) -> dict | None:
        tool_name = getattr(tool, "name", None) or kwargs.get("tool_name") or "unknown_tool"
        text = _stringify(result)
        if not text:
            if self.block_on_screening_failure:
                log_verdict(
                    self.store,
                    agent="loop-analysis",
                    tool=tool_name,
                    args=str(tool_args or {}),
                    verdict="BLOCK",
                    rationale="Empty tool output treated as screening failure (fail closed).",
                    finding="screening_failure",
                )
                return {
                    "blocked": True,
                    "model_armor_blocked": True,
                    "reason": "screening_failure",
                    "message": "Tool output could not be screened.",
                }
            return None
        hit, needle = screen_tool_output(text)
        if hit:
            log_verdict(
                self.store,
                agent="loop-analysis",
                tool=tool_name,
                args=str(tool_args or {}),
                verdict="BLOCK",
                rationale=f"Prompt-injection pattern in tool output: {needle}",
                finding="prompt_injection",
            )
            return {
                "blocked": True,
                "model_armor_blocked": True,
                "reason": "prompt_injection",
                "needle": needle,
                "message": "Untrusted tool output blocked. Content was not forwarded to the model.",
                "trust": "untrusted",
            }
        return None


def _stringify(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        return " ".join(str(v) for v in result.values())
    return str(result)
