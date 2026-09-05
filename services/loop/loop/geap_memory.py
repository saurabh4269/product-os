"""GEAP Memory Bank adapter — recall via live Agent Engine memory APIs.

Uses ``vertexai.Client.agent_engines.get(...).async_search_memory`` on the
deployed Reasoning Engine (no ``google-adk`` import on the lean host).
Writes use ``agent_engines.memories.create`` on the same client.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from loop.geap_runtime import (
    engine_id_short,
    geap_enabled,
    geap_project,
    geap_region,
    get_client,
    get_remote_agent,
    sdk_available,
)

_last_error: str = ""
_engine: Any | None = None
_engine_tried = False


def enabled() -> bool:
    return geap_enabled() and bool(engine_id_short()) and sdk_available()


def status() -> dict[str, Any]:
    configured = geap_enabled() and bool(engine_id_short())
    if configured and sdk_available() and not _engine_tried:
        _get_engine()
    operational = configured and _engine is not None and not _last_error
    skipped_reason: str | None = None
    if not geap_enabled():
        skipped_reason = "LOOP_GEAP_ENABLED is not 1"
    elif not engine_id_short():
        skipped_reason = "LOOP_GEAP_AGENT_ENGINE_ID unset"
    elif not sdk_available():
        skipped_reason = "vertexai SDK not installed on this service"
    elif _last_error:
        skipped_reason = _last_error[:240]
    elif configured and _engine is None and _engine_tried:
        skipped_reason = "Agent Engine memory APIs unavailable"
    elif configured and not _engine_tried:
        skipped_reason = "Memory Bank not probed yet"
    return {
        "configured": configured,
        "enabled": operational,
        "operational": operational,
        "skipped": not operational,
        "skipped_reason": skipped_reason,
        "agent_engine_id": engine_id_short() or None,
        "memory_bank_uri": f"agentengine://{engine_id_short()}" if engine_id_short() else None,
        "project": geap_project() or None,
        "region": geap_region(),
        "last_error": _last_error or None,
        "backend": "agent_engine.async_search_memory",
    }


def reset_service() -> None:
    global _engine, _engine_tried, _last_error
    _engine = None
    _engine_tried = False
    _last_error = ""


def memory_service_builder() -> Any:
    """Factory for AdkApp memory_service_builder hook (deploy script only)."""
    try:
        from google.adk.memory import VertexAiMemoryBankService

        return VertexAiMemoryBankService(
            project=geap_project(),
            location=geap_region(),
            agent_engine_id=engine_id_short(),
        )
    except Exception as exc:
        _note_error(exc)
        return None


def _note_error(exc: Exception | str) -> None:
    global _last_error
    _last_error = str(exc)[:400]


def _memory_name() -> str:
    short = engine_id_short()
    return f"reasoningEngines/{short}" if short else ""


def _get_engine() -> Any | None:
    """Load remote Agent Engine and confirm memory search is registered."""
    global _engine, _engine_tried
    if _engine_tried:
        return _engine
    _engine_tried = True
    if not enabled():
        return None
    try:
        remote = get_remote_agent()
        if remote is None:
            from loop.geap_runtime import status as runtime_status

            rt_err = runtime_status().get("last_error") or "Agent Engine unavailable"
            _note_error(rt_err)
            _engine = None
            return None
        if not hasattr(remote, "async_search_memory"):
            _note_error(
                "Agent Engine missing async_search_memory — redeploy with memory_service_builder"
            )
            _engine = None
            return None
        global _last_error
        _last_error = ""
        _engine = remote
    except Exception as exc:
        _note_error(exc)
        _engine = None
    return _engine


def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=60)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _extract_memory_text(mem: Any) -> str:
    if isinstance(mem, dict):
        text = str(mem.get("fact") or mem.get("text") or mem.get("content") or "")
        if text:
            return text.strip()
        content = mem.get("content")
        if isinstance(content, dict):
            parts = content.get("parts") or []
            for part in parts:
                if isinstance(part, dict) and part.get("text"):
                    return str(part["text"]).strip()
        return ""
    fact = getattr(mem, "fact", None)
    if fact:
        return str(fact).strip()
    text_attr = getattr(mem, "text", None) or getattr(mem, "content", None)
    if isinstance(text_attr, str) and text_attr.strip():
        return text_attr.strip()
    content = getattr(mem, "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if parts:
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                return str(part_text).strip()
    return str(mem).strip()


def _parse_search_hits(result: Any) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    memories = getattr(result, "memories", None) or (result.get("memories") if isinstance(result, dict) else None)
    if not memories and isinstance(result, list):
        memories = result
    for mem in memories or []:
        text = _extract_memory_text(mem)
        if text and text not in seen:
            hits.append(text)
            seen.add(text)
    return hits[:10]


def recall(*needles: str, tenant_id: str | None = None) -> list[str]:
    """Best-effort Memory Bank search for investigation needles."""
    remote = _get_engine()
    if not remote:
        return []
    query = " ".join(n for n in needles if n).strip()
    if not query:
        return []
    user_id = tenant_id or os.environ.get("LOOP_GEAP_MEMORY_USER", "loop")
    try:
        result = _run_async(remote.async_search_memory(user_id=user_id, query=query))
    except Exception as exc:
        _note_error(exc)
        return []
    return _parse_search_hits(result)


def remember(title: str, body: str, *, tenant_id: str | None = None) -> dict[str, Any]:
    """Explicit Memory Bank write via agent_engines.memories.create."""
    st = status()
    if not enabled():
        return {"ok": False, "mirror": st, "error": st.get("skipped_reason") or "Memory Bank unavailable"}
    name = _memory_name()
    if not name:
        return {"ok": False, "mirror": st, "error": "LOOP_GEAP_AGENT_ENGINE_ID unset"}
    app_name = os.environ.get("LOOP_GEAP_APP_NAME", "loop_orchestration")
    user_id = tenant_id or os.environ.get("LOOP_GEAP_MEMORY_USER", "loop")
    payload = f"{title}\n{body}".strip()
    if not payload:
        return {"ok": False, "mirror": st, "error": "empty memory payload"}
    try:
        cli = get_client()
        cli.agent_engines.memories.create(
            name=name,
            fact=payload,
            scope={"app_name": app_name, "user_id": user_id},
            config={"wait_for_completion": True},
        )
        global _last_error
        _last_error = ""
        return {"ok": True, "mirror": status(), "stored": True}
    except Exception as exc:
        _note_error(exc)
        return {"ok": False, "mirror": status(), "error": str(exc)[:200]}
