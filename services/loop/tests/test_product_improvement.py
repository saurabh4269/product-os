"""Generic Type A / Type B product improvement loop."""

from __future__ import annotations

from loop.models import Classification, LoopType, PathKind, RoomKind
from loop.product_improvement import (
    ProductSignalEvent,
    build_experiment_design,
    example_conversion_drop_signal,
    example_shipping_signal,
    resolve_loop,
    run_product_loop,
    simulate_experiment_result,
)


def test_resolve_type_a_vs_b():
    a = ProductSignalEvent(kind="x", metric="m", polarity="negative")
    b = ProductSignalEvent(kind="y", metric="m", polarity="positive")
    assert resolve_loop(a)[0] == LoopType.TYPE_A
    assert resolve_loop(b)[0] == LoopType.TYPE_B
    assert resolve_loop(b)[2] == RoomKind.OPPORTUNITY
    assert resolve_loop(a)[3] == Classification.BUG


def test_type_b_opportunity_experiment_pipeline(engine):
    out = run_product_loop(engine, example_shipping_signal(), scenario_id="test_ship", simulate_outcome=True)
    assert out["loop_type"] == "type_b"
    assert out["pipeline"] == ["detect", "hypothesize", "experiment", "measure", "learn"]
    assert out["experiment"]["treatment"] == "show_delivery_date_earlier"
    assert out["result"]["verdict"] == "ship"
    assert out["lesson"] is not None
    room = engine.store.get_room(out["room_id"])
    assert room is not None
    assert room.kind == RoomKind.OPPORTUNITY
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "hypothesis" in kinds
    assert "experiment_design" in kinds
    assert "experiment_result" in kinds
    assert "product_proposal" in kinds


def test_type_a_fix_pipeline(engine):
    out = run_product_loop(
        engine,
        example_conversion_drop_signal(),
        scenario_id="test_drop",
        simulate_outcome=True,
    )
    assert out["loop_type"] == "type_a"
    assert out["pipeline"] == ["detect", "hypothesize", "fix", "measure", "learn"]
    assert out["hypothesis"]["classification"] == "BUG"
    room = engine.store.get_room(out["room_id"])
    assert room.kind == RoomKind.INCIDENT
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "hypothesis" in kinds
    assert "pr" in kinds or "risk_decision" in kinds


def test_generic_event_no_hardcoded_shipping(engine):
    event = ProductSignalEvent(
        kind="settings_help_loops",
        title="Users loop settings ↔ help",
        metric="help_reopen_rate",
        magnitude=0.22,
        baseline=0.05,
        polarity="positive",
        funnel_position="settings",
        dimensions={
            "evidence": [
                {
                    "source_type": "analytics",
                    "source_reference": "nav_loops",
                    "claim": "22% of settings sessions reopen help within 60s.",
                    "independence_group": "analytics",
                    "collected_by": "analytics_agent",
                },
                {
                    "source_type": "customer_voice",
                    "source_reference": "tickets",
                    "claim": "Cluster: 'where is privacy toggle' n=41.",
                    "independence_group": "voice",
                    "collected_by": "feedback_agent",
                },
                {
                    "source_type": "research",
                    "source_reference": "replay",
                    "claim": "Label 'Data' is misread as export, not privacy.",
                    "independence_group": "ux",
                    "collected_by": "product_agent",
                },
            ],
            "hypothesis": {"statement": "Rename Data → Privacy & data to cut help loops."},
            "experiment": {
                "treatment": "rename_data_label",
                "flag": "rename_data_label",
                "primary_metric": "help_reopen_rate",
                "guardrail": "settings_completion",
                "expected_impact": "Fewer confused navigations into help.",
            },
            "measure": {"control": 0.22, "treatment": 0.09, "verdict": "ship"},
        },
    )
    out = run_product_loop(engine, event, simulate_outcome=True)
    assert out["scenario"] == "improve:settings_help_loops"
    assert out["experiment"]["flag"] == "rename_data_label"
    assert "shipping" not in str(out["event"]).lower()


def test_improve_accepts_evidence_without_source_reference(engine, monkeypatch):
    from fastapi.testclient import TestClient

    import loop.api as api_mod

    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    payload = {
        "kind": "checkout_return_to_shipping",
        "metric": "checkout_return_to_shipping",
        "magnitude": 0.12,
        "baseline": 0.04,
        "polarity": "positive",
        "loop_type": "type_b",
        "scenario_id": "test_thin_evidence",
        "simulate_outcome": True,
        "dimensions": {
            "evidence": [
                {
                    "source_type": "analytics",
                    "claim": "12% return",
                    "independence_group": "a",
                    "collected_by": "analytics_agent",
                },
                {
                    "source_type": "customer_voice",
                    "claim": "late cost",
                    "independence_group": "b",
                    "collected_by": "feedback_agent",
                },
                {
                    "source_type": "research",
                    "claim": "date hunt",
                    "independence_group": "c",
                    "collected_by": "product_agent",
                },
            ]
        },
    }
    with TestClient(api_mod.app) as client:
        res = client.post("/api/improve", json=payload)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["loop_type"] == "type_b"
        assert body["experiment"]["treatment"]
        assert body["result"]["verdict"] == "ship"


def test_shipping_world_seed_still_opportunity(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "shipping_ux")
    assert room.loop_type == LoopType.TYPE_B
    assert room.path == PathKind.FEATURE
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "experiment_design" in kinds


def test_simulate_result_direction():
    ev = example_shipping_signal()
    design = build_experiment_design(ev, "h")
    # without measure override
    ev2 = ProductSignalEvent(
        kind="k",
        metric="m",
        magnitude=0.2,
        baseline=0.2,
        polarity="positive",
        dimensions={"experiment": design.model_dump()},
    )
    r = simulate_experiment_result(ev2, design)
    assert r.treatment < r.control
