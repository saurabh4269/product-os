from __future__ import annotations

import pytest

from loop.agents.apps import ALL_AGENT_NAMES, build_apps


def test_build_adk_apps(engine):
    pytest.importorskip("google.adk")
    apps = build_apps(engine)
    for key in (
        "loop-orchestration",
        "loop-analysis",
        "loop-customer",
        "loop-code",
        "loop-product",
        "loop-experiment",
        "loop-learning",
    ):
        assert key in apps
        app = apps[key]
        assert app.resumability_config is not None
        assert app.resumability_config.is_resumable is True
        names = [p.name for p in app.plugins]
        assert "tool_output_armor" in names
    agents = apps["_agents"]
    assert set(ALL_AGENT_NAMES) == set(agents)
    assert agents["signal_agent"].model == "gemini-3.5-flash"
