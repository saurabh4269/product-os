"""Code worker — apply patches in a real repo, run tests, fail closed before PR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

_COMMON_BIN_DIRS = ("/usr/local/bin", "/usr/bin", "/bin")

# Permanent worker failures — retrying the same job will not help.
NON_RETRYABLE_TEST_ERRORS = (
    "no test runner in worker environment",
    "no files to commit after patch",
)


def find_executable(name: str) -> str | None:
    """Resolve a binary on PATH or common system locations (Cloud Run apt installs)."""
    found = shutil.which(name)
    if found:
        return found
    for directory in _COMMON_BIN_DIRS:
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def node_toolchain_available() -> bool:
    return bool(find_executable("node") and find_executable("npm"))


def apply_patches(repo: Path, patches: dict[str, str]) -> list[str]:
    touched: list[str] = []
    for rel, content in patches.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        touched.append(rel)
    return touched


def detect_test_command(repo: Path, *, override: str | None = None) -> list[str] | None:
    cmd = (override or os.environ.get("LOOP_CODE_TEST_CMD") or "").strip()
    if cmd:
        return ["bash", "-lc", cmd]
    npm = find_executable("npm")
    npx = find_executable("npx")
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None
    try:
        meta = json.loads(pkg.read_text())
    except json.JSONDecodeError:
        return None
    scripts = meta.get("scripts") if isinstance(meta.get("scripts"), dict) else {}
    test_script = str(scripts.get("test") or "").strip()
    if test_script and npm:
        if "vitest" in test_script:
            return [npm, "test", "--", "--run"]
        return [npm, "test"]
    if (repo / "vitest.config.ts").is_file() or (repo / "vitest.config.mjs").is_file():
        if npx:
            return [npx, "vitest", "run"]
    return None


def run_tests(repo: Path, *, timeout_s: int = 240, test_command: str | None = None) -> tuple[bool, str]:
    if os.environ.get("LOOP_CODE_REQUIRE_TESTS", "1" if os.environ.get("K_SERVICE") else "0") != "1":
        return True, "tests skipped (LOOP_CODE_REQUIRE_TESTS=0)"
    cmd = detect_test_command(repo, override=test_command)
    if not cmd:
        if os.environ.get("K_SERVICE") and os.environ.get("LOOP_CODE_REQUIRE_TESTS") == "1":
            if node_toolchain_available():
                return (
                    True,
                    "no tenant test script — skipped (node/npm present; "
                    "set LOOP_CODE_TEST_CMD or tenant test_command to require tests)",
                )
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
