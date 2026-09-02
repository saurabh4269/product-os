"""Production vs eval separation — no fixture data on cold start."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.engine import LoopEngine
from loop.store import Store
from loop.warehouse import Warehouse


@pytest.fixture
def prod_client(tmp_path, warehouse_dir, monkeypatch):
    """Hosted production profile — eval off before app lifespan runs."""
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("K_SERVICE", "loop")
    store = Store(tmp_path / "prod-loop.db")
    eng = LoopEngine(store, Warehouse(warehouse_dir))
    monkeypatch.setattr(api_mod, "_engine", eng)
    monkeypatch.setattr(api_mod, "get_engine", lambda: eng)
    with TestClient(api_mod.app) as client:
        yield client, eng
    api_mod._engine = None


def test_production_seed_standing_only(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.delenv("K_SERVICE", raising=False)
    out = engine.seed_world()
    assert out.get("production") is True
    assert engine.store.list_rooms()
    assert not any(r.scenario_id for r in engine.store.list_rooms())
    assert not engine.store.list_investigations()
    lessons = engine.store.list_lessons()
    assert lessons
    assert all(lesson.investigation_id == "inv_prior_org" for lesson in lessons)


def test_production_lifespan_no_safari_regression(prod_client):
    client, eng = prod_client
    assert client.get("/api/config").json()["eval_mode"] is False
    assert not eng.store.list_investigations()
    assert not any(r.scenario_id for r in eng.store.list_rooms())


def test_demo_run_blocked_in_production(prod_client):
    client, _eng = prod_client
    res = client.post("/api/demo/run")
    assert res.status_code == 403


def test_fixture_seed_blocked_in_production(prod_client):
    client, _eng = prod_client
    res = client.post("/api/world/seed")
    assert res.status_code == 403


def test_scenarios_list_does_not_seed_fixtures(prod_client):
    client, eng = prod_client
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    assert res.json()["scenarios"] == []
    assert not eng.store.list_investigations()
