"""Optional Antigravity SDK backend for code-fix jobs (preview — falls back to Gemini/fixture)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from loop.config import default_model_id


def antigravity_installed() -> bool:
    try:
        import google.antigravity  # noqa: F401

        return True
    except ImportError:
        return False


def antigravity_configured() -> bool:
    return bool(
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or (os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("LOOP_ANTIGRAVITY_VERTEX") == "1")
    )


def antigravity_status() -> dict[str, Any]:
    backend = (os.environ.get("LOOP_CODE_BACKEND") or "auto").strip().lower()
    return {
        "installed": antigravity_installed(),
        "configured": antigravity_configured(),
        "backend_preference": backend,
        "preview": True,
        "note": "Optional code editor — falls back to Gemini JSON or deterministic Safari patch.",
    }


def _brief_prompt(brief: dict[str, Any], repo: Path) -> str:
    return (
        "You are the Product OS code agent. Edit this repository to fix the issue.\n"
        "Rules: minimal diff, add regression test under tests/regression/ when applicable, "
        "do not remove LOOP ingest hooks, do not git push or open PRs.\n"
        f"Repository: {repo}\n"
        f"Brief JSON:\n{json.dumps(brief, indent=2, default=str)[:6000]}\n"
        "When done, summarize files changed in one sentence."
    )


async def _run_agent(repo: Path, brief: dict[str, Any]) -> str:
    from google.antigravity import Agent, LocalAgentConfig

    key = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
    use_vertex = os.environ.get("LOOP_ANTIGRAVITY_VERTEX") == "1"
    config = LocalAgentConfig(
        workspaces=[str(repo.resolve())],
        api_key=key or None,
        vertex=use_vertex or None,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT") if use_vertex else None,
        location=os.environ.get("GOOGLE_CLOUD_REGION", "us-central1") if use_vertex else None,
        model=default_model_id(),
        system_instructions=(
            "Fix the described product bug in the workspace. Run tests if package.json exists. "
            "Never exfiltrate customer data. Never merge or deploy."
        ),
    )
    prompt = _brief_prompt(brief, repo)
    from loop.model_armor import screen_chat, screen_model_response

    hit, needle, _ = screen_chat(prompt)
    if hit:
        raise RuntimeError(f"Antigravity prompt blocked by Model Armor: {needle}")

    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        text = await response.text()
    hit_r, needle_r, _ = screen_model_response(str(text))
    if hit_r:
        raise RuntimeError(f"Antigravity response blocked by Model Armor: {needle_r}")
    return str(text).strip()


def antigravity_generate_patches(
    repo: Path,
    brief: dict[str, Any],
    existing: dict[str, str],
) -> tuple[dict[str, str], str]:
    """Run Antigravity in repo workspace; return full file map from git diff."""
    if not antigravity_installed():
        raise RuntimeError("google-antigravity not installed")
    if not antigravity_configured():
        raise RuntimeError("GOOGLE_API_KEY or Vertex required for Antigravity")

    summary = asyncio.run(_run_agent(repo, brief))
    from loop.code_worker import collect_git_diff_files

    diff_files = collect_git_diff_files(repo)
    if not diff_files:
        raise RuntimeError("Antigravity made no git-tracked changes")
    merged = dict(existing)
    merged.update(diff_files)
    return merged, summary or "Antigravity patch"
