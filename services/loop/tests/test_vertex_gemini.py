"""Vertex Gemini routing."""

from __future__ import annotations

from loop.vertex_gemini import gemini_configured, use_vertex


def test_use_vertex_env(monkeypatch):
    monkeypatch.delenv("LOOP_USE_VERTEX", raising=False)
    monkeypatch.delenv("LOOP_VERTEX_GEMINI", raising=False)
    assert use_vertex() is False
    monkeypatch.setenv("LOOP_USE_VERTEX", "1")
    assert use_vertex() is True


def test_gemini_configured_vertex(monkeypatch):
    monkeypatch.setenv("LOOP_USE_VERTEX", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert gemini_configured() is True
