"""FastAPI control plane for the console."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from .config import REPO_ROOT, settings
from .engine import LoopEngine, default_engine, log_verdict
from .live import HUB, funnel_for
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


class TokenRotateBody(BaseModel):
    token: str


class IngestSignalBody(BaseModel):
    metric: str = "purchase_conversion"
    magnitude: float = -0.2
    baseline: float = 0.08
    source: str = "tenant.ingest"
    note: str = ""


class IngestVoiceBody(BaseModel):
    text: str
    tokenized_user: str = "tok_anon"


class GoogleClientBody(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/health")
def health():
    return {"ok": True, "service": "loop", "hosted": bool(os.environ.get("K_SERVICE")), "region": settings().region}


def _visible_flags(eng, tenant_id: str) -> dict[str, str]:
    raw = eng.store.list_flags()
    flags = {k.split(":", 2)[-1]: v for k, v in raw.items() if k.startswith(f"t:{tenant_id}:")}
    globals_ = {k: v for k, v in raw.items() if not k.startswith("t:")}
    for name in ("pay_sdk_4_3", "onboarding_copy_exp_b", "show_delivery_date_earlier"):
        if name not in flags:
            default = "off" if name == "show_delivery_date_earlier" else "on"
            flags[name] = globals_.get(name) or default
    flags["pay_sdk"] = "4.2.1" if flags.get("pay_sdk_4_3") == "off" else "4.3.0"
    return flags


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


def _gate(eng) -> dict:
    from .tenant import seed_placeholder

    seed_placeholder(eng.store)
    tenants = eng.store.list_tenants()
    t = next((x for x in tenants if x.repo), None) or (tenants[0] if tenants else None)
    if t and t.repo:
        return {
            "mode": "github_pr",
            "tenant_repo": t.repo,
            "label": f"Flag changes will open a pull request on {t.repo}. Product OS will not merge it.",
        }
    return {
        "mode": "flag_only",
        "tenant_repo": "",
        "label": "Will only flip an OS flag. No git repo is connected.",
    }


def _action_gate(eng, action) -> dict:
    tenants = eng.store.list_tenants()
    t = next((x for x in tenants if getattr(x, "repo", None)), None)
    repo = (t.repo if t else "") or ""
    arts = action.artifacts or {}
    if "flag" in arts and repo:
        return {
            "mode": "github_pr",
            "tenant_repo": repo,
            "label": f"Will open a pull request on {repo}. Product OS will not merge it.",
        }
    if isinstance(arts.get("github_issue"), dict) and repo:
        return {
            "mode": "github_issue",
            "tenant_repo": repo,
            "label": f"Will open a GitHub issue on {repo}. Product OS will not merge or deploy.",
        }
    if "flag" in arts:
        return {
            "mode": "flag_only",
            "tenant_repo": "",
            "label": "Will only flip an OS flag. No git repo is connected.",
        }
    return {
        "mode": "internal",
        "tenant_repo": repo,
        "label": "This approval stays inside Product OS. No git change.",
    }


def _action_row(eng, action) -> dict:
    row = action.model_dump(mode="json")
    gate = _action_gate(eng, action)
    row["gate"] = gate["label"]
    row["gate_mode"] = gate["mode"]
    row["tenant_repo"] = gate["tenant_repo"]
    return row


@app.get("/api/tenants")
def tenants():
    from .tenant import seed_placeholder

    eng = get_engine()
    seed_placeholder(eng.store)
    return {"tenants": [_public_tenant(t) for t in eng.store.list_tenants()], "gate": _gate(eng)}


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
        last_pr_url=prev.last_pr_url if prev else "",
        last_ingest_at=prev.last_ingest_at if prev else "",
        last_connector=prev.last_connector if prev else "",
    )
    eng.store.put_tenant(t)
    return {"tenant": _public_tenant(t)}


@app.post("/api/tenants/{tenant_id}/token")
def rotate_token(tenant_id: str, body: TokenRotateBody):
    from .tenant import hash_token

    if not body.token.strip():
        raise HTTPException(400, "token required")
    t = get_engine().store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    t.token_hash = hash_token(body.token.strip())
    t.connected = bool(t.repo)
    get_engine().store.put_tenant(t)
    return {"rotated": True, "tenant": _public_tenant(t)}


@app.get("/api/tenants/{tenant_id}")
def tenant_detail(tenant_id: str):
    t = get_engine().store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    return {"tenant": _public_tenant(t), "flags": _visible_flags(get_engine(), tenant_id)}


@app.get("/api/t/{tenant_id}/flags")
def tenant_flags(tenant_id: str, authorization: str | None = Header(default=None)):
    _require_tenant(tenant_id, authorization)
    return {"tenant": tenant_id, "flags": _visible_flags(get_engine(), tenant_id)}


@app.post("/api/t/{tenant_id}/signals")
def tenant_signal(tenant_id: str, body: IngestSignalBody, authorization: str | None = Header(default=None)):
    from .world import ingest_tenant_signal

    t = _require_tenant(tenant_id, authorization)
    out = ingest_tenant_signal(
        get_engine(),
        t,
        metric=body.metric,
        magnitude=body.magnitude,
        baseline=body.baseline,
        note=body.note,
        source=body.source,
    )
    return {
        "signal": out["signal"].model_dump(mode="json"),
        "room_id": out["room_id"],
        "joined": out["joined"],
    }


@app.get("/api/oauth/google")
def google_oauth_status(request: Request):
    from .connectors import google_oauth

    return google_oauth.status(_request_base(request))


@app.post("/api/oauth/google/client")
def google_oauth_client(body: GoogleClientBody):
    from .connectors import google_oauth

    if not body.client_id.strip() or not body.client_secret.strip():
        raise HTTPException(400, "client_id and client_secret required")
    out = google_oauth.save_client(body.client_id, body.client_secret)
    assert "client_secret" not in out
    return out


@app.get("/api/oauth/google/start")
def google_oauth_start(request: Request):
    from .connectors import google_oauth

    url = google_oauth.authorization_url(_request_base(request))
    if not url:
        return RedirectResponse(google_oauth.CONSOLE_OVERVIEW, status_code=302)
    return RedirectResponse(url, status_code=302)


@app.get("/api/oauth/google/callback")
def google_oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    from .connectors import google_oauth

    if error or not code:
        return RedirectResponse(google_oauth.console_return(False, error or "denied"), status_code=302)
    ok, detail = google_oauth.exchange_code(code, state, _request_base(request))
    return RedirectResponse(google_oauth.console_return(ok, "" if ok else detail), status_code=302)


def _request_base(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    if host and "run.app" in host:
        proto = "https"
    if host:
        return f"{proto}://{host}"
    return str(request.base_url).rstrip("/")


@app.post("/api/t/{tenant_id}/voice")
def tenant_voice(tenant_id: str, body: IngestVoiceBody, authorization: str | None = Header(default=None)):
    from .world import ingest_tenant_voice

    t = _require_tenant(tenant_id, authorization)
    out = ingest_tenant_voice(get_engine(), t, text=body.text, tokenized_user=body.tokenized_user)
    return {"voice": out["voice"], "room_id": out["room_id"], "joined": out["joined"]}


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
    awaiting = False
    state = None
    if bundle and bundle.get("investigation"):
        state = bundle["investigation"].get("state")
        awaiting = any(a.get("status") in {"proposed", "awaiting_approval"} for a in bundle.get("actions") or [])
    return {
        "room": room.model_dump(mode="json"),
        "messages": [m.model_dump(mode="json") for m in eng.store.list_messages(room_id)],
        "bundle": bundle,
        "members": room.members,
        "presence": HUB.agents_in(room_id),
        "funnel": funnel_for(room.loop_type, state, awaiting=awaiting),
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
    gate = _gate(eng)
    pending = [_action_row(eng, a) for a in eng.store.pending_approvals()]
    history = [a.model_dump(mode="json") for a in eng.store.list_approvals()]
    return {"pending": pending, "history": history, "gate": gate}


@app.post("/api/approvals/{action_id}")
def decide(action_id: str, body: ApproveBody):
    eng = get_engine()
    action = eng.store.get_action(action_id)
    if not action:
        raise HTTPException(404, "action not found")
    # Skip-if-done HITL (SalesShortcut before_tool_callback pattern).
    if body.decision == "approve" and action.status == "executed":
        execution = (action.artifacts or {}).get("execution") or {}
        return {
            "approval": "approve",
            "reused": True,
            "execution": execution,
            "pr_url": execution.get("pr_url"),
            **_bundle(eng, action.investigation_id),
        }
    if body.decision == "approve":
        outcome = eng.resume_after_approval(action_id, body.approver, body.rationale)
        fresh = eng.store.get_action(action_id)
        execution = ((fresh.artifacts or {}).get("execution") if fresh else None) or {}
        from .live import room_id_for_investigation

        rid = room_id_for_investigation(eng.store, action.investigation_id)
        if rid:
            HUB.publish(
                rid,
                {
                    "type": "approval_resolved",
                    "approval": {"id": action_id, "status": "approved", "reused": False},
                },
            )
        return {
            "approval": "approve",
            "outcome": outcome.model_dump(mode="json"),
            "execution": execution,
            "pr_url": execution.get("pr_url"),
            **_bundle(eng, action.investigation_id),
        }
    approval = eng.approve(action_id, body.approver, "deny", body.rationale)
    return {"approval": approval.model_dump(mode="json"), **_bundle(eng, action.investigation_id)}


@app.post("/api/scenarios/{slug}/run")
def scenario_run(slug: str):
    """Eval fixture runner — explicit chip, not product shape."""
    from .agents.graphs import run_presence_sweep

    eng = get_engine()
    eng.seed_world()
    room = next((r for r in eng.store.list_rooms() if r.scenario_id == slug), None)
    if not room:
        raise HTTPException(404, f"unknown scenario {slug}")
    for mid in room.members:
        HUB.set_presence(room.id, mid, "idle", {"label": mid, "hue": abs(hash(mid)) % 360})
    HUB.publish(room.id, {"type": "signal", "signal": {"scenario": slug, "roomId": room.id}})
    lt = room.loop_type.value if hasattr(room.loop_type, "value") else str(room.loop_type or "")
    fork = "FEATURE" if lt.lower() in {"type_b", "b", "feature"} else "BUG"
    walked = run_presence_sweep(
        room.id,
        fork,
        lambda rid, aid, st: HUB.set_presence(rid, aid, st, {"label": aid, "hue": abs(hash(aid)) % 360}),
        HUB.publish,
    )
    return {
        "scenario": slug,
        "room_id": room.id,
        "room": room.model_dump(mode="json"),
        "funnel": funnel_for(room.loop_type, None),
        "pipeline": walked,
        "presence": HUB.agents_in(room.id),
    }


@app.get("/api/workflows")
def workflows():
    from .agents.graphs import adk2_alignment

    return adk2_alignment()


class AgentCallbackBody(BaseModel):
    room_id: str = ""
    agent_id: str = "orchestrator"
    status: str = "thinking"
    message: str = ""
    kind: str = "agent_presence"
    data: dict = {}


@app.post("/api/agent_callback")
def agent_callback(body: AgentCallbackBody):
    """SalesShortcut-style push: agents POST updates → WebSocket fans out."""
    rid = body.room_id
    if not rid:
        raise HTTPException(400, "room_id required")
    if body.kind == "agent_presence" or body.status:
        HUB.set_presence(rid, body.agent_id, body.status or "thinking", {"label": body.agent_id})
    if body.message:
        from .world import post

        eng = get_engine()
        if eng.store.get_room(rid):
            post(
                eng,
                rid,
                author=body.agent_id,
                author_kind="agent",
                kind="chat",
                text=body.message,
            )
        else:
            HUB.publish(
                rid,
                {
                    "type": "message",
                    "message": {
                        "author": body.agent_id,
                        "author_kind": "agent",
                        "text": body.message,
                        "kind": "chat",
                    },
                },
            )
    if body.data:
        HUB.publish(rid, {"type": body.kind or "trace", "agentId": body.agent_id, "data": body.data})
    return {"ok": True, "room_id": rid, "presence": HUB.agents_in(rid)}


@app.websocket("/ws")
async def ws_global(ws: WebSocket):
    await HUB.connect_global(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        HUB.disconnect("", ws)


@app.websocket("/ws/rooms/{room_id}")
async def ws_room(room_id: str, ws: WebSocket):
    await HUB.connect(room_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        HUB.disconnect(room_id, ws)


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
        "actions": [_action_row(eng, a) for a in eng.store.list_actions(inv_id)],
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
    if rel.split("/", 1)[0] in {"shop", "company"}:
        return None
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
