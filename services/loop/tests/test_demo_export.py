"""Remotion demo export — generic pipeline bundle."""

from __future__ import annotations

import json
from pathlib import Path

from loop.demo_export import WAITING, build_demo_export, build_demo_scenes, write_demo_export

FORBIDDEN = ("safari_3ds", "safari 3ds", "northstar", "pay-sdk 4.3", "northstar pay")


def _assert_no_fixture_copy(text: str) -> None:
    lower = text.lower()
    for token in FORBIDDEN:
        assert token not in lower, f"forbidden demo copy: {token!r}"


def test_build_demo_scenes_from_generic_bundles():
    type_a = {
        "signals": [{"metric": "ticket_volume", "magnitude": 2.4, "baseline": 0.7}],
        "evidence": [
            {"independence_group": "analytics", "source_type": "analytics", "trust_level": "trusted"},
            {"independence_group": "logs", "source_type": "logs", "trust_level": "trusted"},
            {"independence_group": "customer_voice", "source_type": "customer_voice", "trust_level": "trusted"},
        ],
        "hypotheses": [{"statement": "Feature flag correlated with ticket spike."}],
        "actions": [{"risk_tier": "HIGH", "consequence": "Human approval before flag rollback."}],
        "investigation": {"loop_type": "type_a"},
        "lessons": [{"statement": "Flag flips need a ticket-volume guardrail."}],
    }
    scenes = build_demo_scenes(type_a)
    assert len(scenes) == 6
    titles = [s["title"] for s in scenes]
    assert titles == ["Signal", "Evidence", "Root cause", "HIGH approval", "Verified", "Lesson"]
    _assert_no_fixture_copy(json.dumps(scenes))


def test_waiting_scenes_never_invent_fixture_copy():
    scenes = build_demo_scenes({})
    assert len(scenes) == 6
    bodies = {s["title"]: s["body"] for s in scenes}
    assert bodies["Signal"] == WAITING["signal"]
    assert bodies["Evidence"] == WAITING["evidence"]
    assert bodies["Root cause"] == WAITING["root_cause"]
    assert bodies["HIGH approval"] == WAITING["approval"]
    assert bodies["Verified"] == WAITING["verified"]
    assert bodies["Lesson"] == WAITING["lesson"]
    _assert_no_fixture_copy(json.dumps(scenes))


def test_loop_demo_waiting_copy_has_no_fixture_strings():
    root = Path(__file__).resolve().parents[3]
    source = (root / "apps" / "demo" / "src" / "LoopDemo.tsx").read_text()
    waiting_block = source.split("const WAITING = {", 1)[1].split("} as const;", 1)[0]
    _assert_no_fixture_copy(waiting_block)


def test_export_demo_writes_loop_json(tmp_path):
    out = tmp_path / "loop.json"
    write_demo_export(out, data_dir=tmp_path / "data")
    payload = json.loads(out.read_text())
    assert payload.get("scenes")
    assert len(payload["scenes"]) == 6
    assert payload.get("type_a", {}).get("investigation")
    assert payload.get("type_b", {}).get("investigation")
    assert payload.get("gateway_deny", {}).get("verdict") == "DENY"
    _assert_no_fixture_copy(out.read_text())


def test_build_demo_export_has_customer_voice_evidence(tmp_path):
    payload = build_demo_export(data_dir=tmp_path / "export")
    ev = payload.get("evidence") or []
    assert any(e.get("source_type") == "customer_voice" for e in ev)
    _assert_no_fixture_copy(json.dumps(payload.get("scenes") or []))
