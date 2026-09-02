"""Memory API — honest Firestore mirror status."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod


def test_memory_includes_mirror_status(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        body = client.get("/api/memory").json()
    assert "mirror" in body
    assert "source" in body
    assert body["mirror"]["enabled"] is False
