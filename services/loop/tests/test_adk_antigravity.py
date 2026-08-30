"""ADK status, Antigravity backend routing, code backend prefs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.antigravity_fix import antigravity_status
from loop.code_fix import generate_patches


def test_adk_status_endpoint(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/api/adk/status")
        assert res.status_code == 200
        body = res.json()
        assert "adk_installed" in body
        assert "antigravity" in body
        assert body["code_backend"] in {"auto", "gemini", "antigravity", "deterministic", "fixture"}


def test_antigravity_status_shape():
    st = antigravity_status()
    assert st["preview"] is True
    assert "installed" in st


def test_generate_patches_safari_fixture(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src" / "app" / "(store)" / "checkout").mkdir(parents=True)
    (repo / "src" / "lib").mkdir(parents=True)
    (repo / "src" / "app" / "(store)" / "checkout" / "page.tsx").write_text(
        'await new Promise((r) => setTimeout(r, 2200));'
    )
    (repo / "src" / "lib" / "loop.ts").write_text(
        'export const x = () => flags.pay_sdk === "4.3.0" || flags.pay_sdk_4_3 === "on";'
    )
    brief = {"fixture_id": "safari_3ds", "issue": "Safari hang"}
    patches, summary, backend = generate_patches(repo, brief)
    assert backend == "fixture"
    assert "tests/regression" in str(patches)


def test_generate_patches_auto_tries_antigravity_before_gemini(tmp_path, monkeypatch):
    monkeypatch.setenv("LOOP_CODE_BACKEND", "auto")
    order: list[str] = []

    def fake_ag(*_a, **_k):
        order.append("antigravity")
        raise RuntimeError("skip ag")

    def fake_gem(*_a, **_k):
        order.append("gemini")
        return {"src/a.ts": "x\n"}, "ok"

    monkeypatch.setattr("loop.antigravity_fix.antigravity_generate_patches", fake_ag)
    monkeypatch.setattr("loop.code_fix.gemini_generate_patches", fake_gem)
    repo = tmp_path / "repo"
    repo.mkdir()
    brief = {"issue": "generic bug", "likely_files": ["src/a.ts"]}
    _, _, backend = generate_patches(repo, brief)
    assert order == ["antigravity", "gemini"]
    assert backend == "gemini"
