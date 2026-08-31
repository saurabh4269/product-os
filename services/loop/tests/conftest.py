from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "services" / "loop"))

from generate import main as generate_warehouse  # noqa: E402

from loop.engine import LoopEngine  # noqa: E402
from loop.store import Store  # noqa: E402
from loop.warehouse import Warehouse  # noqa: E402


@pytest.fixture(scope="session")
def warehouse_dir(tmp_path_factory) -> Path:
    dest = tmp_path_factory.mktemp("warehouse")
    generate_warehouse(dest)
    return dest


@pytest.fixture(autouse=True)
def _no_background_job_dispatch(monkeypatch):
    """Enqueue must not spawn Cloud Tasks or daemon threads during unit tests."""
    monkeypatch.setattr("loop.jobs.dispatch", lambda _job, _store: None)
    monkeypatch.setenv("LOOP_DEMO_ASYNC", "0")
    monkeypatch.setenv("LOOP_DEMO_STAGE_MS", "0")
    monkeypatch.setenv("LOOP_DEMO_STAGED", "0")


@pytest.fixture()
def engine(tmp_path, warehouse_dir) -> LoopEngine:
    store = Store(tmp_path / "loop.db")
    return LoopEngine(store, Warehouse(warehouse_dir))
