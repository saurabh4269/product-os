"""Minimal FastAPI app for the ADK worker Cloud Run service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from loop.adk_runtime import adk_available, fleet_status, run_adk_research, run_adk_signal
from loop.auth import require_admin_or_internal
from loop.config import settings
from loop.engine import LoopEngine, default_engine

_engine: LoopEngine | None = None


def get_engine() -> LoopEngine:
    global _engine
    if _engine is None:
        _engine = default_engine()
    return _engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = settings()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    from loop.state_persist import hydrate_db

    hydrate_db(cfg.db_path())
    from loop.runtime_mode import use_file_warehouse

    if use_file_warehouse() and not (cfg.warehouse_path() / "meta.json").exists():
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
        from generate import main as gen

        gen(cfg.warehouse_path())
    eng = get_engine()
    from loop.flags_persist import hydrate_flags

    hydrate_flags(eng.store)
    from loop.tenant import hydrate_all_tenants, seed_placeholder

    hydrate_all_tenants(eng.store)
    if not eng.store.list_rooms():
        eng.seed_world()
    seed_placeholder(eng.store)
    yield


app = FastAPI(title="LOOP ADK Worker", version="0.1.0", lifespan=lifespan)


class SignalBody(BaseModel):
    room_id: str
    signal: dict[str, Any] = Field(default_factory=dict)
    fork: str | None = None
    probe_exfil: bool = False


class ResearchBody(BaseModel):
    event: dict[str, Any] = Field(default_factory=dict)
    kwargs: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    eng = get_engine()
    return {"ok": True, "adk": adk_available(), **fleet_status(eng)}


@app.get("/internal/adk/health")
def adk_health():
    return health()


@app.post("/internal/adk/signal")
def adk_signal(
    body: SignalBody,
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
):
    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    if not adk_available():
        raise HTTPException(503, "google-adk not available on this service")
    eng = get_engine()
    return run_adk_signal(
        eng,
        body.room_id,
        body.signal,
        fork=body.fork,
        probe_exfil=body.probe_exfil,
    )


@app.post("/internal/adk/research")
def adk_research(
    body: ResearchBody,
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
):
    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    if not adk_available():
        raise HTTPException(503, "google-adk not available on this service")
    from loop.customer_research import ResearchEvent

    eng = get_engine()
    event = ResearchEvent.model_validate(body.event)
    return run_adk_research(eng, event, **body.kwargs)
