"""FastAPI control plane for the console."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .engine import LoopEngine, default_engine
from .models import InvestigationState

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
    if not (cfg.warehouse_path() / "meta.json").exists():
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
        from generate import main as gen

        gen(cfg.warehouse_path())
    get_engine()
    yield


_origin = settings().console_origin
_wildcard = _origin == "*"
app = FastAPI(title="LOOP", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if _wildcard
    else [
        _origin,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveBody(BaseModel):
    approver: str = "oncall@northstar"
    decision: str = "approve"
    rationale: str = "Reviewed evidence graph; blast radius is payment 3DS on Safari."


@app.get("/api/health")
def health():
    return {"ok": True, "service": "loop"}


@app.post("/api/detect")
def detect():
    eng = get_engine()
    signals = eng.detect_signals()
    return {"signals": [s.model_dump(mode="json") for s in signals]}


@app.post("/api/loop/run")
def run_until_approval():
    eng = get_engine()
    inv = eng.run_until_approval()
    return _bundle(eng, inv.id)


@app.get("/api/signals")
def signals():
    return {"signals": [s.model_dump(mode="json") for s in get_engine().store.list_signals()]}


@app.get("/api/investigations")
def investigations():
    eng = get_engine()
    items = []
    for inv in eng.store.list_investigations():
        items.append(_summary(eng, inv.id))
    return {"investigations": items}


@app.get("/api/investigations/{inv_id}")
def investigation(inv_id: str):
    eng = get_engine()
    if not eng.store.get_investigation(inv_id):
        raise HTTPException(404, "investigation not found")
    return _bundle(eng, inv_id)


@app.get("/api/approvals")
def approvals():
    eng = get_engine()
    pending = [a.model_dump(mode="json") for a in eng.store.pending_approvals()]
    history = [a.model_dump(mode="json") for a in eng.store.list_approvals()]
    return {"pending": pending, "history": history}


@app.post("/api/approvals/{action_id}")
def decide(action_id: str, body: ApproveBody):
    eng = get_engine()
    action = eng.store.get_action(action_id)
    if not action:
        raise HTTPException(404, "action not found")
    if body.decision == "approve":
        outcome = eng.resume_after_approval(action_id, body.approver)
        return {"approval": "approve", "outcome": outcome.model_dump(mode="json"), **_bundle(eng, action.investigation_id)}
    approval = eng.approve(action_id, body.approver, "deny", body.rationale)
    return {"approval": approval.model_dump(mode="json"), **_bundle(eng, action.investigation_id)}


@app.get("/api/outcomes")
def outcomes():
    return {"outcomes": [o.model_dump(mode="json") for o in get_engine().store.list_outcomes()]}


@app.get("/api/lessons")
def lessons():
    return {"lessons": [lesson.model_dump(mode="json") for lesson in get_engine().store.list_lessons()]}


@app.get("/api/governance")
def governance():
    eng = get_engine()
    return {
        "identities": [
            {"id": "loop-orchestration", "envelope": "model + own memory only"},
            {"id": "loop-analysis", "envelope": "read-only warehouse/logs/deploys"},
            {"id": "loop-customer", "envelope": "media-bridge + SDP"},
            {"id": "loop-code", "envelope": "github + sandbox; no customer data"},
            {"id": "loop-product", "envelope": "workspace drafts; no merge"},
            {"id": "loop-experiment", "envelope": "flags + metrics"},
            {"id": "loop-learning", "envelope": "memory write"},
        ],
        "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()],
        "failOpen": False,
        "block_on_screening_failure": True,
    }


@app.get("/api/opportunities")
def opportunities():
    return {
        "opportunities": [
            {
                "id": "opp_retry_banner",
                "title": "Retry-after-3DS banner on Safari",
                "frequency": 37,
                "revenue_affected_usd": 18400,
                "churn_risk": "medium",
                "source_query": "events_20260820+ Safari begin_checkout without purchase",
            }
        ]
    }


def _summary(eng: LoopEngine, inv_id: str) -> dict:
    inv = eng.store.get_investigation(inv_id)
    assert inv
    hyps = eng.store.list_hypotheses(inv_id)
    actions = eng.store.list_actions(inv_id)
    return {
        **inv.model_dump(mode="json"),
        "hypothesis": hyps[0].statement if hyps else None,
        "confidence": hyps[0].confidence if hyps else None,
        "risk_tier": actions[0].risk_tier.value if actions else None,
        "action_status": actions[0].status if actions else None,
    }


def _bundle(eng: LoopEngine, inv_id: str) -> dict:
    inv = eng.store.get_investigation(inv_id)
    assert inv
    return {
        "investigation": inv.model_dump(mode="json"),
        "signals": [
            s.model_dump(mode="json")
            for s in (eng.store.get_signal(i) for i in inv.originating_signal_ids)
            if s
        ],
        "evidence": [e.model_dump(mode="json") for e in eng.store.list_evidence(inv_id)],
        "hypotheses": [h.model_dump(mode="json") for h in eng.store.list_hypotheses(inv_id)],
        "actions": [a.model_dump(mode="json") for a in eng.store.list_actions(inv_id)],
        "approvals": [
            ap.model_dump(mode="json")
            for a in eng.store.list_actions(inv_id)
            for ap in eng.store.list_approvals(a.id)
        ],
        "timeline": [t.model_dump(mode="json") for t in eng.store.list_timeline(inv_id)],
        "agent_calls": [c.model_dump(mode="json") for c in eng.store.list_agent_calls(inv_id)],
        "outcomes": [o.model_dump(mode="json") for o in eng.store.list_outcomes() if o.investigation_id == inv_id],
        "lessons": [lesson.model_dump(mode="json") for lesson in eng.store.list_lessons() if lesson.investigation_id == inv_id],
        "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()],
        "state": inv.state.value if isinstance(inv.state, InvestigationState) else inv.state,
    }


def create_app() -> FastAPI:
    return app
