"""GEAP Memory Bank adapter — optional recall path via VertexAiMemoryBankService."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from loop.geap_runtime import (
    engine_id_short,
    geap_enabled,
    geap_project,
    geap_region,
    sdk_available,
)

_last_error: str = ""
_service: Any | None = None
_service_tried = False


def enabled() -> bool:
    return geap_enabled() and bool(engine_id_short()) and sdk_available()


def status() -> dict[str, Any]:
    configured = geap_enabled() and bool(engine_id_short())
    operational = configured and _service is not None and not _last_error
    skipped_reason: str | None = None
    if not geap_enabled():
        skipped_reason = "LOOP_GEAP_ENABLED is not 1"
    elif not engine_id_short():
        skipped_reason = "LOOP_GEAP_AGENT_ENGINE_ID unset"
    elif not sdk_available():
        skipped_reason = "Memory Bank SDK not installed on this service"
    elif _last_error:
        skipped_reason = _last_error[:240]
    elif configured and _service is None and _service_tried:
        skipped_reason = "VertexAiMemoryBankService unavailable"
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
    }


def reset_service() -> None:
    global _service, _service_tried, _last_error
    _service = None
    _service_tried = False
    _last_error = ""


def memory_service_builder() -> Any:
    """Factory for AdkApp memory_service_builder hook."""
    return _get_service()


def _note_error(exc: Exception | str) -> None:
    global _last_error
    _last_error = str(exc)[:400]


def _get_service() -> Any | None:
    global _service, _service_tried
    if _service_tried:
        return _service
    _service_tried = True
    if not enabled():
        return None
    try:
        from google.adk.memory import VertexAiMemoryBankService

        _service = VertexAiMemoryBankService(
            project=geap_project(),
            location=geap_region(),
            agent_engine_id=engine_id_short(),
        )
        global _last_error
        _last_error = ""
    except Exception as exc:
        _note_error(exc)
        _service = None
    return _service


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


def recall(*needles: str, tenant_id: str | None = None) -> list[str]:
    """Best-effort Memory Bank search for investigation needles."""
    svc = _get_service()
    if not svc:
        return []
    query = " ".join(n for n in needles if n).strip()
    if not query:
        return []
    app_name = os.environ.get("LOOP_GEAP_APP_NAME", "loop_orchestration")
    user_id = tenant_id or os.environ.get("LOOP_GEAP_MEMORY_USER", "loop")
    try:
        if hasattr(svc, "search_memory"):
            result = _run_async(svc.search_memory(app_name=app_name, user_id=user_id, query=query))
        else:
            return []
    except Exception as exc:
        _note_error(exc)
        return []
    hits: list[str] = []
    seen: set[str] = set()
    memories = getattr(result, "memories", None) or (result.get("memories") if isinstance(result, dict) else None)
    if not memories and isinstance(result, list):
        memories = result
    for mem in memories or []:
        text = ""
        if isinstance(mem, dict):
            text = str(mem.get("fact") or mem.get("text") or mem.get("content") or "")
        else:
            text = str(getattr(mem, "fact", None) or getattr(mem, "text", None) or mem)
        text = text.strip()
        if text and text not in seen:
            hits.append(text)
            seen.add(text)
    return hits[:10]


def remember(title: str, body: str, *, tenant_id: str | None = None) -> dict[str, Any]:
    """Explicit Memory Bank write when SDK supports add_memory."""
    svc = _get_service()
    st = status()
    if not svc:
        return {"ok": False, "mirror": st, "error": _last_error or "Memory Bank unavailable"}
    app_name = os.environ.get("LOOP_GEAP_APP_NAME", "loop_orchestration")
    user_id = tenant_id or os.environ.get("LOOP_GEAP_MEMORY_USER", "loop")
    payload = f"{title}\n{body}".strip()
    try:
        if hasattr(svc, "add_memory"):
            _run_async(
                svc.add_memory(
                    app_name=app_name,
                    user_id=user_id,
                    memory={"fact": payload},
                )
            )
            return {"ok": True, "mirror": status(), "stored": True}
        return {"ok": False, "mirror": st, "error": "add_memory not supported by SDK version"}
    except Exception as exc:
        _note_error(exc)
        return {"ok": False, "mirror": status(), "error": str(exc)[:200]}
