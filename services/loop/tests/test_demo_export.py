"""Remotion demo export — generic pipeline bundle."""

from __future__ import annotations

import json

from loop.demo_export import build_demo_export, build_demo_scenes, write_demo_export


def test_build_demo_scenes_from_generic_bundles():
    type_a = {
        "signals": [{"metric": "ticket_volume", "magnitude": 2.4, "baseline": 0.7}],
        "evidence": [
            {"independence_group": "analytics", "source_type": "analytics", "trust_level": "trusted"},
            {"independence_group": "logs", "source_type": "logs", "trust_level": "trusted"},
            {"independence_group": "customer_voice", "source_type": "customer_voice", "trust_level": "trusted"},
        ],
        "hypotheses": [{"statement": "Feature flag correlated with ticket spike."}],
        "actions": [{"risk_tier": "MEDIUM", "consequence": "Human approval before flag rollback."}],
        "investigation": {"loop_type": "type_a"},
        "lessons": [{"statement": "Flag flips need a ticket-volume guardrail."}],
    }
    type_b = {"investigation": {"loop_type": "type_b"}}
    gateway = {"verdict": "DENY", "tool": "customer_records.dump"}
    scenes = build_demo_scenes(type_a, type_b, gateway)
    assert len(scenes) == 6
    text = json.dumps(scenes).lower()
    assert "safari" not in text
    assert "3ds" not in text
    assert "pay_sdk" not in text
    assert any(s["title"] == "Gateway deny" for s in scenes)


def test_export_demo_writes_loop_json(tmp_path):
    out = tmp_path / "loop.json"
    write_demo_export(out, data_dir=tmp_path / "data")
    payload = json.loads(out.read_text())
    assert payload.get("scenes")
    assert len(payload["scenes"]) >= 6
    assert payload.get("type_a", {}).get("investigation")
    assert payload.get("type_b", {}).get("investigation")
    assert payload.get("gateway_deny", {}).get("verdict") == "DENY"
    blob = out.read_text().lower()
    assert "safari_3ds" not in blob
    assert "northstar pay" not in blob


def test_build_demo_export_has_customer_voice_evidence(tmp_path):
    payload = build_demo_export(data_dir=tmp_path / "export")
    ev = payload.get("evidence") or []
    assert any(e.get("source_type") == "customer_voice" for e in ev)
