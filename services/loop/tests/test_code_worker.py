"""Code worker — runner detection and hosted test policy."""

from __future__ import annotations

import os
import stat

from loop.code_worker import (
    NON_RETRYABLE_TEST_ERRORS,
    detect_test_command,
    find_executable,
    node_toolchain_available,
    run_tests,
)


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


def test_detect_test_command_returns_none_without_test_script(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        '{"scripts":{"dev":"next dev","lint":"eslint .","build":"next build"}}'
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_npm = bindir / "npm"
    fake_npm.write_text("#!/bin/sh\necho npm\n")
    fake_npm.chmod(fake_npm.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir))
    assert detect_test_command(repo) is None


def test_run_tests_hosted_skips_when_node_present_but_no_script(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"build":"next build"}}')
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("node", "npm"):
        tool = bindir / name
        tool.write_text(f"#!/bin/sh\necho {name}\n")
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir))
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")
    ok, msg = run_tests(repo)
    assert ok is True
    assert "no tenant test script" in msg


def test_run_tests_hosted_fails_without_node(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"test":"vitest run"}}')
    monkeypatch.delenv("PATH", raising=False)
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CODE_REQUIRE_TESTS", "1")
    ok, msg = run_tests(repo)
    assert ok is False
    assert "no test runner" in msg


def test_node_toolchain_available_with_both_tools(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("node", "npm"):
        tool = bindir / name
        tool.write_text(f"#!/bin/sh\necho {name}\n")
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir))
    assert node_toolchain_available() is True


def test_non_retryable_errors_tuple():
    assert "no test runner in worker environment" in NON_RETRYABLE_TEST_ERRORS
