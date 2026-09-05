"""GEAP Runtime client — create/query/fallback (no live GCP in CI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop import geap_memory, geap_runtime


@pytest.fixture(autouse=True)
def _reset_geap(monkeypatch):
    geap_runtime.reset_cache()
    geap_memory.reset_service()
    monkeypatch.delenv("LOOP_GEAP_ENABLED", raising=False)
    monkeypatch.delenv("LOOP_GEAP_AGENT_ENGINE_ID", raising=False)


def test_geap_status_disabled():
    st = geap_runtime.status()
    assert st["enabled"] is False
    assert st["operational"] is False
    assert st["skipped_reason"]


def test_geap_preferred_requires_engine(monkeypatch):
    monkeypatch.setenv("LOOP_GEAP_ENABLED", "1")
    assert geap_runtime.geap_preferred() is False
    monkeypatch.setenv("LOOP_GEAP_AGENT_ENGINE_ID", "12345")
    monkeypatch.setattr(geap_runtime, "sdk_available", lambda: True)
    assert geap_runtime.geap_preferred() is True


def test_engine_resource_name(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
    monkeypatch.setenv("GOOGLE_CLOUD_REGION", "us-central1")
    monkeypatch.setenv("LOOP_GEAP_AGENT_ENGINE_ID", "999")
    assert geap_runtime.engine_resource_name() == "projects/demo-proj/locations/us-central1/reasoningEngines/999"
    monkeypatch.setenv(
        "LOOP_GEAP_AGENT_ENGINE_ID",
        "projects/demo-proj/locations/us-central1/reasoningEngines/888",
    )
    assert geap_runtime.engine_resource_name().endswith("/reasoningEngines/888")


def test_geap_engine_requirements_include_cloudpickle():
    reqs = geap_runtime.geap_engine_requirements()
    assert any("cloudpickle" in r for r in reqs)
    assert any("pydantic" in r for r in reqs)


def test_geap_model_candidates(monkeypatch):
    monkeypatch.delenv("LOOP_GEAP_MODEL", raising=False)
    models = geap_runtime.geap_model_candidates()
    assert models[0] == "gemini-3.5-flash"
    assert "gemini-2.5-flash" in models


def test_query_agent_engine_mock(monkeypatch):
    monkeypatch.setenv("LOOP_GEAP_ENABLED", "1")
    monkeypatch.setenv("LOOP_GEAP_AGENT_ENGINE_ID", "abc")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")

    async def _stream(**_kwargs):
        yield {"text": "Investigate checkout latency."}

    remote = MagicMock()
    remote.async_stream_query = _stream
    monkeypatch.setattr(geap_runtime, "get_remote_agent", lambda **_: remote)

    out = geap_runtime.query_agent_engine("signal metric checkout")
    assert out["ok"] is True
    assert "checkout" in (out.get("reply") or "")


def test_create_agent_engine_mock(engine, monkeypatch):
    import sys

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
    monkeypatch.setattr(geap_runtime, "sdk_available", lambda: True)

    fake_remote = MagicMock()
    fake_remote.api_resource.name = "projects/demo-proj/locations/us-central1/reasoningEngines/777"

    fake_client = MagicMock()
    fake_client.agent_engines.create.return_value = fake_remote

    mock_vertexai = MagicMock()
    mock_vertexai.types.IdentityType.AGENT_IDENTITY = "AGENT_IDENTITY"
    monkeypatch.setitem(sys.modules, "vertexai", mock_vertexai)

    with patch("loop.geap_runtime.build_loop_adk_app", return_value=MagicMock()) as build:
        with patch("loop.geap_runtime.get_client", return_value=fake_client):
            result = geap_runtime.create_agent_engine(engine)
    assert result["agent_engine_id"] == "777"
    assert result["model_id"] == "gemini-3.5-flash"
    build.assert_called_once()
    fake_client.agent_engines.create.assert_called_once()
    req = fake_client.agent_engines.create.call_args.kwargs["config"]["requirements"]
    assert "cloudpickle" in req


def test_create_agent_engine_model_fallback(engine, monkeypatch):
    import sys

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
    monkeypatch.setattr(geap_runtime, "sdk_available", lambda: True)

    fake_remote = MagicMock()
    fake_remote.api_resource.name = "projects/demo-proj/locations/us-central1/reasoningEngines/888"

    fake_client = MagicMock()
    fake_client.agent_engines.create.side_effect = [RuntimeError("3.5 unavailable"), fake_remote]

    mock_vertexai = MagicMock()
    mock_vertexai.types.IdentityType.AGENT_IDENTITY = "AGENT_IDENTITY"
    monkeypatch.setitem(sys.modules, "vertexai", mock_vertexai)

    with patch("loop.geap_runtime.build_loop_adk_app", return_value=MagicMock()):
        with patch("loop.geap_runtime.get_client", return_value=fake_client):
            result = geap_runtime.create_agent_engine(engine)
    assert result["model_id"] == "gemini-2.5-flash"
    assert fake_client.agent_engines.create.call_count == 2


def test_list_agent_engines_mock(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
    monkeypatch.setattr(geap_runtime, "sdk_available", lambda: True)
    item = MagicMock()
    item.api_resource.name = "projects/demo-proj/locations/us-central1/reasoningEngines/1"
    item.api_resource.display_name = "loop-orchestrator"
    fake_client = MagicMock()
    fake_client.agent_engines.list.return_value = [item]
    with patch("loop.geap_runtime.get_client", return_value=fake_client):
        rows = geap_runtime.list_agent_engines()
    assert rows[0]["resource_name"].endswith("/reasoningEngines/1")


def test_dispatch_geap_signal_falls_back_when_disabled(engine, monkeypatch):
    monkeypatch.setattr(geap_runtime, "geap_preferred", lambda: False)
    assert geap_runtime.dispatch_geap_signal(engine, None, {"metric": "x"}) is None


def test_dispatch_signal_prefers_geap(engine, monkeypatch):
    from loop.adk_runtime import dispatch_signal

    called = {"geap": False}

    def fake_geap(*_a, **_k):
        called["geap"] = True
        return {"room_id": "room_test", "backend": "geap_runtime"}

    monkeypatch.setattr("loop.geap_runtime.dispatch_geap_signal", fake_geap)
    out = dispatch_signal(engine, "room_test", {"metric": "checkout"})
    assert called["geap"] is True
    assert out["backend"] == "geap_runtime"


def test_geap_api_status(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/api/geap/status")
        assert res.status_code == 200
        body = res.json()
        assert "geap" in body
        assert "memory_bank" in body
        assert "entitlements_needed" in body


def test_geap_memory_status_api(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        res = client.get("/api/geap/memory")
        assert res.status_code == 200
        assert "memory_bank" in res.json()


def test_adk_status_includes_geap(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        body = client.get("/api/adk/status").json()
    assert "geap" in body
    assert "geap_memory" in body


def test_geap_memory_recall_mock(monkeypatch):
    monkeypatch.setenv("LOOP_GEAP_ENABLED", "1")
    monkeypatch.setenv("LOOP_GEAP_AGENT_ENGINE_ID", "123")
    monkeypatch.setattr(geap_memory, "sdk_available", lambda: True)

    svc = MagicMock()

    async def _search(**_kwargs):
        return {"memories": [{"fact": "OTP verify timeout on Safari"}]}

    svc.search_memory = _search
    monkeypatch.setattr(geap_memory, "_get_service", lambda: svc)

    hits = geap_memory.recall("otp", "safari")
    assert any("OTP" in h for h in hits)
