"""GEAP Agent Runtime client — managed Reasoning Engine for LOOP orchestration.

Uses client-based ``vertexai.Client`` (SDK >=1.112). Fail closed: when GEAP is
unavailable the caller falls back to ADK worker / inline ADK / LoopEngine.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

_DEFAULT_STAGING_BUCKET = "gs://mystical-timing-442601-q8-loop-host"
_last_error: str = ""
_cached_remote: Any | None = None


def geap_enabled() -> bool:
    return os.environ.get("LOOP_GEAP_ENABLED", "").strip() == "1"


def geap_engine_id() -> str:
    return (os.environ.get("LOOP_GEAP_AGENT_ENGINE_ID") or "").strip()


def geap_staging_bucket() -> str:
    return (os.environ.get("LOOP_GEAP_STAGING_BUCKET") or _DEFAULT_STAGING_BUCKET).strip()


def geap_project() -> str:
    return (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()


def geap_region() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_REGION")
        or os.environ.get("GOOGLE_CLOUD_LOCATION")
        or "us-central1"
    ).strip()


def sdk_available() -> bool:
    try:
        import vertexai  # noqa: F401

        return True
    except ImportError:
        return False


def engine_id_short(raw: str | None = None) -> str:
    value = (raw or geap_engine_id()).strip()
    if not value:
        return ""
    if "/" in value:
        return value.rsplit("/", 1)[-1]
    return value


def engine_resource_name(engine_id: str | None = None) -> str:
    eid = (engine_id or geap_engine_id()).strip()
    if not eid:
        return ""
    if eid.startswith("projects/"):
        return eid
    project = geap_project()
    region = geap_region()
    short = engine_id_short(eid)
    if not project or not short:
        return eid
    return f"projects/{project}/locations/{region}/reasoningEngines/{short}"


def geap_configured() -> bool:
    return geap_enabled() and bool(geap_project()) and bool(geap_engine_id() or sdk_available())


def geap_preferred() -> bool:
    """True when hosted path should try GEAP before local ADK orchestration."""
    return geap_enabled() and bool(geap_engine_id()) and sdk_available()


def _note_error(exc: Exception | str) -> None:
    global _last_error
    _last_error = str(exc)[:400]


def reset_cache() -> None:
    global _cached_remote, _last_error
    _cached_remote = None
    _last_error = ""


def status() -> dict[str, Any]:
    configured = geap_enabled()
    has_engine = bool(geap_engine_id())
    sdk = sdk_available()
    operational = configured and has_engine and sdk and not _last_error
    skipped_reason: str | None = None
    if not configured:
        skipped_reason = "LOOP_GEAP_ENABLED is not 1"
    elif not has_engine:
        skipped_reason = "LOOP_GEAP_AGENT_ENGINE_ID unset — run scripts/deploy-geap-agent.sh"
    elif not sdk:
        skipped_reason = "google-cloud-aiplatform[agent_engines,adk] not installed on this service"
    elif _last_error:
        skipped_reason = _last_error[:240]
    return {
        "enabled": geap_enabled(),
        "configured": configured,
        "operational": operational,
        "skipped": not operational,
        "skipped_reason": skipped_reason,
        "sdk": sdk,
        "project": geap_project() or None,
        "region": geap_region(),
        "agent_engine_id": geap_engine_id() or None,
        "agent_engine_short_id": engine_id_short() or None,
        "resource_name": engine_resource_name() or None,
        "staging_bucket": geap_staging_bucket(),
        "memory_bank_uri": f"agentengine://{engine_id_short()}" if engine_id_short() else None,
        "last_error": _last_error or None,
        "preferred": geap_preferred(),
    }


def build_loop_adk_app(engine: Any) -> Any:
    """Wrap LOOP orchestrator LlmAgent in AdkApp for Agent Runtime deploy."""
    from loop.adk_runtime import adk_available

    if not adk_available():
        raise RuntimeError("google-adk not installed — required to build AdkApp")
    from loop.agents.apps import build_apps

    apps = build_apps(engine)
    orchestrator = (apps.get("_agents") or {}).get("orchestrator")
    if orchestrator is None:
        raise RuntimeError("orchestrator agent missing from build_apps()")

    from vertexai import agent_engines

    memory_builder = None
    if engine_id_short():
        from loop.geap_memory import memory_service_builder

        memory_builder = memory_service_builder
    return agent_engines.AdkApp(agent=orchestrator, memory_service_builder=memory_builder)


def get_client() -> Any:
    from vertexai import Client

    project = geap_project()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT required for GEAP client")
    return Client(project=project, location=geap_region())


def get_remote_agent(*, client: Any | None = None, force_refresh: bool = False) -> Any | None:
    """Load an existing Agent Engine by LOOP_GEAP_AGENT_ENGINE_ID."""
    global _cached_remote
    if _cached_remote is not None and not force_refresh:
        return _cached_remote
    name = engine_resource_name()
    if not name:
        _note_error("LOOP_GEAP_AGENT_ENGINE_ID unset")
        return None
    if not sdk_available():
        _note_error("vertexai SDK not installed")
        return None
    try:
        cli = client or get_client()
        remote = cli.agent_engines.get(name=name)
        _cached_remote = remote
        global _last_error
        _last_error = ""
        return remote
    except Exception as exc:
        _note_error(exc)
        _cached_remote = None
        return None


def create_agent_engine(engine: Any, *, display_name: str = "loop-orchestrator") -> dict[str, Any]:
    """Create a new Reasoning Engine from LOOP AdkApp. Used by deploy script."""
    if not sdk_available():
        raise RuntimeError("google-cloud-aiplatform[agent_engines,adk] not installed")
    from vertexai import types

    app = build_loop_adk_app(engine)
    client = get_client()
    remote = client.agent_engines.create(
        agent=app,
        config={
            "display_name": display_name,
            "requirements": ["google-cloud-aiplatform[agent_engines,adk]>=1.112", "google-adk>=2.8.0"],
            "staging_bucket": geap_staging_bucket(),
            "identity_type": types.IdentityType.AGENT_IDENTITY,
        },
    )
    resource = getattr(getattr(remote, "api_resource", None), "name", None) or str(remote)
    global _cached_remote
    _cached_remote = remote
    return {
        "resource_name": resource,
        "agent_engine_id": engine_id_short(str(resource)),
        "display_name": display_name,
    }


def _collect_async_stream(coro: Any) -> list[Any]:
    async def _run() -> list[Any]:
        events: list[Any] = []
        async for event in coro:
            events.append(event)
        return events

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # FastAPI / nested loop — run in a fresh loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _run()).result(timeout=120)
        return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())


def _event_text(event: Any) -> str:
    if isinstance(event, dict):
        for key in ("text", "content", "message", "output"):
            val = event.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return json.dumps(event, default=str)[:2000]
    text = getattr(event, "text", None) or getattr(event, "content", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return str(event)[:2000]


def query_agent_engine(
    message: str,
    *,
    user_id: str = "loop",
    session_id: str | None = None,
    engine: Any | None = None,
) -> dict[str, Any]:
    """Sync wrapper around remote ``async_stream_query``."""
    remote = get_remote_agent()
    if remote is None:
        return {"ok": False, "error": _last_error or "GEAP agent engine unavailable"}
    prompt = message[:6000]
    kwargs: dict[str, Any] = {"user_id": user_id, "message": prompt}
    if session_id:
        kwargs["session_id"] = session_id
    try:
        stream = remote.async_stream_query(**kwargs)
        events = _collect_async_stream(stream)
        text_parts = [_event_text(ev) for ev in events]
        reply = "\n".join(p for p in text_parts if p).strip()
        return {
            "ok": True,
            "reply": reply or None,
            "events": len(events),
            "backend": "geap_runtime",
            "agent_engine_id": engine_id_short(),
        }
    except Exception as exc:
        _note_error(exc)
        return {"ok": False, "error": str(exc)[:300], "backend": "geap_runtime"}


def _signal_prompt(signal: dict[str, Any], *, room_id: str | None = None) -> str:
    room_bit = f"Room {room_id}. " if room_id else ""
    return (
        "You are the LOOP investigation orchestrator on GEAP Agent Runtime. "
        f"{room_bit}One sentence: what should the fleet do next?\n"
        f"Signal JSON: {json.dumps(signal, default=str)[:2500]}"
    )


def dispatch_geap_signal(
    engine: Any,
    room_id: str | None,
    signal: dict[str, Any],
    *,
    fork: str | None = None,
    probe_exfil: bool = False,
) -> dict[str, Any] | None:
    """Query GEAP Runtime, then run local investigation pipeline for persistence/UI."""
    if not geap_preferred():
        return None
    from loop.model_armor import screen_chat

    prompt = _signal_prompt(signal, room_id=room_id)
    blocked, needle, _ = screen_chat(prompt)
    geap_out: dict[str, Any] = {"backend": "geap_runtime", "geap": status()}
    if blocked:
        geap_out["orchestrator_note"] = f"[screened: {needle}]"
    else:
        q = query_agent_engine(prompt, user_id=room_id or "loop-signal")
        geap_out["geap_query"] = q
        if q.get("ok") and q.get("reply"):
            reply = str(q["reply"])
            blocked_r, needle_r, _ = screen_chat(reply)
            geap_out["orchestrator_note"] = f"[response screened: {needle_r}]" if blocked_r else reply[:500]
        elif not q.get("ok"):
            return {"error": q.get("error", "GEAP query failed"), **geap_out}

    from loop.unified_runner import run_signal_pipeline

    local = run_signal_pipeline(engine, room_id, signal, fork=fork, probe_exfil=probe_exfil)
    if geap_out.get("orchestrator_note") and local.get("room_id"):
        from loop.world import post

        post(
            engine,
            str(local["room_id"]),
            author="orchestrator",
            author_kind="agent",
            kind="chat",
            text=str(geap_out["orchestrator_note"])[:500],
        )
    return {**local, **geap_out}


def dispatch_geap_research(engine: Any, event: Any, **kwargs: Any) -> dict[str, Any] | None:
    """GEAP note + local customer research pipeline."""
    if not geap_preferred():
        return None
    topic = getattr(event, "kind", None) or getattr(event, "topic", None) or "research"
    prompt = (
        "You are the LOOP customer-research orchestrator on GEAP Agent Runtime. "
        f"Brief one-sentence takeaway plan for event kind={topic}."
    )
    q = query_agent_engine(prompt, user_id="loop-research")
    from loop.customer_research import run_customer_research

    out = run_customer_research(engine, event, **kwargs)
    out["backend"] = "geap_runtime"
    out["geap"] = status()
    out["geap_query"] = q
    if q.get("ok") and q.get("reply"):
        out["geap_summary"] = str(q["reply"])[:500]
    return out
