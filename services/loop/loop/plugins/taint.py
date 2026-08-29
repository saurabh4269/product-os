"""M-13: tag customer/external content as untrusted at ingest."""

from __future__ import annotations

from typing import Any

UNTRUSTED_TOOLS = {"read_github_issue", "read_transcript", "search_corpus", "read_email"}

try:
    from google.adk.plugins.base_plugin import BasePlugin as _Base
except Exception:  # pragma: no cover
    class _Base:  # type: ignore[no-redef]
        def __init__(self, name: str | None = None):
            self.name = name or "plugin"


class TaintPlugin(_Base):
    name = "taint"

    def __init__(self):
        super().__init__(name="taint")

    async def after_tool_callback(
        self,
        *,
        tool: Any = None,
        tool_args: dict | None = None,
        result: Any = None,
        **kwargs: Any,
    ) -> dict | None:
        tool_name = getattr(tool, "name", None) or kwargs.get("tool_name") or ""
        if tool_name not in UNTRUSTED_TOOLS:
            return None
        if isinstance(result, dict):
            tagged = dict(result)
            tagged["trust"] = "untrusted"
            tagged["taint"] = "external"
            return tagged
        return {"trust": "untrusted", "taint": "external", "data": result}
