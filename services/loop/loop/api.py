"""FastAPI control plane for the console."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import REPO_ROOT, settings
from .engine import LoopEngine, default_engine, log_verdict
from .models import InvestigationState
from .office import agent_snapshot, office_snapshot
from .registry import ENTRIES, gateway_allows
from .world import post as post_room

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
    eng = get_engine()
    if not eng.store.list_rooms():
        eng.seed_world()
    elif not eng.store.list_investigations():
        eng.run_until_approval()
    from .tenant import seed_placeholder

    seed_placeholder(eng.store)
    yield


_origin = settings().console_origin
_wildcard = _origin == "*" or bool(os.environ.get("K_SERVICE"))
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
    rationale: str = "Reviewed the evidence pack and risk gate."


class RoomPostBody(BaseModel):
    author: str = "you"
    text: str


class TenantBody(BaseModel):
    id: str
    name: str
    product: str
    repo: str = ""
    deploy_url: str = ""
    token: str = ""


class IngestSignalBody(BaseModel):
    metric: str = "purchase_conversion"
    magnitude: float = -0.2
    baseline: float = 0.08
    source: str = "tenant.ingest"
    note: str = ""


class IngestVoiceBody(BaseModel):
    text: str
    tokenized_user: str = "tok_anon"


@app.get("/api/health")
def health():
    return {"ok": True, "service": "loop", "hosted": bool(os.environ.get("K_SERVICE")), "region": settings().region}


def _public_tenant(t) -> dict:
    d = t.model_dump()
    d.pop("token_hash", None)
    d["has_token"] = bool(t.token_hash)
    return d


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return authorization.strip()


def _require_tenant(tenant_id: str, authorization: str | None):
    from .tenant import token_ok

    t = get_engine().store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    if not token_ok(t, _bearer(authorization)):
        raise HTTPException(401, "tenant token required")
    return t


@app.get("/api/tenants")
def tenants():
    from .tenant import seed_placeholder

    eng = get_engine()
    seed_placeholder(eng.store)
    return {"tenants": [_public_tenant(t) for t in eng.store.list_tenants()]}


@app.post("/api/tenants")
def upsert_tenant(body: TenantBody):
    from .tenant import Tenant, hash_token

    eng = get_engine()
    prev = eng.store.get_tenant(body.id)
    token_hash = hash_token(body.token) if body.token else (prev.token_hash if prev else "")
    t = Tenant(
        id=body.id,
        name=body.name,
        product=body.product,
        repo=body.repo,
        deploy_url=body.deploy_url,
        token_hash=token_hash,
        connected=bool(body.repo),
    )
    eng.store.put_tenant(t)
    return {"tenant": _public_tenant(t)}


@app.get("/api/tenants/{tenant_id}")
def tenant_detail(tenant_id: str):
    from .tenant import flag_key

    t = get_engine().store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    flags = {
        k.split(":", 2)[-1]: v
        for k, v in get_engine().store.list_flags().items()
        if k.startswith(flag_key(tenant_id, ""))
    }
    return {"tenant": _public_tenant(t), "flags": flags}


@app.get("/api/t/{tenant_id}/flags")
def tenant_flags(tenant_id: str, authorization: str | None = Header(default=None)):
    _require_tenant(tenant_id, authorization)
    raw = get_engine().store.list_flags()
    flags = {k.split(":", 2)[-1]: v for k, v in raw.items() if k.startswith(f"t:{tenant_id}:")}
    globals_ = {k: v for k, v in raw.items() if not k.startswith("t:")}
    for name in ("pay_sdk_4_3", "onboarding_copy_exp_b", "show_delivery_date_earlier"):
        if name not in flags:
            default = "off" if name == "show_delivery_date_earlier" else "on"
            flags[name] = globals_.get(name) or default
    return {"tenant": tenant_id, "flags": flags}


@app.post("/api/t/{tenant_id}/signals")
def tenant_signal(tenant_id: str, body: IngestSignalBody, authorization: str | None = Header(default=None)):
    from datetime import datetime, timezone

    from .engine import _id
    from .models import Direction, Segment, Signal, SignalFamily, SignalStatus
    from .world import post as post_room

    _require_tenant(tenant_id, authorization)
    eng = get_engine()
    sig = Signal(
        id=_id("sig"),
        family=SignalFamily.BUSINESS,
        direction=Direction.NEGATIVE if body.magnitude < 0 else Direction.POSITIVE,
        funnel_position="ingest",
        metric=body.metric,
        magnitude=body.magnitude,
        baseline=body.baseline,
        affected_segments=[Segment(channel="tenant")],
        detection_window={"source": body.source},
        confidence=0.6,
        source=f"tenant.{tenant_id}",
        status=SignalStatus.OPEN,
        detected_at=datetime.now(timezone.utc),
    )
    eng.store.put_signal(sig)
    rooms = [r for r in eng.store.list_rooms() if r.kind.value == "incident"]
    room = rooms[0] if rooms else None
    if room:
        post_room(
            eng,
            room.id,
            author="signal_agent",
            author_kind="agent",
            kind="artifact",
            text=body.note or f"{body.metric} {body.magnitude} from {tenant_id}",
            artifact_type="signal",
            artifact={"signal_id": sig.id, "tenant": tenant_id},
        )
    return {"signal": sig.model_dump(mode="json"), "room_id": room.id if room else None}


@app.post("/api/t/{tenant_id}/voice")
def tenant_voice(tenant_id: str, body: IngestVoiceBody, authorization: str | None = Header(default=None)):
    from .engine import _id

    _require_tenant(tenant_id, authorization)
    eng = get_engine()
    rec = {
        "id": _id("voice"),
        "kind": "customer",
        "tenant": tenant_id,
        "tokenized_user": body.tokenized_user,
        "text": body.text[:4000],
        "channel": "tenant.ingest",
    }
    eng.store.put_memory(rec["id"], "customer", rec)
    return {"voice": rec}


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


@app.post("/api/world/seed")
def world_seed():
    return get_engine().seed_world()


@app.get("/api/rooms")
def rooms():
    eng = get_engine()
    items = []
    for room in eng.store.list_rooms():
        msgs = eng.store.list_messages(room.id)
        items.append(
            {
                **room.model_dump(mode="json"),
                "message_count": len(msgs),
                "preview": msgs[-1].text if msgs else room.topic,
            }
        )
    return {"rooms": items}


@app.get("/api/rooms/{room_id}")
def room_detail(room_id: str):
    eng = get_engine()
    room = eng.store.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    bundle = _bundle(eng, room.investigation_id) if room.investigation_id and eng.store.get_investigation(room.investigation_id) else None
    return {
        "room": room.model_dump(mode="json"),
        "messages": [m.model_dump(mode="json") for m in eng.store.list_messages(room_id)],
        "bundle": bundle,
        "members": room.members,
    }


@app.post("/api/rooms/{room_id}/messages")
def room_post(room_id: str, body: RoomPostBody):
    eng = get_engine()
    room = eng.store.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    post_room(eng, room_id, author=body.author, author_kind="human", kind="chat", text=body.text)
    low = body.text.lower()
    if any(n in low for n in ("customer records", "production database", "dump all customer", "send me the customer")):
        if not gateway_allows("code_agent", "customer_data.read"):
            log_verdict(
                eng.store,
                agent="loop-code",
                tool="prod_db.query",
                args=body.text,
                verdict="DENY",
                rationale="Gateway identity loop-code denied customer_data.read.",
                finding="exfil_attempt",
            )
            post_room(
                eng,
                room_id,
                author="security_policy_agent",
                author_kind="agent",
                kind="artifact",
                text="DENY · identity/gateway. Engineering cannot read customer records.",
                artifact_type="risk_decision",
                artifact={"verdict": "DENY", "finding": "exfil_attempt"},
            )
    return room_detail(room_id)


@app.get("/api/registry")
def registry():
    return {"agents": [e.model_dump(mode="json") for e in ENTRIES]}


@app.get("/api/memory")
def memory():
    eng = get_engine()
    by_kind: dict[str, list] = {"customer": [], "product": [], "engineering": [], "organizational": []}
    for item in eng.store.list_memory():
        kind = item.get("kind") or "organizational"
        by_kind.setdefault(kind, []).append(item)
    return {"memory": by_kind, "lessons": [lesson.model_dump(mode="json") for lesson in eng.store.list_lessons()]}


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": get_engine().seed_world().get("scenarios")}


@app.get("/api/traces")
def traces():
    eng = get_engine()
    calls = []
    for inv in eng.store.list_investigations():
        calls.extend(c.model_dump(mode="json") for c in eng.store.list_agent_calls(inv.id))
    return {"traces": calls, "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()]}


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
            {"id": "loop-security", "envelope": "gateway + identity; deny customer_records.dump"},
        ],
        "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()],
        "failOpen": False,
        "block_on_screening_failure": True,
    }


@app.get("/api/opportunities")
def opportunities():
    eng = get_engine()
    items = []
    for room in eng.store.list_rooms():
        if room.kind.value != "opportunity":
            continue
        items.append(
            {
                "id": room.scenario_id or room.id,
                "title": room.title,
                "room_id": room.id,
                "status": room.status,
                "loop_type": room.loop_type.value if room.loop_type else "type_b",
            }
        )
    return {"opportunities": items}


@app.get("/api/metrics")
def metrics():
    eng = get_engine()
    invs = eng.store.list_investigations()
    outcomes = eng.store.list_outcomes()
    closed = [i for i in invs if i.closed_at and i.opened_at]
    hours = []
    for i in closed:
        delta = (i.closed_at - i.opened_at).total_seconds() / 3600
        hours.append(delta)
    return {
        "idea_to_impact_hours_mean": round(sum(hours) / len(hours), 3) if hours else None,
        "idea_to_impact_target_hours": 48,
        "baseline_manual_hours": 504,
        "investigations": len(invs),
        "resolved": sum(1 for o in outcomes if str(o.verdict) in {"RESOLVED", "OutcomeVerdict.RESOLVED", "resolved"}),
        "failOpen": False,
    }


@app.get("/api/office")
def office():
    return office_snapshot(get_engine())


@app.get("/api/agents")
def agents():
    return {
        "agents": [
            {
                "id": e.id,
                "room": e.room,
                "role": e.role,
                "tb": e.trust_boundary,
                "status": e.status,
                "owner": e.owner,
                "identity": e.identity,
                "risk_level": e.risk_level,
                "version": e.version,
            }
            for e in ENTRIES
        ]
    }


@app.get("/api/agents/{agent_id}")
def agent_detail(agent_id: str):
    snap = agent_snapshot(get_engine(), agent_id)
    if not snap:
        raise HTTPException(404, "agent not found")
    return snap


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


def _static_dir() -> Path | None:
    env = os.environ.get("LOOP_STATIC_DIR")
    candidates = [
        Path(env) if env else None,
        REPO_ROOT / "apps" / "console" / "out",
        Path("/app/static"),
    ]
    for c in candidates:
        if c and (c / "index.html").exists():
            return c
    return None


_STATIC = _static_dir()


def _spa_file(path: str) -> FileResponse | None:
    if _STATIC is None:
        return None
    if path.startswith("api/"):
        return None
    rel = path.strip("/")
    if not rel:
        return FileResponse(_STATIC / "index.html")
    direct = _STATIC / rel
    if direct.is_file():
        return FileResponse(direct)
    nested = _STATIC / rel / "index.html"
    if nested.is_file():
        return FileResponse(nested)
    if rel.startswith("investigations/") or rel.startswith("rooms/") or rel.startswith("agents/"):
        folder = "rooms" if rel.startswith("rooms/") else "investigations" if rel.startswith("investigations/") else "agents"
        for placeholder in (
            _STATIC / folder / "_" / "index.html",
            _STATIC / folder / "_.html",
        ):
            if placeholder.is_file():
                return FileResponse(placeholder)
    html = _STATIC / f"{rel}.html"
    if html.is_file():
        return FileResponse(html)
    return FileResponse(_STATIC / "index.html")


if _STATIC is not None:

    @app.get("/", include_in_schema=False)
    def hosted_root():
        return FileResponse(_STATIC / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def hosted_spa(path: str):
        page = _spa_file(path)
        if page is None:
            raise HTTPException(404)
        return page


def create_app() -> FastAPI:
    return app
