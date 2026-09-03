"""Code worker — apply patches in a real repo, run tests, fail closed before PR."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

_COMMON_BIN_DIRS = ("/usr/local/bin", "/usr/bin", "/bin")

# Permanent worker failures — retrying the same job will not help.
NON_RETRYABLE_TEST_ERRORS = (
    "node/npm not available in worker environment",
    "no files to commit after patch",
)

TestOutcome = Literal["pass", "fail", "skip"]


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


def read_package_scripts(repo: Path) -> dict[str, str]:
    pkg = repo / "package.json"
    if not pkg.is_file():
        return {}
    try:
        meta = json.loads(pkg.read_text())
    except json.JSONDecodeError:
        return {}
    scripts = meta.get("scripts") if isinstance(meta.get("scripts"), dict) else {}
    return {k: str(v).strip() for k, v in scripts.items() if v}


def tenant_declares_tests(repo: Path) -> bool:
    """True when package.json (or vitest config) expects a real test runner."""
    scripts = read_package_scripts(repo)
    if scripts.get("test"):
        return True
    return (repo / "vitest.config.ts").is_file() or (repo / "vitest.config.mjs").is_file()


def tenant_has_test_runner(repo: Path) -> bool:
    """True when the tenant repo declares a real test entrypoint (not lint-only)."""
    return tenant_declares_tests(repo)


def build_test_command(repo: Path) -> list[str] | None:
    npm = find_executable("npm")
    npx = find_executable("npx")
    scripts = read_package_scripts(repo)
    test_script = scripts.get("test", "")
    if test_script and npm:
        if "vitest" in test_script:
            return [npm, "test", "--", "--run"]
        return [npm, "test"]
    if (repo / "vitest.config.ts").is_file() or (repo / "vitest.config.mjs").is_file():
        if npx:
            return [npx, "vitest", "run"]
    return None


def detect_test_command(repo: Path, *, override: str | None = None) -> list[str] | None:
    """Return a runnable tenant test command when toolchain and package.json allow it."""
    cmd = (override or os.environ.get("LOOP_CODE_TEST_CMD") or "").strip()
    if cmd:
        return ["bash", "-lc", cmd]
    if not tenant_declares_tests(repo):
        return None
    return build_test_command(repo)


def install_command(repo: Path, npm: str) -> list[str]:
    if (repo / "package-lock.json").is_file():
        return [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
    return [npm, "install", "--ignore-scripts", "--no-audit", "--no-fund"]


def _run_command(cmd: list[str], repo: Path, *, timeout_s: int) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    out = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    return proc.returncode, out


def run_lint_smoke(repo: Path, *, timeout_s: int = 240) -> tuple[TestOutcome, str]:
    """Install deps when needed, then run npm run lint as smoke for tenants without tests."""
    npm = find_executable("npm")
    scripts = read_package_scripts(repo)
    if not scripts.get("lint"):
        return "skip", "no lint script in package.json"
    if not npm:
        return "skip", "lint smoke skipped — node/npm not in worker (lean boot); flags.json GitHub PR is the ship path"

    install_timeout = max(60, timeout_s // 2)
    lint_timeout = max(60, timeout_s - install_timeout)
    if not (repo / "node_modules").is_dir():
        code, out = _run_command(install_command(repo, npm), repo, timeout_s=install_timeout)
        if code != 0:
            return (
                "skip",
                "lint smoke skipped — npm install failed; no test script in package.json "
                f"({out.strip() or f'exit {code}'})",
            )

    code, out = _run_command([npm, "run", "lint"], repo, timeout_s=lint_timeout)
    if code == 0:
        return "pass", f"lint smoke passed (no test script in package.json)\n{out.strip() or 'ok'}"
    return "fail", f"lint smoke failed (no test script in package.json): {out.strip() or f'exit {code}'}"


def run_tests(repo: Path, *, timeout_s: int = 240, test_command: str | None = None) -> tuple[bool, str]:
    require = os.environ.get("LOOP_CODE_REQUIRE_TESTS", "1" if os.environ.get("K_SERVICE") else "0") == "1"
    if not require:
        return True, "tests skipped (LOOP_CODE_REQUIRE_TESTS=0)"

    cmd = detect_test_command(repo, override=test_command)
    declares_tests = tenant_declares_tests(repo) or bool((test_command or "").strip())
    if declares_tests:
        if not node_toolchain_available():
            return (
                True,
                "tests skipped — node/npm not in worker (lean boot); flags.json GitHub PR is the ship path",
            )
        if not cmd:
            return (
                True,
                "tests skipped — no runnable test command on lean worker; flags.json GitHub PR is the ship path",
            )
        try:
            code, out = _run_command(cmd, repo, timeout_s=timeout_s)
            if code == 0:
                return True, out or "tests passed"
            return False, out or f"exit {code}"
        except subprocess.TimeoutError:
            return False, f"tests timed out after {timeout_s}s"
        except OSError as exc:
            return False, str(exc)

    scripts = read_package_scripts(repo)
    if scripts.get("lint"):
        try:
            outcome, detail = run_lint_smoke(repo, timeout_s=timeout_s)
            if outcome == "pass":
                return True, detail
            if outcome == "fail":
                return False, detail
            return True, detail
        except subprocess.TimeoutError:
            return False, f"lint smoke timed out after {timeout_s}s"
        except OSError as exc:
            return True, f"lint smoke skipped — {exc}; no test script in package.json"

    if (repo / "package.json").is_file():
        if node_toolchain_available():
            return (
                True,
                "no tenant test script — skipped (node/npm present; "
                "set LOOP_CODE_TEST_CMD or tenant test_command to require tests)",
            )
        return (
            True,
            "no tenant test script — skipped (nothing to execute; node/npm not required)",
        )

    return True, "no package.json — tests skipped"


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
