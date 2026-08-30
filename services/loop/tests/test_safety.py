from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loop.engine import log_verdict, redact_pii, screen_tool_output
from loop.plugins.tool_output_armor import ToolOutputArmorPlugin
from loop.tools.side_effects import CONTACT_CAP, MAX_ROLLOUT_PCT, make_side_effect_tools
from loop.tools.untrusted import make_untrusted_tools

ROOT = Path(__file__).resolve().parents[3]


def test_injection_patterns_caught():
    body = json.loads((ROOT / "data" / "fixtures" / "prompt_injection_tool.json").read_text())["issue"]["body"]
    hit, needle = screen_tool_output(body)
    assert hit
    assert needle


def test_after_tool_callback_blocks_and_logs(engine):
    plugin = ToolOutputArmorPlugin(engine.store)
    tools = make_untrusted_tools()
    read_issue = tools[0]
    payload = read_issue(1847)
    blocked = asyncio.run(plugin.after_tool_callback(tool_name="read_github_issue", result=payload))
    assert blocked is not None
    assert blocked["blocked"] is True
    assert blocked["reason"] == "prompt_injection"
    verdicts = engine.store.list_verdicts()
    assert verdicts
    assert verdicts[-1].verdict == "BLOCK"
    assert verdicts[-1].finding_type == "prompt_injection"


def test_empty_tool_output_fails_closed(engine):
    plugin = ToolOutputArmorPlugin(engine.store, block_on_screening_failure=True)
    blocked = asyncio.run(plugin.after_tool_callback(tool_name="read_github_issue", result=""))
    assert blocked["reason"] == "screening_failure"


def test_pii_redacted_from_transcript():
    raw = json.loads((ROOT / "data" / "fixtures" / "pii_transcript.json").read_text())
    text = " ".join(t["text"] for t in raw["turns"])
    red = redact_pii(text)
    assert "priya.sharma" not in red.lower()
    assert "415-555-0199" not in red
    assert "[EMAIL_ADDRESS]" in red
    assert "[PHONE_NUMBER]" in red


def test_hard_limits_in_tool_code(engine):
    tools = {t.__name__: t for t in make_side_effect_tools(engine)}
    assert tools["send_gmail"]()["error"] == "GMAIL_CANNOT_SEND"
    over = tools["experiment_rollout"](80, True, "k1")
    assert over["error"] == "ROLLOUT_CEILING"
    assert over["max"] == MAX_ROLLOUT_PCT
    first = tools["place_call"]("tok_1", "inv_x", "call-1")
    assert first.get("placed")
    second = tools["place_call"]("tok_1", "inv_x", "call-2")
    assert second["error"] == "FREQUENCY_CAP"
    assert CONTACT_CAP == 1


def test_three_source_gate_refuses_single_group(engine):
    signals = engine.detect_signals()
    safari = next(s for s in signals if any(seg.browser == "Safari" for seg in s.affected_segments))
    inv = engine.open_investigation(safari)
    assert inv
    engine._evidence(
        inv,
        source_type="analytics",
        source_reference="events_20260820",
        claim="restated once",
        independence_group="analytics_ga4",
        collected_by="analytics_agent",
        confidence=0.9,
    )
    engine._evidence(
        inv,
        source_type="analytics",
        source_reference="events_20260821",
        claim="restated twice",
        independence_group="analytics_ga4",
        collected_by="analytics_agent",
        confidence=0.9,
    )
    engine._evidence(
        inv,
        source_type="analytics",
        source_reference="events_20260822",
        claim="restated thrice",
        independence_group="analytics_ga4",
        collected_by="analytics_agent",
        confidence=0.9,
    )
    assert engine.form_hypothesis(inv) is None
    _ = log_verdict
