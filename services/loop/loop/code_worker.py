"""Code worker — apply patches in a real repo, run tests, fail closed before PR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def apply_patches(repo: Path, patches: dict[str, str]) -> list[str]:
    touched: list[str] = []
    for rel, content in patches.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        touched.append(rel)
    return touched


def detect_test_command(repo: Path) -> list[str] | None:
    override = (os.environ.get("LOOP_CODE_TEST_CMD") or "").strip()
    if override:
        return ["bash", "-lc", override]
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None
    try:
        meta = json.loads(pkg.read_text())
    except json.JSONDecodeError:
        return None
    scripts = meta.get("scripts") if isinstance(meta.get("scripts"), dict) else {}
    if "test" in scripts and scripts["test"]:
        if shutil.which("npm"):
            return ["npm", "test", "--", "--run"]
    if (repo / "vitest.config.ts").is_file() or (repo / "vitest.config.mjs").is_file():
        if shutil.which("npx"):
            return ["npx", "vitest", "run"]
    return None


def run_tests(repo: Path, *, timeout_s: int = 240) -> tuple[bool, str]:
    if os.environ.get("LOOP_CODE_REQUIRE_TESTS", "1" if os.environ.get("K_SERVICE") else "0") != "1":
        return True, "tests skipped (LOOP_CODE_REQUIRE_TESTS=0)"
    cmd = detect_test_command(repo)
    if not cmd:
        if os.environ.get("K_SERVICE") and os.environ.get("LOOP_CODE_REQUIRE_TESTS") == "1":
            return False, "no test runner in worker environment (need node/npm for tenant tests)"
        return True, "no test runner detected — skipped"
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]
        if proc.returncode == 0:
            return True, out or "tests passed"
        return False, out or f"exit {proc.returncode}"
    except subprocess.TimeoutError:
        return False, f"tests timed out after {timeout_s}s"
    except OSError as exc:
        return False, str(exc)


def read_patched_files(repo: Path, rel_paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in rel_paths:
        path = repo / rel
        if path.is_file():
            out[rel] = path.read_text(encoding="utf-8", errors="replace")
    return out


def collect_git_diff_files(repo: Path) -> dict[str, str]:
    """Prefer git-tracked diff; fall back to listing modified paths."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True, timeout=30)
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        )
        names = [n.strip() for n in (proc.stdout or "").splitlines() if n.strip()]
        if names:
            return read_patched_files(repo, names)
    except (subprocess.CalledProcessError, subprocess.TimeoutError, OSError):
        pass
    return {}
