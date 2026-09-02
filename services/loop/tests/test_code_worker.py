"""Code worker — runner detection and hosted test policy."""

from __future__ import annotations

import stat

from loop.code_worker import (
    NON_RETRYABLE_TEST_ERRORS,
    detect_test_command,
    find_executable,
    node_toolchain_available,
    run_lint_smoke,
    run_tests,
    tenant_has_test_runner,
)


def _fake_toolchain(tmp_path, monkeypatch, names=("node", "npm")):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in names:
        tool = bindir / name
        tool.write_text(f"#!/bin/sh\necho {name}\n")
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir))
    return bindir


def test_find_executable_on_path(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_npm = bindir / "npm"
    fake_npm.write_text("#!/bin/sh\necho npm\n")
    fake_npm.chmod(fake_npm.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir))
    assert find_executable("npm") == str(fake_npm)


def test_find_executable_common_system_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("PATH", raising=False)
    bindir = tmp_path / "usr" / "bin"
    bindir.mkdir(parents=True)
    fake_node = bindir / "node"
    fake_node.write_text("#!/bin/sh\necho node\n")
    fake_node.chmod(fake_node.stat().st_mode | stat.S_IXUSR)
    import loop.code_worker as cw

    monkeypatch.setattr(cw, "_COMMON_BIN_DIRS", (str(bindir),))
    assert find_executable("node") == str(fake_node)


def test_tenant_has_test_runner_false_for_lint_only(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint .","build":"next build"}}')
    _fake_toolchain(tmp_path, monkeypatch)
    assert detect_test_command(repo) is None
    assert tenant_has_test_runner(repo) is False


def test_run_tests_hosted_runs_lint_smoke_when_no_test_script(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint .","build":"next build"}}')
    _fake_toolchain(tmp_path, monkeypatch)
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")

    def fake_run(cmd, repo_path, timeout_s=240):
        if cmd[-2:] == ["run", "lint"]:
            return 0, "LINT_OK"
        return 0, "installed"

    monkeypatch.setattr("loop.code_worker._run_command", fake_run)
    ok, msg = run_tests(repo)
    assert ok is True
    assert "lint smoke passed" in msg


def test_run_tests_hosted_skips_when_no_test_or_lint(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"build":"next build"}}')
    _fake_toolchain(tmp_path, monkeypatch)
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")
    ok, msg = run_tests(repo)
    assert ok is True
    assert "no tenant test script" in msg


def test_run_tests_hosted_fails_when_test_script_but_no_node(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"test":"vitest run"}}')
    monkeypatch.setattr("loop.code_worker.node_toolchain_available", lambda: False)
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")
    ok, msg = run_tests(repo)
    assert ok is False
    assert "node/npm not available" in msg
    assert "defines tests" in msg


def test_run_tests_hosted_skips_lint_when_install_fails(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint ."}}')
    bindir = _fake_toolchain(tmp_path, monkeypatch)
    npm = bindir / "npm"
    npm.write_text("#!/bin/sh\nif [ \"$1\" = ci ] || [ \"$1\" = install ]; then exit 1; fi\nexit 0\n")
    npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")
    ok, msg = run_tests(repo)
    assert ok is True
    assert "lint smoke skipped" in msg
    assert "npm install failed" in msg


def test_run_lint_smoke_fails_when_lint_red(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint ."}}')
    (repo / "node_modules").mkdir()
    _fake_toolchain(tmp_path, monkeypatch)

    def fake_run(cmd, repo_path, timeout_s=240):
        if cmd[-2:] == ["run", "lint"]:
            return 1, "eslint errors"
        return 0, ""

    monkeypatch.setattr("loop.code_worker._run_command", fake_run)
    outcome, msg = run_lint_smoke(repo)
    assert outcome == "fail"
    assert "lint smoke failed" in msg


def test_node_toolchain_available_with_both_tools(tmp_path, monkeypatch):
    _fake_toolchain(tmp_path, monkeypatch)
    assert node_toolchain_available() is True


def test_non_retryable_errors_tuple():
    assert "node/npm not available in worker environment" in NON_RETRYABLE_TEST_ERRORS
