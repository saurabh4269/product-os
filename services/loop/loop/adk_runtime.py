"""ADK 2 worker runtime — separate Cloud Run service or inline when LOOP_ADK_ENABLED=1.

Honest contract (PRD Q-3):
  - Deterministic `run_live_graph` remains CI + fallback.
  - When ADK + GOOGLE_API_KEY are present, build_apps() runs with Workflow-as-Tool
    on orchestrator/investigator and plugins (ToolOutputArmor, RiskGate, Taint).
  - Live Gemini turns are best-effort; quota/billing errors fall back to deterministic graph.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from loop.config import default_model_id


def adk_available() -> bool:
    if os.environ.get("LOOP_ADK_DISABLE") == "1":
        return False
    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_CLOUD_PROJECT")):
        return False
    try:
        import google.adk  # noqa: F401

        return True
    except ImportError:
        return False


def adk_worker_url() -> str:
    return (os.environ.get("LOOP_ADK_WORKER_URL") or "").rstrip("/")


def adk_inline_enabled() -> bool:
    return os.environ.get("LOOP_ADK_ENABLED") == "1" and adk_available()


def fleet_status(engine: Any) -> dict[str, Any]:
    if not adk_available():
        return {"adk": False, "reason": "google-adk not installed or no API key/project"}
    from loop.agents.apps import build_apps
    from loop.agents.workflows import workflow_tools

    apps = build_apps(engine)
    wf = workflow_tools()
    agents = apps.get("_agents") or {}
    orch_tools = getattr(agents.get("orchestrator"), "tools", None) or []
    return {
        "adk": True,
        "apps": [k for k in apps if not k.startswith("_")],
        "agents": len(agents),
        "workflow_tools": len(wf),
        "orchestrator_tools": len(orch_tools),
        "plugins": [p.name for p in apps["loop-orchestration"].plugins],
        "model": default_model_id(),
    }


def _gemini_turn(prompt: str) -> tuple[str | None, str]:
    key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key:
        return None, "no GOOGLE_API_KEY"
    from loop.config import generate_content_config_for

    import httpx

    model = default_model_id()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body: dict[str, Any] = {"contents": [{"parts": [{"text": prompt[:6000]}]}]}
    cfg = generate_content_config_for(model)
    if cfg:
        body["generationConfig"] = cfg
    try:
        res = httpx.post(url, json=body, timeout=60.0)
        if res.status_code != 200:
            return None, res.text[:200]
        payload = res.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return str(text).strip(), "ok"
    except Exception as exc:
        return None, str(exc)[:200]


def run_adk_signal(
    engine: Any,
    room_id: str,
    signal: dict[str, Any],
    *,
    fork: str | None = None,
    probe_exfil: bool = False,
) -> dict[str, Any]:
    """Build ADK fleet, optional Gemini orchestrator note, then deterministic live graph."""
    from loop.agents.graphs import run_live_graph
    from loop.model_armor import screen_chat

    meta = fleet_status(engine)
    summary = None
    if os.environ.get("LOOP_ADK_LLM") != "0":
        prompt = (
            "You are the LOOP orchestrator. One sentence: what should the fleet do next?\n"
            f"Signal JSON: {json.dumps(signal, default=str)[:2000]}"
        )
        blocked, needle, _ = screen_chat(prompt)
        if blocked:
            summary = f"[screened: {needle}]"
        else:
            summary, detail = _gemini_turn(prompt)
            if summary:
                blocked_r, needle_r, _ = screen_chat(summary)
                if blocked_r:
                    summary = f"[response screened: {needle_r}]"
            else:
                meta["llm_skip"] = detail

    graph = run_live_graph(engine, room_id, signal, fork=fork, probe_exfil=probe_exfil)
    if summary:
        from loop.world import post

        post(
            engine,
            room_id,
            author="orchestrator",
            author_kind="agent",
            kind="chat",
            text=summary[:500],
        )
    return {
        **graph,
        "backend": "adk_worker",
        "adk": meta,
        "orchestrator_note": summary,
    }


def run_adk_research(engine: Any, event: Any, **kwargs: Any) -> dict[str, Any]:
    from loop.customer_research import run_customer_research

    meta = fleet_status(engine)
    out = run_customer_research(engine, event, **kwargs)
    if os.environ.get("LOOP_ADK_LLM") != "0" and isinstance(out, dict):
        topic = str(out.get("room_id") or event.kind if hasattr(event, "kind") else "research")
        note, detail = _gemini_turn(f"Brief customer-research takeaway for {topic} in one sentence.")
        if note:
            out["adk_summary"] = note
        else:
            out["adk_llm_skip"] = detail
    out["backend"] = "adk_worker"
    out["adk"] = meta
    return out


def forward_post(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    base = adk_worker_url()
    if not base:
        return None
    url = f"{base}{path}"
    admin = (os.environ.get("LOOP_ADMIN_TOKEN") or "").strip()
    headers = {"Content-Type": "application/json"}
    if admin:
        headers["Authorization"] = f"Bearer {admin}"
        headers["X-Loop-Worker"] = admin
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return {"error": exc.read().decode()[:300], "status": exc.code}
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return {"error": str(exc)[:200]}


def dispatch_signal(
    engine: Any,
    room_id: str,
    signal: dict[str, Any],
    *,
    fork: str | None = None,
    probe_exfil: bool = False,
) -> dict[str, Any]:
    """Worker URL → inline ADK → deterministic graph."""
    forwarded = forward_post(
        "/internal/adk/signal",
        {"room_id": room_id, "signal": signal, "fork": fork, "probe_exfil": probe_exfil},
    )
    if forwarded and "error" not in forwarded:
        return forwarded
    if adk_inline_enabled():
        return run_adk_signal(engine, room_id, signal, fork=fork, probe_exfil=probe_exfil)
    from loop.agents.graphs import run_live_graph

    return run_live_graph(engine, room_id, signal, fork=fork, probe_exfil=probe_exfil)
