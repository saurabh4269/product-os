"""FastAPI control plane for the console."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

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
    from loop.state_persist import hydrate_db

    hydrate_db(cfg.db_path())
    if not (cfg.warehouse_path() / "meta.json").exists():
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
        from generate import main as gen

        gen(cfg.warehouse_path())
    eng = get_engine()
    from loop.flags_persist import hydrate_flags

    hydrate_flags(eng.store)
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


class SignalInBody(BaseModel):
    source: str = "ga4"
    polarity: str = "negative"
    domain: str = "technical"
    metric: str = "conversion"
    delta: float | None = None
    title: str | None = None
    dimensions: dict = {}
    fork: str | None = None
    scenario: str | None = None


class MemoryInBody(BaseModel):
    type: str = "engineering"
    title: str
    body: str = ""
    tags: list[str] = []
    room_id: str | None = None


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
    phone: str = ""
    sentiment: str = ""
    meta: dict = Field(default_factory=dict)


class PlaceCallBody(BaseModel):
    to_number: str
    reason: str = "checkout issue"
    room_id: str = ""
    product: str = "Cove"
    tokenized_user: str = "tok_anon"


class ResearchEventBody(BaseModel):
    """Generic research event — any recipe posts one of these; abandon is just an example."""

    kind: str
    user_id: str
    title: str = ""
    topic: str = ""
    phone: str = ""
    metric: str = "customer_research"
    funnel_position: str = "product"
    dimensions: dict = Field(default_factory=dict)
    memory_conditions: list[str] = Field(default_factory=list)
    place_real_call: bool = False
    scenario_id: str | None = None
    loop_type: str = "type_a"
    path: str = "bug"
    room_kind: str = "research"


class ImproveEventBody(BaseModel):
    """Generic Type A/B product signal — detect → hypothesize → fix|experiment → measure → learn."""

    kind: str
    metric: str
    magnitude: float = 0.0
    baseline: float = 0.0
    title: str = ""
    topic: str = ""
    funnel_position: str = "product"
    confidence: float = 0.8
    source: str = "warehouse"
    family: str = "business"
    polarity: str | None = None
    loop_type: str | None = None
    path: str | None = None
    room_kind: str | None = None
    dimensions: dict = Field(default_factory=dict)
    memory_conditions: list[str] = Field(default_factory=list)
    scenario_id: str | None = None
    simulate_outcome: bool = True


class CoordinateBody(BaseModel):
    """Generic HITL coordination — owners → calendar → schedule → notify (never auto-merge)."""

    kind: str = "review_request"
    title: str
    subject: str = ""
    surface: str = ""
    risk_tier: str = "MEDIUM"
    owners: list[str] = Field(default_factory=list)
    duration_minutes: int | None = None
    prefer_meet: bool | None = None
    notify_channels: list[str] = Field(default_factory=lambda: ["gmail_draft", "room"])
    room_id: str | None = None
    action_id: str | None = None
    investigation_id: str | None = None
    pr_url: str | None = None
    dimensions: dict = Field(default_factory=dict)
    apply_calendar: bool = True


class InvestigateBody(BaseModel):
    """Broad anomaly → parallel investigators → evidence pack → hypothesis → briefs."""

    kind: str
    metric: str
    title: str = ""
    family: str = "business"
    magnitude: float = 0.0
    baseline: float = 0.0
    funnel_position: str = "product"
    polarity: str | None = None
    dimensions: dict = Field(default_factory=dict)
    scenario_id: str | None = None
    propose_action: bool = True
    action_type: str = "code_change"
    surface: str | None = None


class ProductIntelBody(BaseModel):
    """N customer mentions → one product proposal (not N GitHub issues)."""

    mentions: list[dict] = Field(default_factory=list)
    theme: str | None = None
    title: str | None = None
    scenario_id: str | None = None
    competitor_capability: bool | None = None
    implementation_estimate: str = "medium"
    revenue_affected_usd: float | None = None


class CalendarSuggestBody(BaseModel):
    duration_minutes: int = 30
    calendars: list[str] | None = None
    time_min: str = ""
    time_max: str = ""
    limit: int = 5


class GoogleClientBody(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/health")
def health():
    return {"ok": True, "service": "loop", "hosted": bool(os.environ.get("K_SERVICE")), "region": settings().region}


@app.get("/api/status")
def status():
    """SalesShortcut dashboard energy — funnel counts, presence, gates (not a CRUD board)."""
    eng = get_engine()
    rooms = eng.store.list_rooms()
    pending = eng.store.pending_approvals()
    presence_n = sum(len(v) for v in HUB.presence.values())
    open_rooms = [r for r in rooms if r.status == "open"]
    by_kind: dict[str, int] = {}
    for r in rooms:
        k = r.kind.value if hasattr(r.kind, "value") else str(r.kind)
        by_kind[k] = by_kind.get(k, 0) + 1
    stages: dict[str, int] = {}
    for rid, agents in HUB.presence.items():
        for ev in agents.values():
            st = str(ev.get("status") or "idle")
            stages[st] = stages.get(st, 0) + 1
    from .connectors import google_oauth

    oauth = google_oauth.status()
    return {
        "ok": True,
        "running": True,
        "rooms": {"total": len(rooms), "open": len(open_rooms), "by_kind": by_kind},
        "approvals_pending": len(pending),
        "presence": {"agents": presence_n, "by_status": stages},
        "funnel": {
            "signal": by_kind.get("incident", 0) + by_kind.get("opportunity", 0),
            "approve": len(pending),
            "learn": len(eng.store.list_lessons()),
        },
        "workspace": {"connected": bool(oauth.get("connected")), "email": oauth.get("email") or ""},
        "patterns": ["parallel_fanout", "review_critique", "skip_if_done", "agent_callback"],
    }


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
def upsert_tenant(body: TenantBody, authorization: str | None = Header(default=None)):
    from .auth import require_admin
    from .audit import record

    actor = require_admin(authorization, actor=f"tenant:{body.id}")
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
    record(eng.store, actor=actor, action="tenant.upsert", resource=f"tenant:{t.id}", detail={"repo": t.repo})
    return {"tenant": _public_tenant(t)}


@app.post("/api/tenants/{tenant_id}/token")
def rotate_token(tenant_id: str, body: TokenRotateBody, authorization: str | None = Header(default=None)):
    from .auth import require_admin
    from .audit import record

    actor = require_admin(authorization, actor=f"tenant:{tenant_id}")
    from .tenant import hash_token

    if not body.token.strip():
        raise HTTPException(400, "token required")
    t = get_engine().store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    t.token_hash = hash_token(body.token.strip())
    t.connected = bool(t.repo)
    get_engine().store.put_tenant(t)
    record(get_engine().store, actor=actor, action="tenant.rotate_token", resource=f"tenant:{tenant_id}")
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
def google_oauth_client(body: GoogleClientBody, authorization: str | None = Header(default=None)):
    from .auth import require_admin

    require_admin(authorization, actor="oauth")
    from .connectors import google_oauth

    if not body.client_id.strip() or not body.client_secret.strip():
        raise HTTPException(400, "client_id and client_secret required")
    try:
        out = google_oauth.save_client(body.client_id, body.client_secret)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    assert "client_secret" not in out
    return out


@app.get("/api/oauth/google/start")
def google_oauth_start(request: Request):
    from .connectors import google_oauth

    url = google_oauth.authorization_url(_request_base(request))
    if not url:
        # Do not send users to Cloud Console — that page often shows "denied"
        # when they only need to paste a Web client on Connect first.
        return RedirectResponse(
            google_oauth.console_return(False, "Paste OAuth client ID and secret on Connect first"),
            status_code=302,
        )
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
    phone = body.phone or str((body.meta or {}).get("phone") or "")
    out = ingest_tenant_voice(
        get_engine(),
        t,
        text=body.text,
        tokenized_user=body.tokenized_user,
        phone=phone,
    )
    return {
        "voice": out["voice"],
        "room_id": out["room_id"],
        "joined": out["joined"],
        "classification": out.get("classification"),
    }


@app.get("/api/telephony")
def telephony_status():
    from .customer_research import telephony_capabilities

    caps = telephony_capabilities()
    return {
        "twilio": caps["twilio_outbound"],
        "gemini": caps["gemini"],
        "google_inbound": caps["google_telephony"]["inbound"],
        "google_outbound": False,
        "mode": caps["default_mode"],
        "detail": caps["google_telephony"]["detail"],
        "capabilities": caps,
    }


@app.get("/api/adk/status")
def adk_status():
    """Connect / judges — ADK fleet + Antigravity + worker routing (honest)."""
    from loop.adk_runtime import adk_available, adk_inline_enabled, adk_worker_url, fleet_status
    from loop.antigravity_fix import antigravity_status
    from loop.code_fix import code_backend
    from loop.vertex_gemini import gemini_configured, use_vertex

    eng = get_engine()
    worker = adk_worker_url()
    fleet = None
    if adk_available():
        try:
            fleet = fleet_status(eng)
        except Exception as exc:
            fleet = {"error": str(exc)[:200]}
    return {
        "adk_installed": adk_available(),
        "adk_inline": adk_inline_enabled(),
        "adk_worker_url": worker or None,
        "worker_reachable": bool(worker),
        "fleet": fleet,
        "antigravity": antigravity_status(),
        "code_backend": code_backend(),
        "vertex_gemini": use_vertex(),
        "gemini_configured": gemini_configured(),
        "pitch": "ADK orchestrates on worker; gateway + Model Armor enforce; jobs clone → test → PR.",
    }


@app.post("/api/research")
def research_event(body: ResearchEventBody):
    """Generic event → probes → brief → call → structured evidence (recipe-agnostic)."""
    from .adk_runtime import adk_inline_enabled, forward_post, run_adk_research
    from .customer_research import ResearchEvent, run_customer_research
    from .models import LoopType, PathKind, RoomKind

    eng = get_engine()
    eng.seed_world()
    lt = LoopType.TYPE_A if body.loop_type.lower() in {"type_a", "a", "bug"} else LoopType.TYPE_B
    path = PathKind.BUG if body.path.lower() in {"bug", "a"} else PathKind.FEATURE
    try:
        rk = RoomKind(body.room_kind)
    except ValueError:
        rk = RoomKind.RESEARCH
    event = ResearchEvent(
        kind=body.kind,
        user_id=body.user_id,
        title=body.title,
        topic=body.topic,
        phone=body.phone,
        metric=body.metric,
        funnel_position=body.funnel_position,
        dimensions=body.dimensions,
        memory_conditions=body.memory_conditions,
        loop_type=lt,
        path=path,
        room_kind=rk,
    )
    kwargs = {
        "place_real_call": body.place_real_call,
        "scenario_id": body.scenario_id,
    }
    forwarded = forward_post(
        "/internal/adk/research",
        {"event": event.model_dump(mode="json"), "kwargs": kwargs},
    )
    if forwarded and "error" not in forwarded:
        out = forwarded
    elif adk_inline_enabled():
        out = run_adk_research(eng, event, **kwargs)
    else:
        out = run_customer_research(eng, event, **kwargs)
    room = eng.store.get_room(out["room_id"])
    return {
        **out,
        "room": room.model_dump(mode="json") if room else None,
        "pipeline": ["investigate", "brief", "memory", "call", "structured_evidence"],
        "presence": HUB.agents_in(out["room_id"]) if out.get("room_id") else [],
    }


@app.post("/api/improve")
def improve_event(body: ImproveEventBody):
    """Type A/B product loop — detect → hypothesize → fix|experiment → measure → learn."""
    from .models import LoopType, PathKind, RoomKind
    from .product_improvement import ProductSignalEvent, run_product_loop

    eng = get_engine()
    eng.seed_world()
    lt = None
    if body.loop_type:
        lt = LoopType.TYPE_A if body.loop_type.lower() in {"type_a", "a", "bug"} else LoopType.TYPE_B
    path = None
    if body.path:
        path = PathKind.BUG if body.path.lower() in {"bug", "a", "security"} else PathKind.FEATURE
    rk = None
    if body.room_kind:
        try:
            rk = RoomKind(body.room_kind)
        except ValueError:
            rk = None
    polarity = body.polarity if body.polarity in {"negative", "positive"} else None
    event = ProductSignalEvent(
        kind=body.kind,
        metric=body.metric,
        magnitude=body.magnitude,
        baseline=body.baseline,
        title=body.title,
        topic=body.topic,
        funnel_position=body.funnel_position,
        confidence=body.confidence,
        source=body.source,
        family=body.family if body.family in {"business", "technical", "customer"} else "business",
        polarity=polarity,  # type: ignore[arg-type]
        loop_type=lt,
        path=path,
        room_kind=rk,
        dimensions=body.dimensions,
        memory_conditions=body.memory_conditions,
    )
    out = run_product_loop(
        eng,
        event,
        scenario_id=body.scenario_id,
        simulate_outcome=body.simulate_outcome,
    )
    room = eng.store.get_room(out["room_id"])
    return {
        **out,
        "room": room.model_dump(mode="json") if room else None,
        "presence": HUB.agents_in(out["room_id"]) if out.get("room_id") else [],
    }


@app.get("/api/calendar")
def calendar_status():
    from .connectors import calendar as cal

    return cal.capabilities()


@app.post("/api/calendar/suggest")
def calendar_suggest(body: CalendarSuggestBody):
    from .connectors import calendar as cal

    return cal.suggest_times(
        duration_minutes=body.duration_minutes,
        calendars=body.calendars,
        time_min=body.time_min,
        time_max=body.time_max,
        limit=body.limit,
    )


@app.post("/api/coordinate")
def coordinate(body: CoordinateBody):
    """HITL in company workflow: resolve owners → calendar → schedule → notify. Never merges."""
    from .coordination import CoordinationRequest, coordinate_for_action, run_coordination

    eng = get_engine()
    if body.action_id:
        out = coordinate_for_action(
            eng,
            body.action_id,
            kind=body.kind,
            title=body.title,
            surface=body.surface,
            owners=body.owners,
            duration_minutes=body.duration_minutes,
            prefer_meet=body.prefer_meet,
            notify_channels=body.notify_channels,
            dimensions=body.dimensions,
        )
        return out

    tier = body.risk_tier.upper() if body.risk_tier else "MEDIUM"
    if tier not in {"LOW", "MEDIUM", "HIGH"}:
        tier = "MEDIUM"
    req = CoordinationRequest(
        kind=body.kind,
        title=body.title,
        subject=body.subject,
        surface=body.surface,
        risk_tier=tier,  # type: ignore[arg-type]
        owners=body.owners,
        duration_minutes=body.duration_minutes,
        prefer_meet=body.prefer_meet,
        notify_channels=body.notify_channels,
        room_id=body.room_id,
        investigation_id=body.investigation_id,
        pr_url=body.pr_url,
        dimensions=body.dimensions,
    )
    return run_coordination(eng, req, apply_calendar=body.apply_calendar)


@app.get("/api/signals/catalog")
def signals_catalog():
    from .investigation import catalog

    return catalog()


@app.post("/api/investigate")
def investigate(body: InvestigateBody):
    """Parallel investigation workflow — not 'conversion dropped' alone."""
    from .investigation import AnomalyEvent, run_investigation

    eng = get_engine()
    eng.seed_world()
    family = body.family if body.family in {"funnel", "technical", "business", "customer"} else "business"
    polarity = body.polarity if body.polarity in {"negative", "positive"} else None
    event = AnomalyEvent(
        kind=body.kind,
        metric=body.metric,
        title=body.title,
        family=family,  # type: ignore[arg-type]
        magnitude=body.magnitude,
        baseline=body.baseline,
        funnel_position=body.funnel_position,
        polarity=polarity,  # type: ignore[arg-type]
        dimensions=body.dimensions,
    )
    out = run_investigation(
        eng,
        event,
        scenario_id=body.scenario_id,
        propose_action=body.propose_action,
        action_type=body.action_type,
        surface=body.surface,
    )
    room = eng.store.get_room(out["room_id"])
    return {
        **out,
        "room": room.model_dump(mode="json") if room else None,
        "presence": HUB.agents_in(out["room_id"]) if out.get("room_id") else [],
    }


@app.post("/api/product-intel")
def product_intel(body: ProductIntelBody):
    """Cluster feature requests → one PM proposal."""
    from .investigation import FeatureMention, run_product_intelligence

    eng = get_engine()
    eng.seed_world()
    mentions = [
        FeatureMention(
            text=str(m.get("text") or ""),
            user_id=str(m.get("user_id") or ""),
            channel=str(m.get("channel") or "voice"),
            revenue_hint_usd=m.get("revenue_hint_usd"),
        )
        for m in body.mentions
        if m.get("text")
    ]
    est = body.implementation_estimate if body.implementation_estimate in {"low", "medium", "high"} else "medium"
    out = run_product_intelligence(
        eng,
        mentions,
        theme=body.theme,
        title=body.title,
        scenario_id=body.scenario_id,
        competitor_capability=body.competitor_capability,
        implementation_estimate=est,  # type: ignore[arg-type]
        revenue_affected_usd=body.revenue_affected_usd,
    )
    return out


@app.post("/api/calls")
def place_outbound_call(body: PlaceCallBody):
    """Human-triggered outbound call from a room (SalesShortcut OutreachCaller energy)."""
    from .connectors.voice import place_call
    from .world import post as room_post

    eng = get_engine()
    report = place_call(
        body.tokenized_user,
        body.reason,
        to_number=body.to_number,
        room_id=body.room_id,
        product=body.product,
    )
    if body.room_id and eng.store.get_room(body.room_id):
        room_post(
            eng,
            body.room_id,
            author="outreach_caller",
            author_kind="agent",
            kind="artifact",
            text=report.detail,
            artifact_type="call",
            artifact=report.model_dump(),
        )
    return {"report": report.model_dump()}


@app.post("/api/twilio/voice")
async def twilio_voice(
    request: Request,
    room: str = Query(default=""),
    reason: str = Query(default="checkout"),
    product: str = Query(default="Cove"),
):
    from .telephony import put_session, twiml_open

    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    if call_sid:
        put_session(
            call_sid,
            {
                "to": str(form.get("To") or ""),
                "room_id": room,
                "reason": reason,
                "product": product,
                "status": "in-progress",
                "turns": 0,
                "transcript": [],
            },
        )
    xml = twiml_open(room, reason, product)
    return Response(content=xml, media_type="application/xml")


@app.post("/api/twilio/gather")
async def twilio_gather(request: Request, room: str = Query(default="")):
    from .telephony import twiml_gather

    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    speech = str(form.get("SpeechResult") or form.get("UnstableSpeechResult") or "")
    xml = twiml_gather(call_sid, speech, room)
    return Response(content=xml, media_type="application/xml")


@app.post("/api/twilio/status")
async def twilio_status(request: Request):
    from .telephony import finalize_call
    from .world import post as room_post

    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    status = str(form.get("CallStatus") or "completed")
    result = finalize_call(call_sid, status)
    sess = (result.get("session") or {}) if result.get("ok") else {}
    room_id = sess.get("room_id") or ""
    eng = get_engine()
    if room_id and eng.store.get_room(room_id):
        outcome = result.get("outcome") or {}
        structured = result.get("structured") or sess.get("structured") or {}
        room_post(
            eng,
            room_id,
            author="outreach_caller",
            author_kind="agent",
            kind="artifact",
            text=f"Call {status}. {outcome.get('label', 'Transcript ready')}.",
            artifact_type="call_transcript",
            artifact={
                "call_sid": call_sid,
                "status": status,
                "transcript": sess.get("transcript") or [],
                "outcome": outcome,
            },
        )
        if structured:
            room_post(
                eng,
                room_id,
                author="customer_voice_agent",
                author_kind="agent",
                kind="artifact",
                text=(
                    f"Structured evidence · {structured.get('reason')} · "
                    f"intent={structured.get('purchase_intent')} · "
                    f"friction={structured.get('friction')}"
                ),
                artifact_type="call_evidence",
                artifact={"structured": structured, "transcript": sess.get("transcript") or []},
            )
    return {"ok": True}


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
def memory(q: str = "", type: str | None = None):
    eng = get_engine()
    by_kind: dict[str, list] = {"customer": [], "product": [], "engineering": [], "organizational": []}
    items = eng.store.list_memory(type) if type else eng.store.list_memory()
    if q:
        ql = q.lower()
        items = [
            i
            for i in items
            if ql in str(i.get("title", "")).lower()
            or ql in str(i.get("body", "")).lower()
            or ql in str(i.get("statement", "")).lower()
            or ql in str(i.get("text", "")).lower()
        ]
    for item in items:
        kind = item.get("kind") or item.get("type") or "organizational"
        by_kind.setdefault(kind, []).append(item)
    return {"memory": by_kind, "lessons": [lesson.model_dump(mode="json") for lesson in eng.store.list_lessons()]}


@app.post("/api/memory")
def memory_remember(body: MemoryInBody):
    valid = {"customer", "product", "engineering", "organizational"}
    if body.type not in valid:
        raise HTTPException(400, f"type must be one of {sorted(valid)}")
    eng = get_engine()
    mid = f"mem-{abs(hash(body.title + body.body)) % 10_000_000}"
    payload = {
        "id": mid,
        "type": body.type,
        "kind": body.type,
        "title": body.title,
        "body": body.body,
        "tags": body.tags,
        "room_id": body.room_id,
    }
    eng.store.put_memory(mid, body.type, payload)
    return payload


@app.get("/api/scenarios")
def scenarios():
    rows = list(get_engine().seed_world().get("scenarios") or [])
    if not any(str(r.get("id")) == "checkout_abandon" for r in rows):
        rows.append(
            {
                "id": "checkout_abandon",
                "title": "Checkout abandon → call",
                "kind": "research",
                "loop_type": "type_a",
                "path": "bug",
                "recipe": True,
                "note": "Example ResearchEvent recipe on /api/research infra",
            }
        )
    return {"scenarios": rows}


@app.get("/api/traces")
def traces():
    eng = get_engine()
    calls = []
    for inv in eng.store.list_investigations():
        calls.extend(c.model_dump(mode="json") for c in eng.store.list_agent_calls(inv.id))
    return {"traces": calls, "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()]}


@app.get("/api/traces/{trace_id}")
def trace_detail(trace_id: str):
    eng = get_engine()
    inv = eng.store.get_investigation(trace_id)
    if inv:
        return {
            "id": trace_id,
            "investigation": inv.model_dump(mode="json"),
            "agent_calls": [c.model_dump(mode="json") for c in eng.store.list_agent_calls(trace_id)],
            "timeline": [t.model_dump(mode="json") for t in eng.store.list_timeline(trace_id)],
        }
    # Live graph trace ids are ephemeral UUIDs buffered on the Hub.
    buffered = []
    for events in HUB.buffer.values():
        for ev in events:
            if ev.get("type") == "trace" and ev.get("traceId") == trace_id:
                buffered.append(ev.get("step"))
    if not buffered:
        raise HTTPException(404, "trace not found")
    return {"id": trace_id, "steps": buffered}


@app.get("/api/signals")
def signals():
    return {"signals": [s.model_dump(mode="json") for s in get_engine().store.list_signals()]}


@app.post("/api/signals")
def post_signal(body: SignalInBody):
    """v2-style: ingest a signal → open/join a room → run the live fleet graph."""
    from .agents.graphs import run_live_graph
    from .adk_runtime import dispatch_signal
    from .engine import _id, _now
    from .models import LoopType, Room, RoomKind

    eng = get_engine()
    eng.seed_world()
    fork = (body.fork or ("FEATURE" if body.polarity == "positive" else "BUG")).upper()
    kind = RoomKind.OPPORTUNITY if fork == "FEATURE" else RoomKind.INCIDENT
    title = body.title or f"{body.metric} ({body.polarity})"
    # Prefer an open room for the same metric/scenario when present.
    room = None
    if body.scenario:
        room = next((r for r in eng.store.list_rooms() if r.scenario_id == body.scenario), None)
    if room is None:
        room = Room(
            id=_id("room"),
            kind=kind,
            title=title,
            topic=f"{body.source} · {body.domain} · {body.metric}",
            members=["orchestrator", "signal_agent", "investigator_agent", "risk_agent"],
            status="open",
            created_at=_now(),
            last_message_at=_now(),
            loop_type=LoopType.TYPE_B if fork == "FEATURE" else LoopType.TYPE_A,
            scenario_id=body.scenario,
        )
        eng.store.put_room(room)
    sig = {
        "source": body.source,
        "polarity": body.polarity,
        "domain": body.domain,
        "metric": body.metric,
        "delta": body.delta,
        "dimensions": body.dimensions,
        "fork": fork,
        "scenario": body.scenario,
        "title": title,
    }
    try:
        from .connectors.warehouse import publish_signal

        publish_signal({**sig, "room_id": room.id, "path": "api.signals"})
    except Exception:
        pass
    result = dispatch_signal(
        eng,
        room.id,
        sig,
        fork=fork,
        probe_exfil=body.scenario in {"security_exfil", "pii-exfil-deny"},
    )
    return {
        "signalId": f"sig-{result['trace_id'][:8]}",
        "roomId": room.id,
        "room_id": room.id,
        "trace_id": result["trace_id"],
        "fork": result["fork"],
        "pipeline": result.get("pipeline"),
        "steps": result.get("steps"),
    }


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
def decide(action_id: str, body: ApproveBody, authorization: str | None = Header(default=None)):
    from .audit import record

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
        record(
            eng.store,
            actor=body.approver,
            action="approval.approve",
            resource=f"action:{action_id}",
            detail={"rationale": body.rationale, "execution": execution},
        )
        return {
            "approval": "approve",
            "outcome": outcome.model_dump(mode="json"),
            "execution": execution,
            "pr_url": execution.get("pr_url"),
            **_bundle(eng, action.investigation_id),
        }
    approval = eng.approve(action_id, body.approver, "deny", body.rationale)
    record(
        eng.store,
        actor=body.approver,
        action="approval.deny",
        resource=f"action:{action_id}",
        detail={"rationale": body.rationale},
    )
    return {"approval": approval.model_dump(mode="json"), **_bundle(eng, action.investigation_id)}


@app.get("/api/jobs")
def list_jobs(
    authorization: str | None = Header(default=None),
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
):
    from .auth import require_admin

    require_admin(authorization)
    eng = get_engine()
    rows = eng.store.list_jobs(status=status, kind=kind)
    return {"jobs": [j.model_dump(mode="json") for j in rows]}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str, authorization: str | None = Header(default=None)):
    from .auth import require_admin

    require_admin(authorization)
    job = get_engine().store.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {"job": job.model_dump(mode="json")}


@app.post("/api/internal/worker/run/{job_id}")
def worker_run_job(
    job_id: str,
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
):
    from .auth import require_admin_or_internal
    from .jobs import process_job

    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    eng = get_engine()
    result = process_job(eng.store, eng, job_id)
    if not result:
        raise HTTPException(404, "job not found or not runnable")
    return {"result": result}


@app.post("/api/internal/worker/tick")
def worker_tick(
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
    limit: int = Query(default=3, ge=1, le=10),
):
    from .auth import require_admin_or_internal
    from .jobs import process_one

    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    eng = get_engine()
    processed: list[dict] = []
    for _ in range(limit):
        result = process_one(eng.store, eng)
        if not result:
            break
        processed.append(result)
    return {"processed": processed, "count": len(processed)}


@app.get("/api/approvals/{action_id}/status")
def approval_execution_status(action_id: str):
    """Console polling — job + execution without admin bearer."""
    eng = get_engine()
    action = eng.store.get_action(action_id)
    if not action:
        raise HTTPException(404, "action not found")
    execution = dict((action.artifacts or {}).get("execution") or {})
    job_id = execution.get("job_id")
    job = eng.store.get_job(str(job_id)) if job_id else None
    pr_url = execution.get("pr_url") or execution.get("code_pr_url")
    return {
        "action_id": action_id,
        "status": action.status,
        "execution": execution,
        "job": job.model_dump(mode="json") if job else None,
        "pr_url": pr_url,
    }


@app.get("/api/audit")
def audit_log(authorization: str | None = Header(default=None), limit: int = Query(default=100, ge=1, le=500)):
    from .auth import require_admin

    require_admin(authorization)
    rows = get_engine().store.list_audit(limit=limit)
    return {"events": [e.model_dump(mode="json") for e in rows]}


@app.post("/api/scenarios/{slug}/run")
def scenario_run(slug: str, request: Request):
    """Eval fixture runner — live fleet walk into the scenario room."""
    from .agents.graphs import run_live_graph

    eng = get_engine()
    eng.seed_world()

    if slug in {"checkout_abandon", "abandon", "checkout-abandon"}:
        from .abandon_research import run_abandon_research

        q = request.query_params
        out = run_abandon_research(
            eng,
            user_id=q.get("user_id") or "8472",
            phone=q.get("phone") or "",
            place_real_call=q.get("call") == "1",
        )
        room = eng.store.get_room(out["room_id"])
        return {
            **out,
            "room": room.model_dump(mode="json") if room else None,
            "funnel": funnel_for("type_a", "HYPOTHESIS", awaiting=False),
            "pipeline": ["investigate", "brief", "memory", "call", "structured_evidence"],
            "presence": HUB.agents_in(out["room_id"]) if out.get("room_id") else [],
        }

    room = next((r for r in eng.store.list_rooms() if r.scenario_id == slug), None)
    if not room:
        raise HTTPException(404, f"unknown scenario {slug}")
    for mid in room.members:
        HUB.set_presence(room.id, mid, "idle", {"label": mid, "hue": abs(hash(mid)) % 360})
    lt = room.loop_type.value if hasattr(room.loop_type, "value") else str(room.loop_type or "")
    fork = "FEATURE" if lt.lower() in {"type_b", "b", "feature"} else "BUG"
    signal = {
        "scenario": slug,
        "metric": slug,
        "source": "fixture",
        "polarity": "positive" if fork == "FEATURE" else "negative",
        "domain": "technical",
        "delta": -0.18 if fork == "BUG" else 0.12,
        "dimensions": {"flow": slug, "hypothesis": room.topic},
        "fork": fork,
        "title": room.title,
    }
    result = run_live_graph(
        eng,
        room.id,
        signal,
        fork=fork,
        probe_exfil=slug in {"security_exfil", "pii-exfil-deny"},
    )
    return {
        "scenario": slug,
        "room_id": room.id,
        "room": room.model_dump(mode="json"),
        "funnel": funnel_for(room.loop_type, None),
        "pipeline": result.get("pipeline"),
        "trace_id": result.get("trace_id"),
        "steps": result.get("steps"),
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
