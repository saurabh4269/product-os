"""FastAPI control plane for the console."""

from __future__ import annotations

import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import (
    BackgroundTasks,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from .auth import AdminUnlessEval, cors_allowlist
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
    import asyncio

    cfg = settings()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    from loop.state_persist import hydrate_db

    hydrate_db(cfg.db_path())
    from loop.runtime_mode import is_eval_mode, use_file_warehouse

    if use_file_warehouse() and not (cfg.warehouse_path() / "meta.json").exists():
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
        from generate import main as gen

        gen(cfg.warehouse_path())
    eng = get_engine()
    from loop.flags_persist import hydrate_flags

    hydrate_flags(eng.store)
    from .tenant import hydrate_all_tenants, seed_placeholder

    hydrate_all_tenants(eng.store)
    if not eng.store.list_rooms():
        eng.seed_world()
    elif is_eval_mode() and not eng.store.list_investigations():
        eng.run_until_approval()
    seed_placeholder(eng.store)

    try:
        from loop import firestore_memory

        firestore_memory.warm_client()
        firestore_memory.backfill_from_store(eng.store)
    except Exception:
        pass

    if os.environ.get("LOOP_SIGNAL_WATCH", "1") == "1":
        from .signal_watch import start_signal_watch

        start_signal_watch(eng)

    tick_task = None
    if os.environ.get("LOOP_INLINE_WORKER") == "1":

        async def _worker_loop() -> None:
            from .jobs import process_one

            interval = max(5, int(os.environ.get("LOOP_WORKER_INTERVAL", "30")))
            while True:
                await asyncio.sleep(interval)
                try:
                    detected = eng.detect_all_signals()
                    investigated: list[dict] = []
                    if os.environ.get("LOOP_AUTO_INVESTIGATE", "1") == "1":
                        from .auto_investigate import (
                            auto_investigate_new_signals,
                            count_applied,
                            open_signal_ids_for_auto_investigate,
                        )

                        open_ids = open_signal_ids_for_auto_investigate(eng, detected)
                        if open_ids:
                            investigated = auto_investigate_new_signals(eng, open_ids)
                    processed: list[dict] = []
                    limit = max(1, int(os.environ.get("LOOP_WORKER_JOB_BATCH", "3")))
                    for _ in range(limit):
                        result = process_one(eng.store, eng)
                        if not result:
                            break
                        processed.append(result)
                    from .worker_heartbeat import record_tick

                    record_tick(
                        {
                            "processed": processed,
                            "count": len(processed),
                            "detected": len(detected),
                            "investigated": investigated,
                            "auto_investigated": count_applied(investigated),
                        }
                    )
                except Exception:
                    pass

        tick_task = asyncio.create_task(_worker_loop())

    yield

    if tick_task:
        tick_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tick_task


_cors_origins, _cors_credentials = cors_allowlist()
app = FastAPI(title="LOOP", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveBody(BaseModel):
    approver: str = "oncall@northstar"
    decision: Literal["approve", "deny"]
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
    flag_names: list[str] = Field(default_factory=list)
    code_paths: list[str] = Field(default_factory=list)
    flag_file_path: str = "config/flags.json"
    stack: str = ""
    test_command: str = ""
    default_surface: str = "product"
    metric_catalog: list[str] = Field(default_factory=list)
    bq_project: str = ""
    bq_raw_dataset: str = ""
    bq_metrics_dataset: str = ""
    ga4_property_id: str = ""
    ga4_dataset: str = ""
    ads_dataset: str = ""
    ads_customer_id: str = ""
    warehouse_mode: str = "auto"
    primary_metric: str = "purchase_conversion"
    funnel_events: list[str] = Field(default_factory=list)


class TokenRotateBody(BaseModel):
    token: str


class OnboardBody(BaseModel):
    """Wire a GCP Cloud Run Product Y to Product OS (mint token + push env)."""

    cloud_run_service: str = ""
    repo: str
    region: str = ""
    project: str = ""
    tenant_id: str = ""
    name: str = ""
    product: str = ""
    deploy_url: str = ""
    wire: bool = True


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
    email: str = ""
    sentiment: str = ""
    meta: dict = Field(default_factory=dict)


class RegisterUserBody(BaseModel):
    """Product Y registration — email required for mail-first outreach."""

    tokenized_user: str
    email: str
    phone: str = ""
    consent_email: bool = True
    consent_voice: bool = True
    meta: dict = Field(default_factory=dict)


class PlaceCallBody(BaseModel):
    to_number: str = ""
    reason: str = "checkout issue"
    room_id: str = ""
    product: str = ""
    tokenized_user: str = "tok_anon"
    force: bool = False  # human override of mail-first gate
    purpose: str = ""  # feedback_ask | fix_notify


class AdvanceOutreachBody(BaseModel):
    room_id: str
    force_call: bool = False
    fix_summary: str = ""


class MailReplyBody(BaseModel):
    tokenized_user: str
    text: str = ""
    solved: bool = False
    investigation_id: str = ""
    room_id: str = ""


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


def _status_payload(eng) -> dict:
    """Shared counters for GET /api/status and WebSocket initial_state."""
    from .connectors import google_oauth
    from .workflow import workflow_from_store

    from .room_ui import visible_pending_approvals

    rooms = eng.store.list_rooms()
    pending = visible_pending_approvals(eng.store)
    presence_n = sum(len(v) for v in HUB.presence.values())
    open_rooms = [r for r in rooms if r.status == "open"]
    by_kind: dict[str, int] = {}
    for r in rooms:
        k = r.kind.value if hasattr(r.kind, "value") else str(r.kind)
        by_kind[k] = by_kind.get(k, 0) + 1
    stages: dict[str, int] = {}
    for _rid, agents in HUB.presence.items():
        for ev in agents.values():
            st = str(ev.get("status") or "idle")
            stages[st] = stages.get(st, 0) + 1
    engaged = 0
    verified = 0
    for room in open_rooms:
        inv = eng.store.get_investigation(room.investigation_id) if room.investigation_id else None
        funnel = workflow_from_store(eng.store, room, inv)
        st = funnel.get("current") or "signal"
        if st in {"investigate", "evidence", "root_cause", "customer", "product"}:
            engaged += 1
        if inv and str(getattr(inv.state, "value", inv.state)) in {
            "resolved",
            "partially_resolved",
        }:
            verified += 1
    oauth = google_oauth.status()
    from loop import firestore_memory, gcs_state
    from loop.signal_watch import last_tick_summary
    from loop.state_persist import last_upload_ts
    from loop.worker_heartbeat import last_tick as worker_last_tick

    jobs_queued = len(eng.store.list_jobs(status="queued"))
    jobs_dead = len(eng.store.list_jobs(status="dead"))
    last_tick = last_tick_summary()
    worker_tick = worker_last_tick()

    return {
        "ok": True,
        "running": True,
        "rooms": {"total": len(rooms), "open": len(open_rooms), "by_kind": by_kind},
        "approvals_pending": len(pending),
        "engaged": engaged,
        "verified": verified,
        "presence": {"agents": presence_n, "by_status": stages},
        "funnel": {
            "signal": by_kind.get("incident", 0) + by_kind.get("opportunity", 0),
            "approve": len(pending),
            "learn": len(eng.store.list_lessons()),
        },
        "workspace": {"connected": bool(oauth.get("connected")), "email": oauth.get("email") or ""},
        "memory": firestore_memory.status(),
        "worker": {
            "inline": os.environ.get("LOOP_INLINE_WORKER") == "1",
            "tasks_disabled": os.environ.get("LOOP_TASKS_DISABLE") == "1",
            "last_signal_tick": last_tick.get("at"),
            "last_worker_tick": worker_tick.get("at"),
            "auto_investigated": max(
                int(last_tick.get("auto_investigated", 0) or 0),
                int(worker_tick.get("auto_investigated", 0) or 0),
            ),
            "jobs_queued": jobs_queued,
            "jobs_dead": jobs_dead,
            "state_upload_ts": last_upload_ts(),
            "last_tick_detected": worker_tick.get("detected"),
            "last_tick_processed": worker_tick.get("count"),
        },
        "gcs": {"last_error": gcs_state.last_error() or None},
        "auth": {
            "admin_required": __import__("loop.auth", fromlist=["admin_required"]).admin_required(),
            "eval_open": __import__("loop.auth", fromlist=["eval_mode_open"]).eval_mode_open(),
        },
        "patterns": ["parallel_fanout", "review_critique", "skip_if_done", "agent_callback"],
    }


@app.get("/api/status")
def status(_actor: AdminUnlessEval):
    """Live dashboard — funnel counts, presence, gates (not a CRUD board)."""
    return _status_payload(get_engine())


def _visible_flags(eng, tenant_id: str) -> dict[str, str]:
    raw = eng.store.list_flags()
    return {k.split(":", 2)[-1]: v for k, v in raw.items() if k.startswith(f"t:{tenant_id}:")}


def _public_tenant(t) -> dict:
    d = t.model_dump()
    d.pop("token_hash", None)
    d["has_token"] = bool(t.token_hash)
    return d


def _connect_tenants(store) -> list:
    """Hide duplicate tenant rows that share the same product repo (e.g. acme vs cove)."""
    from .tenant import hydrate_tenant_config

    rows = [hydrate_tenant_config(t, store) for t in store.list_tenants()]
    canonical = (os.environ.get("LOOP_TENANT_ID") or "acme").strip() or "acme"
    by_repo: dict[str, list] = {}
    for t in rows:
        repo = (t.repo or "").strip()
        if repo:
            by_repo.setdefault(repo, []).append(t)
    hidden: set[str] = set()
    for group in by_repo.values():
        if len(group) < 2:
            continue
        keep = next((t for t in group if t.id == canonical), group[0])
        for t in group:
            if t.id != keep.id:
                hidden.add(t.id)
    return [t for t in rows if t.id not in hidden]


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


def _gate(eng, tenant_id: str | None = None) -> dict:
    from .tenant import resolve_tenant, seed_placeholder

    seed_placeholder(eng.store)
    t = resolve_tenant(eng.store, tenant_id=tenant_id)
    if not t:
        tenants = eng.store.list_tenants()
        t = next((x for x in tenants if x.repo), None)
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
    from .tenant import resolve_tenant
    from .tenant_context import effective_action_artifacts, github_pr_eligible

    inv = eng.store.get_investigation(action.investigation_id)
    t = resolve_tenant(eng.store, investigation=inv)
    repo = (t.repo if t else "") or ""
    arts = effective_action_artifacts(eng.store, action, inv=inv, tenant=t)
    if github_pr_eligible(arts, t):
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
    arts = row.get("artifacts") if isinstance(row.get("artifacts"), dict) else {}
    exe = arts.get("execution") if isinstance(arts.get("execution"), dict) else {}
    compact_exe = {
        k: exe[k]
        for k in ("pr_url", "pr_opened", "code_pr_url", "code_fix", "flag", "value", "status", "proof")
        if k in exe
    }
    keep_arts = {k: arts[k] for k in ("flag", "to", "from", "code_fix", "github_pr") if k in arts}
    if compact_exe:
        keep_arts["execution"] = compact_exe
    brief = arts.get("code_brief") if isinstance(arts.get("code_brief"), dict) else None
    if brief and brief.get("issue"):
        keep_arts["code_brief"] = {"issue": brief.get("issue")}
    row["artifacts"] = keep_arts
    gate = _action_gate(eng, action)
    row["gate"] = gate["label"]
    row["gate_mode"] = gate["mode"]
    row["tenant_repo"] = gate["tenant_repo"]
    return row


@app.get("/api/tenants")
def tenants(authorization: str | None = Header(default=None)):
    from .auth import require_admin
    from .tenant import seed_placeholder

    require_admin(authorization, actor="tenant.list")
    eng = get_engine()
    seed_placeholder(eng.store)
    return {"tenants": [_public_tenant(t) for t in _connect_tenants(eng.store)], "gate": _gate(eng)}


@app.post("/api/tenants")
def upsert_tenant(_actor: AdminUnlessEval, body: TenantBody):
    from .audit import record

    actor = f"tenant:{body.id}"
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
        flag_names=body.flag_names or (prev.flag_names if prev else []),
        code_paths=body.code_paths or (prev.code_paths if prev else []),
        flag_file_path=body.flag_file_path or (prev.flag_file_path if prev else "config/flags.json"),
        stack=body.stack or (prev.stack if prev else ""),
        test_command=body.test_command or (prev.test_command if prev else ""),
        default_surface=body.default_surface or (prev.default_surface if prev else "product"),
        metric_catalog=body.metric_catalog or (prev.metric_catalog if prev else []),
        bq_project=body.bq_project or (prev.bq_project if prev else ""),
        bq_raw_dataset=body.bq_raw_dataset or (prev.bq_raw_dataset if prev else ""),
        bq_metrics_dataset=body.bq_metrics_dataset or (prev.bq_metrics_dataset if prev else ""),
        ga4_property_id=body.ga4_property_id or (prev.ga4_property_id if prev else ""),
        ga4_dataset=body.ga4_dataset or (prev.ga4_dataset if prev else ""),
        ads_dataset=body.ads_dataset or (prev.ads_dataset if prev else ""),
        ads_customer_id=body.ads_customer_id or (prev.ads_customer_id if prev else ""),
        warehouse_mode=body.warehouse_mode or (prev.warehouse_mode if prev else "auto"),
        primary_metric=body.primary_metric or (prev.primary_metric if prev else "purchase_conversion"),
        funnel_events=body.funnel_events or (prev.funnel_events if prev else []),
    )
    from .tenant import hydrate_tenant_config

    t = hydrate_tenant_config(t, eng.store)
    eng.store.put_tenant(t)
    from .tenant import bind_fixture_tenants

    bind_fixture_tenants(eng.store)
    record(eng.store, actor=actor, action="tenant.upsert", resource=f"tenant:{t.id}", detail={"repo": t.repo})
    return {"tenant": _public_tenant(t)}


@app.post("/api/tenants/{tenant_id}/token")
def rotate_token(tenant_id: str, body: TokenRotateBody, authorization: str | None = Header(default=None)):
    from .audit import record
    from .auth import require_admin

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


@app.post("/api/admin/verify")
def admin_verify(authorization: str | None = Header(default=None)):
    """Validate admin bearer — console stores in sessionStorage, not build-time env."""
    from .auth import require_admin

    actor = require_admin(authorization)
    return {"ok": True, "actor": actor}


@app.get("/api/tenants/{tenant_id}")
def tenant_detail(tenant_id: str, authorization: str | None = Header(default=None)):
    from .auth import require_admin_or_tenant

    eng = get_engine()
    require_admin_or_tenant(authorization, tenant_id=tenant_id, store=eng.store)
    t = eng.store.get_tenant(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    return {"tenant": _public_tenant(t), "flags": _visible_flags(eng, tenant_id), "gate": _gate(eng, tenant_id)}


@app.get("/api/onboard/services")
def onboard_services(
    project: str = "",
    region: str = "",
    authorization: str | None = Header(default=None),
):
    """List Cloud Run services in the project for the Connect picker."""
    from .auth import require_admin
    from .onboard import list_cloud_run_services

    require_admin(authorization, actor="onboard.list")
    return list_cloud_run_services(project=project, region=region)


@app.post("/api/tenants/onboard")
def tenants_onboard(body: OnboardBody, authorization: str | None = Header(default=None)):
    """Create tenant + mint token + push LOOP_* env to Cloud Run (production wire)."""
    from .audit import record
    from .auth import require_admin
    from .onboard import onboard_tenant
    from .tenant import bind_fixture_tenants

    actor = require_admin(authorization, actor="onboard.wire")
    if not body.repo.strip():
        raise HTTPException(400, "repo required")
    if not body.cloud_run_service.strip() and not body.deploy_url.strip():
        raise HTTPException(400, "cloud_run_service or deploy_url required")
    eng = get_engine()
    out = onboard_tenant(
        eng.store,
        cloud_run_service=body.cloud_run_service,
        repo=body.repo,
        region=body.region,
        project=body.project,
        tenant_id=body.tenant_id,
        name=body.name,
        product=body.product,
        deploy_url=body.deploy_url,
        wire=body.wire,
    )
    if out.get("status") == "skipped" and out.get("detail"):
        raise HTTPException(400, str(out["detail"]))
    bind_fixture_tenants(eng.store)
    tid = out.get("tenant_id") or ""
    record(
        eng.store,
        actor=actor,
        action="tenant.onboard",
        resource=f"tenant:{tid}",
        detail={"repo": body.repo, "service": body.cloud_run_service, "wire": out.get("wire", {}).get("status")},
    )
    return out


@app.post("/api/tenants/{tenant_id}/onboard")
def tenant_onboard(tenant_id: str, body: OnboardBody, authorization: str | None = Header(default=None)):
    """Same as POST /api/tenants/onboard with tenant_id fixed in the path."""
    body.tenant_id = tenant_id
    return tenants_onboard(body, authorization)


@app.post("/api/tenants/{tenant_id}/verify")
def tenant_verify(tenant_id: str, authorization: str | None = Header(default=None)):
    """Run the e2e checklist (flags, ingest, GitHub readiness)."""
    from .audit import record
    from .auth import require_admin
    from .onboard import verify_tenant

    actor = require_admin(authorization, actor=f"onboard.verify:{tenant_id}")
    eng = get_engine()
    if not eng.store.get_tenant(tenant_id):
        raise HTTPException(404, "tenant not found")
    out = verify_tenant(eng, tenant_id)
    record(eng.store, actor=actor, action="tenant.verify", resource=f"tenant:{tenant_id}", detail={"ok": out.get("ok")})
    return out


@app.get("/api/tenants/{tenant_id}/incident-lifecycle")
def tenant_incident_lifecycle(
    tenant_id: str,
    authorization: str | None = Header(default=None),
    metric: str = Query(default="checkout_conversion"),
):
    """Poll checkout-regression progress for Connect walkthrough (Cove → room → approve → verify)."""
    from .auth import require_admin_or_tenant

    eng = get_engine()
    if not eng.store.get_tenant(tenant_id):
        raise HTTPException(404, "tenant not found")
    require_admin_or_tenant(authorization, tenant_id=tenant_id, store=eng.store, actor="lifecycle")
    from .incident_lifecycle import incident_lifecycle

    return incident_lifecycle(eng, tenant_id, metric=metric)


@app.post("/api/tenants/{tenant_id}/incident-lifecycle/arm")
def tenant_incident_arm(tenant_id: str, authorization: str | None = Header(default=None)):
    """Admin reset — re-enable pay-sdk 4.3 on Product Y for another checkout repro."""
    from .audit import record
    from .auth import require_admin
    from .incident_lifecycle import arm_checkout_regression

    actor = require_admin(authorization, actor=f"incident.arm:{tenant_id}")
    eng = get_engine()
    if not eng.store.get_tenant(tenant_id):
        raise HTTPException(404, "tenant not found")
    out = arm_checkout_regression(eng, tenant_id)
    record(
        eng.store,
        actor=actor,
        action="incident.arm",
        resource=f"tenant:{tenant_id}",
        detail={"flag": out.get("flag"), "value": out.get("value")},
    )
    from .incident_lifecycle import incident_lifecycle, publish_incident_lifecycle

    lifecycle = publish_incident_lifecycle(eng, tenant_id) or incident_lifecycle(eng, tenant_id)
    return {**out, "lifecycle": lifecycle}


@app.get("/api/t/{tenant_id}/flags")
def tenant_flags(tenant_id: str, authorization: str | None = Header(default=None)):
    _require_tenant(tenant_id, authorization)
    return {"tenant": tenant_id, "flags": _visible_flags(get_engine(), tenant_id)}


@app.post("/api/t/{tenant_id}/signals")
def tenant_signal(tenant_id: str, body: IngestSignalBody, authorization: str | None = Header(default=None)):
    from .auth import ingest_async_default
    from .world import ingest_tenant_signal

    t = _require_tenant(tenant_id, authorization)
    eng = get_engine()
    out = ingest_tenant_signal(
        eng,
        t,
        metric=body.metric,
        magnitude=body.magnitude,
        baseline=body.baseline,
        note=body.note,
        source=body.source,
        async_finish=ingest_async_default(),
    )
    inv_id = out.get("investigation_id")
    if out.get("async") and inv_id:
        inv = eng.store.get_investigation(inv_id)
        if inv and not eng.store.list_hypotheses(inv.id):
            from .auto_investigate import finish_stalled_investigation

            finish_stalled_investigation(eng, inv)
            out["async_finished"] = True
    return _ingest_response(out)


@app.post("/api/loop/ingest")
def loop_ingest(body: IngestSignalBody, authorization: str | None = Header(default=None)):
    """Tenant wire — Cove checkout hang posts here with tenant bearer (LOOP_TENANT_TOKEN)."""
    from .auth import ingest_async_default
    from .tenant import resolve_tenant_by_token
    from .world import ingest_tenant_signal

    eng = get_engine()
    token = _bearer(authorization)
    tenant = resolve_tenant_by_token(eng.store, token)
    if not tenant:
        raise HTTPException(401, "tenant bearer token required")
    note = body.note or "Checkout authorization hung at Pay now"
    source = body.source if body.source != "tenant.ingest" else "cove.checkout"
    out = ingest_tenant_signal(
        eng,
        tenant,
        metric=body.metric if body.metric != "purchase_conversion" else "checkout_conversion",
        magnitude=body.magnitude,
        baseline=body.baseline,
        note=note,
        source=source,
        async_finish=ingest_async_default(),
    )
    inv_id = out.get("investigation_id")
    if out.get("async") and inv_id:
        inv = eng.store.get_investigation(inv_id)
        if inv and not eng.store.list_hypotheses(inv.id):
            from .auto_investigate import finish_stalled_investigation

            finish_stalled_investigation(eng, inv)
            out["async_finished"] = True
    return _ingest_response(out)


def _ingest_response(out: dict) -> dict:
    inv_id = out.get("investigation_id")
    sig = out.get("signal")
    return {
        "signal": sig.model_dump(mode="json") if sig is not None else None,
        "room_id": out.get("room_id"),
        "joined": out.get("joined", False),
        "investigation_id": inv_id,
        "async": out.get("async", False),
        "async_finished": out.get("async_finished", False),
    }


@app.get("/api/oauth/google")
def google_oauth_status(request: Request, _actor: AdminUnlessEval):
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
    ok, detail, mode = google_oauth.exchange_code(code, state, _request_base(request))
    if mode == "ga4":
        return RedirectResponse(google_oauth.ga4_console_return(ok, "" if ok else detail), status_code=302)
    return RedirectResponse(google_oauth.console_return(ok, "" if ok else detail), status_code=302)


@app.get("/api/oauth/ga4/start")
def google_oauth_ga4_start(request: Request):
    from .connectors import google_oauth

    url = google_oauth.ga4_authorization_url(_request_base(request))
    if not url:
        return RedirectResponse(
            google_oauth.ga4_console_return(False, "Paste OAuth client on Connect first"),
            status_code=302,
        )
    return RedirectResponse(url, status_code=302)


@app.get("/api/oauth/ga4/status")
def google_oauth_ga4_status():
    from .connectors import google_oauth

    return {"ready": google_oauth.ga4_adc_ready()}


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
    email = body.email or str((body.meta or {}).get("email") or "")
    out = ingest_tenant_voice(
        get_engine(),
        t,
        text=body.text,
        tokenized_user=body.tokenized_user,
        phone=phone,
        email=email,
    )
    return {
        "voice": out["voice"],
        "room_id": out["room_id"],
        "joined": out["joined"],
        "classification": out.get("classification"),
        "identity": out.get("identity"),
    }


@app.post("/api/t/{tenant_id}/users")
def tenant_register_user(
    tenant_id: str,
    body: RegisterUserBody,
    authorization: str | None = Header(default=None),
):
    """Product Y registration webhook — store email (+ optional phone) for mail-first outreach."""
    from .customer_contact import upsert_registration

    t = _require_tenant(tenant_id, authorization)
    if not body.email or "@" not in body.email:
        raise HTTPException(400, "email required at registration")
    identity = upsert_registration(
        get_engine().store,
        tokenized_user=body.tokenized_user,
        tenant_id=t.id,
        email=body.email,
        phone=body.phone,
        consent_email=body.consent_email,
        consent_voice=body.consent_voice,
        meta=body.meta,
    )
    return {"ok": True, "identity": identity}


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
def research_event(body: ResearchEventBody, _actor: AdminUnlessEval):
    """Generic event → probes → brief → call → structured evidence (recipe-agnostic)."""
    from .adk_runtime import adk_inline_enabled, run_adk_research
    from .customer_research import ResearchEvent, run_customer_research
    from .models import LoopType, PathKind, RoomKind

    eng = get_engine()
    from loop.world import ensure_api_ready

    ensure_api_ready(eng)
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
    # Rooms live in this service's SQLite — do not forward to ADK worker (separate ephemeral DB).
    if adk_inline_enabled():
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
def improve_event(body: ImproveEventBody, _actor: AdminUnlessEval):
    """Type A/B product loop — detect → hypothesize → fix|experiment → measure → learn."""
    from .models import LoopType, PathKind, RoomKind
    from .product_improvement import ProductSignalEvent, run_product_loop

    eng = get_engine()
    from loop.world import ensure_api_ready

    ensure_api_ready(eng)
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
def coordinate(body: CoordinateBody, _actor: AdminUnlessEval):
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
            apply_calendar=body.apply_calendar,
        )
        _publish_coordination_payoff(out, body.room_id)
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
    out = run_coordination(eng, req, apply_calendar=body.apply_calendar)
    _publish_coordination_payoff(out, body.room_id)
    return out


def _publish_coordination_payoff(out: dict, room_id: str | None) -> None:
    coord = out.get("coordination") or {}
    slot = coord.get("slot") if isinstance(coord, dict) else None
    if not isinstance(slot, dict) or not slot.get("start"):
        return
    HUB.publish_global(
        {
            "type": "payoff",
            "kind": "calendar_scheduled",
            "room_id": room_id or coord.get("room_id"),
            "event_url": slot.get("event_url"),
            "start": slot.get("start"),
        }
    )


@app.get("/api/signals/catalog")
def signals_catalog():
    from .investigation import catalog

    return catalog()


@app.post("/api/investigate")
def investigate(body: InvestigateBody, _actor: AdminUnlessEval):
    """Parallel investigation workflow — not 'conversion dropped' alone."""
    from .investigation import AnomalyEvent, run_investigation

    eng = get_engine()
    from loop.world import ensure_api_ready

    ensure_api_ready(eng)
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
    from loop.world import ensure_api_ready

    ensure_api_ready(eng)
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
    """Outbound call — mail-first gate: only non-responders (or human force)."""
    from .connectors.voice import place_call
    from .customer_contact import resolve_callback_phone
    from .outreach import call_brief_for_outreach, gate_place_call
    from .tenant import product_for_room
    from .world import post as room_post

    eng = get_engine()
    product = body.product.strip() or product_for_room(eng.store, body.room_id)
    to_number = (body.to_number or "").strip()
    resolved = None

    gate = gate_place_call(
        eng.store,
        room_id=body.room_id,
        tokenized_user=body.tokenized_user,
        force=body.force,
    )
    if not gate.get("allowed"):
        if body.room_id and eng.store.get_room(body.room_id):
            room_post(
                eng,
                body.room_id,
                author="customer_voice_agent",
                author_kind="agent",
                kind="chat",
                text=str(gate.get("detail") or "Mail feedback first — don't spam-call."),
                artifact_type="contact_lookup",
                artifact=gate,
            )
        raise HTTPException(409, gate.get("detail") or "mail_first")

    if not to_number and body.room_id:
        resolved = resolve_callback_phone(eng.store, body.room_id)
        if resolved.get("found") and resolved.get("phone"):
            to_number = str(resolved["phone"])
            if eng.store.get_room(body.room_id):
                room_post(
                    eng,
                    body.room_id,
                    author="customer_voice_agent",
                    author_kind="agent",
                    kind="chat",
                    text=(
                        f"Looked up contact. Callback {to_number}. "
                        f"Calling only because mail wait elapsed / non-responder ({gate.get('reason')})."
                    ),
                    artifact_type="contact_lookup",
                    artifact={**resolved, "gate": gate},
                )
        elif body.room_id and eng.store.get_room(body.room_id):
            room_post(
                eng,
                body.room_id,
                author="customer_voice_agent",
                author_kind="agent",
                kind="chat",
                text="No callback number on file yet. Capture phone at registration or Cove feedback.",
                artifact_type="contact_lookup",
                artifact=resolved or {"found": False},
            )

    purpose = (body.purpose or "").strip() or "feedback_ask"
    brief = call_brief_for_outreach({"purpose": purpose})
    report = place_call(
        body.tokenized_user,
        body.reason,
        to_number=to_number,
        room_id=body.room_id,
        product=product,
        brief=brief,
    )
    if body.room_id and eng.store.get_room(body.room_id):
        from .receipts import call_proof, post_receipt

        art = {
            **report.model_dump(),
            "resolved_from": (resolved or {}).get("source"),
            "purpose": purpose,
            "gate": gate,
            "to_number": to_number or report.model_dump().get("to_number"),
            "title": "Customer call" if purpose == "feedback_ask" else purpose.replace("_", " ").title(),
            "reason": body.reason,
        }
        post_receipt(
            eng,
            body.room_id,
            kind="contacts",
            title=str(art["title"]),
            agent="outreach_caller",
            status="done" if report.status in {"applied", "queued", "simulated"} else "failed",
            detail=report.detail,
            proof=call_proof(art),
            extra=art,
        )
    return {
        "report": report.model_dump(),
        "resolved": resolved,
        "to_number": to_number or None,
        "gate": gate,
        "purpose": purpose,
    }


@app.post("/api/outreach/advance")
def outreach_advance(body: AdvanceOutreachBody):
    """After mail wait: call non-responders (or fix-notify if mail replies already solved it)."""
    from .outreach import advance_outreach

    eng = get_engine()
    if not eng.store.get_room(body.room_id):
        raise HTTPException(404, "room not found")
    return advance_outreach(
        eng,
        room_id=body.room_id,
        force_call=body.force_call,
        fix_summary=body.fix_summary,
    )


@app.post("/api/outreach/mail-reply")
def outreach_mail_reply(body: MailReplyBody):
    """Inbound reply to a feedback email (from Product Y or mail webhook)."""
    from .outreach import record_mail_reply
    from .world import post as room_post

    eng = get_engine()
    row = record_mail_reply(
        eng.store,
        tokenized_user=body.tokenized_user,
        investigation_id=body.investigation_id,
        room_id=body.room_id,
        summary=body.text,
        solved=body.solved,
    )
    if not row:
        raise HTTPException(404, "no outreach email on file for this user")
    rid = body.room_id or row.get("room_id") or ""
    if rid and eng.store.get_room(rid):
        room_post(
            eng,
            rid,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text=f"Mail reply from {body.tokenized_user}: {(body.text or '')[:160]}",
            artifact_type="mail_reply",
            artifact=row,
        )
    return {"ok": True, "outreach": row}


@app.get("/api/rooms/{room_id}/contact")
def room_contact(room_id: str):
    """Email + phone on file for this room (registration / Cove feedback / memory)."""
    from .customer_contact import resolve_customer_contact

    eng = get_engine()
    if not eng.store.get_room(room_id):
        raise HTTPException(404, "room not found")
    return resolve_customer_contact(eng.store, room_id=room_id)


@app.post("/api/twilio/voice")
async def twilio_voice(
    request: Request,
    room: str = Query(default=""),
    reason: str = Query(default="checkout"),
    product: str = Query(default=""),
):
    from .telephony import put_session, twiml_open
    from .tenant import product_for_room

    eng = get_engine()
    resolved = product.strip() or product_for_room(eng.store, room)

    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    if call_sid:
        put_session(
            call_sid,
            {
                "to": str(form.get("To") or ""),
                "room_id": room,
                "reason": reason,
                "product": resolved,
                "status": "in-progress",
                "turns": 0,
                "transcript": [],
            },
        )
    xml = twiml_open(room, reason, resolved)
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
    from .customer_contact import feedback_summary_from_transcript
    from .telephony import finalize_call
    from .world import post as room_post

    form = await request.form()
    call_sid = str(form.get("CallSid") or "")
    status = str(form.get("CallStatus") or "completed")
    # Only summarize when the call is finished.
    if status not in {"completed", "busy", "failed", "no-answer", "canceled"}:
        return {"ok": True, "ignored": status}
    result = finalize_call(call_sid, status)
    sess = (result.get("session") or {}) if result.get("ok") else {}
    room_id = sess.get("room_id") or ""
    eng = get_engine()
    if room_id and eng.store.get_room(room_id):
        outcome = result.get("outcome") or {}
        structured = result.get("structured") or sess.get("structured") or {}
        transcript = sess.get("transcript") or []
        summary = feedback_summary_from_transcript(transcript)
        room_post(
            eng,
            room_id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="chat",
            text=summary,
            artifact_type="call_feedback",
            artifact={
                "call_sid": call_sid,
                "status": status,
                "transcript": transcript,
                "outcome": outcome,
                "to": sess.get("to"),
            },
        )
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
                "transcript": transcript,
                "outcome": outcome,
            },
        )
        if structured:
            reason = structured.get("reason") or "feedback"
            room_post(
                eng,
                room_id,
                author="customer_voice_agent",
                author_kind="agent",
                kind="artifact",
                text=f"Recorded feedback about {reason}. Intent {structured.get('purchase_intent') or 'unknown'}.",
                artifact_type="call_evidence",
                artifact={"structured": structured, "transcript": transcript},
            )
    return {"ok": True}


@app.post("/api/detect")
def detect():
    eng = get_engine()
    signals = eng.detect_all_signals()
    return {"signals": [s.model_dump(mode="json") for s in signals]}


@app.post("/api/loop/run")
def run_until_approval():
    from loop.runtime_mode import require_eval

    require_eval("synthetic Safari regression")
    eng = get_engine()
    inv = eng.run_until_approval()
    return _bundle(eng, inv.id)


@app.post("/api/world/seed")
def world_seed():
    from loop.runtime_mode import require_eval

    require_eval("fixture seed")
    return get_engine().seed_world()


@app.get("/api/rooms")
def rooms(_actor: AdminUnlessEval, tenant_id: str | None = Query(default=None)):
    eng = get_engine()
    items = []
    for room in eng.store.list_rooms():
        if tenant_id and room.tenant_id not in (None, tenant_id):
            continue
        count, preview = eng.store.room_message_summary(room.id)
        items.append(
            {
                **room.model_dump(mode="json"),
                "message_count": count,
                "preview": preview or room.topic,
            }
        )
    return {"rooms": items}


@app.get("/api/rooms/by-scenario/{slug}")
def room_by_scenario(slug: str, _actor: AdminUnlessEval):
    eng = get_engine()
    room = next((r for r in eng.store.list_rooms() if r.scenario_id == slug), None)
    if not room:
        raise HTTPException(404, "room not found for scenario")
    return {"room_id": room.id, "room": room.model_dump(mode="json")}


def _pipeline_cards(eng, tenant_id: str | None = None) -> list[dict]:
    from .tenant import resolve_tenant
    from .workflow import workflow_from_store

    cards = []
    for room in eng.store.list_rooms():
        if room.status != "open":
            continue
        if tenant_id and room.tenant_id not in (None, tenant_id):
            continue
        inv = eng.store.get_investigation(room.investigation_id) if room.investigation_id else None
        state = inv.state if inv else None
        actions = eng.store.list_actions(inv.id) if inv else []
        awaiting = any(a.status in {"proposed", "awaiting_approval"} for a in actions)
        funnel = workflow_from_store(eng.store, room, inv)
        tenant = resolve_tenant(eng.store, investigation=inv, room=room)
        pr_url = None
        pending_action_id = None
        for act in actions:
            exe = (act.artifacts or {}).get("execution") if act.artifacts else {}
            if isinstance(exe, dict):
                pr_url = exe.get("pr_url") or exe.get("code_pr_url") or pr_url
            if act.status in {"proposed", "awaiting_approval"} and not pending_action_id:
                pending_action_id = act.id
        evidence_snippet = ""
        if inv:
            hyps = eng.store.list_hypotheses(inv.id)
            if hyps:
                evidence_snippet = (hyps[0].statement or "")[:120]
            if not evidence_snippet:
                ev = eng.store.list_evidence(inv.id)
                if ev:
                    evidence_snippet = (ev[0].claim or "")[:120]
        inv_state = str(getattr(state, "value", state) if state else "")
        verified = inv_state in {"resolved", "partially_resolved"}
        denied = any(a.status == "denied" for a in actions) or (
            str(getattr(room, "path", "") or "").upper() == "SECURITY"
            or str(getattr(room, "kind", "") or "") == "review"
        )
        active_agents = [
            aid
            for aid, ev in HUB.presence.get(room.id, {}).items()
            if str(ev.get("status") or "idle") not in {"idle", ""}
        ]
        calendar_snippet = ""
        calendar_url = None
        meet_url = None
        gmail_url = None
        voice_snippet = ""
        contact_phone = None
        call_feedback = None
        warehouse_snippet = ""
        code_snippet = ""
        activity_line = ""
        activity_author = ""
        for msg in reversed(eng.store.list_messages(room.id)):
            art = msg.artifact if isinstance(msg.artifact, dict) else {}
            if msg.artifact_type == "coordination":
                slot = art.get("slot") or {}
                if not calendar_snippet and slot.get("start"):
                    calendar_snippet = f"Hold {str(slot['start'])[:16].replace('T', ' ')}"
                if slot.get("event_url"):
                    url = str(slot["event_url"])
                    if "meet.google" in url:
                        meet_url = meet_url or url
                    else:
                        calendar_url = calendar_url or url
                if art.get("gmail_url"):
                    gmail_url = gmail_url or str(art["gmail_url"])
            if not voice_snippet and msg.artifact_type == "voice" and msg.text:
                voice_snippet = (msg.text or "")[:80]
            if not contact_phone:
                for key in ("phone", "callback_phone", "to_number"):
                    raw = art.get(key)
                    if isinstance(raw, str) and raw.strip():
                        contact_phone = raw.strip()
                        break
            if not call_feedback and msg.artifact_type in {"call_feedback", "call_evidence"} and msg.text:
                call_feedback = (msg.text or "")[:160]
            if not warehouse_snippet and msg.artifact_type in {
                "analytics",
                "warehouse",
                "bq",
                "metric",
                "evidence",
            }:
                warehouse_snippet = (msg.text or "")[:100]
            if not code_snippet and msg.artifact_type in {"code", "code_brief", "pr", "patch"}:
                code_snippet = (msg.text or "")[:100]
            if not activity_line and msg.author_kind == "agent" and (msg.text or "").strip():
                # Prefer contact lookup / call / warehouse / code chatter for the live footer.
                if msg.artifact_type in {
                    "contact",
                    "contact_lookup",
                    "call",
                    "call_feedback",
                    "call_transcript",
                    "voice",
                    "analytics",
                    "warehouse",
                    "code",
                    "code_brief",
                    "pr",
                    "coordination",
                } or msg.kind == "chat":
                    activity_line = (msg.text or "")[:120]
                    activity_author = msg.author or ""
            if (
                calendar_snippet
                and voice_snippet
                and contact_phone
                and call_feedback
                and activity_line
            ):
                break
        if not activity_line:
            if call_feedback:
                activity_line = call_feedback
                activity_author = "customer_voice_agent"
            elif warehouse_snippet:
                activity_line = warehouse_snippet
                activity_author = "analytics_agent"
            elif code_snippet:
                activity_line = code_snippet
                activity_author = "code_agent"
            elif voice_snippet:
                activity_line = voice_snippet
                activity_author = "customer_voice"
        cards.append(
            {
                "room_id": room.id,
                "title": room.title,
                "stage": funnel["current"],
                "kind": funnel["kind"],
                "workflow": {
                    "nodes": funnel.get("nodes"),
                    "steps": funnel.get("steps"),
                    "current": funnel.get("current"),
                    "needs": funnel.get("needs"),
                    "tags": funnel.get("tags"),
                },
                "tenant_id": room.tenant_id,
                "tenant_product": tenant.product if tenant else None,
                "scenario_id": room.scenario_id,
                "investigation_id": room.investigation_id,
                "awaiting_approval": awaiting,
                "pending_action_id": pending_action_id,
                "pr_url": pr_url,
                "evidence_snippet": evidence_snippet,
                "calendar_snippet": calendar_snippet or None,
                "calendar_url": calendar_url,
                "meet_url": meet_url,
                "gmail_url": gmail_url,
                "voice_snippet": voice_snippet or None,
                "contact_phone": contact_phone,
                "call_feedback": call_feedback,
                "warehouse_snippet": warehouse_snippet or None,
                "code_snippet": code_snippet or None,
                "activity_line": activity_line or None,
                "activity_author": activity_author or None,
                "verified": verified,
                "denied": denied,
                "active_agents": active_agents,
            }
        )
    return cards


@app.get("/api/pipeline")
def pipeline_board(_actor: AdminUnlessEval, tenant_id: str | None = Query(default=None)):
    """Kanban-style cards for open investigations — columns from active workflows."""
    from .workflow import NODE_LABEL, focus_steps, union_columns

    eng = get_engine()
    cards = _pipeline_cards(eng, tenant_id=tenant_id)
    workflows = [c.get("workflow") or {} for c in cards]
    columns = union_columns(workflows)
    focus = None
    ranked: list[dict] = []
    if cards:
        ranked = sorted(
            cards,
            key=lambda c: (
                2 if c.get("awaiting_approval") else 1 if c.get("active_agents") else 0,
                1 if c.get("kind") == "bug" else 0,
            ),
            reverse=True,
        )
        focus = ranked[0].get("workflow")
    from .orchestration import home_orchestration

    orch = home_orchestration(eng.store, eng)
    return {
        "columns": columns,
        "column_labels": {c: NODE_LABEL.get(c, c) for c in columns},
        "cards": cards,
        "focus": {
            "mode": orch.get("mode"),
            "watch_line": orch.get("watch_line"),
            "signal_agent": orch.get("signal_agent"),
            "steps": focus_steps(orchestration=orch),
            "handoffs": orch.get("handoffs") or [],
            "current": orch.get("current") or (focus or {}).get("current"),
            "kind": orch.get("kind") or (focus or {}).get("kind"),
            "needs": orch.get("needs") or (focus or {}).get("needs"),
            "tags": orch.get("tags") or (focus or {}).get("tags") or [],
            "room_id": orch.get("room_id") or (ranked[0]["room_id"] if ranked else None),
        },
    }


@app.get("/api/orchestration/home")
def orchestration_home(tenant_id: str | None = Query(default=None)):
    """Progressive homepage flow — watching or active case with handoff reasons."""
    from .orchestration import home_orchestration

    eng = get_engine()
    _ = tenant_id  # reserved for tenant-scoped watch
    return home_orchestration(eng.store, eng)


@app.get("/api/workflows/focus")
def workflows_focus(tenant_id: str | None = Query(default=None)):
    """Homepage flow — progressive steps + handoffs, not a hardcoded pipeline."""
    from .orchestration import home_orchestration

    eng = get_engine()
    _ = tenant_id
    orch = home_orchestration(eng.store, eng)
    return {
        "mode": orch.get("mode", "watching"),
        "watch_line": orch.get("watch_line"),
        "signal_agent": orch.get("signal_agent"),
        "steps": orch.get("steps") or [],
        "handoffs": orch.get("handoffs") or [],
        "current": orch.get("current"),
        "kind": orch.get("kind"),
        "needs": orch.get("needs") or {},
        "tags": orch.get("tags") or [],
        "room_id": orch.get("room_id"),
    }


@app.get("/api/live-work")
def live_work_board(_actor: AdminUnlessEval):
    """Homepage live work board — receipts that pile into Signal → Evidence → Code → Approve → Verify."""
    from .live_work import build_live_work
    from .proof import enrich_card_proof

    eng = get_engine()
    out = build_live_work(eng.store)
    cards = []
    for card in out.get("cards") or []:
        # Prefer proof already stored on the message artifact
        room_id = card.get("room_id")
        if room_id and not card.get("proof"):
            for msg in eng.store.list_messages(room_id):
                if msg.id != card.get("id"):
                    continue
                art = msg.artifact if isinstance(msg.artifact, dict) else {}
                if isinstance(art.get("proof"), dict):
                    card["proof"] = art["proof"]
                break
        cards.append(enrich_card_proof(eng.store, card, engine=eng))
    out["cards"] = cards
    return out


@app.get("/api/proof")
def proof_bundle(_actor: AdminUnlessEval):
    """Homepage trust strip — live BQ/GA4 tables + latest GitHub PR."""
    from .proof import homepage_proofs

    return homepage_proofs(get_engine())


@app.get("/api/proof/resources")
def proof_resources(
    agent: str = Query(default=""),
    signal: str = Query(default=""),
    arm: str = Query(default=""),
):
    """Live connector cards scoped to an agent, signal source, or fan-out arm."""
    from .proof import (
        agent_resources,
        all_resource_cards,
        fanout_arm_resources,
        signal_source_resources,
    )

    eng = get_engine()
    if agent.strip():
        return {"scope": "agent", "id": agent.strip(), "cards": agent_resources(eng, agent.strip())}
    if signal.strip() in {"push", "pull"}:
        return {"scope": "signal", "id": signal.strip(), "cards": signal_source_resources(eng, signal.strip())}
    if arm.strip():
        return {"scope": "arm", "id": arm.strip(), "cards": fanout_arm_resources(eng, arm.strip())}
    return {"scope": "all", "id": "", "cards": all_resource_cards(eng)}


@app.get("/api/proof/github")
def proof_github(url: str = Query(default="")):
    from .proof import github_pr_proof

    eng = get_engine()
    tenants = eng.store.list_tenants()
    tenant = next((t for t in tenants if t.repo), None)
    return github_pr_proof(url, tenant=tenant)


@app.get("/api/proof/warehouse")
def proof_warehouse(metric: str = Query(default="purchase_conversion")):
    from .proof import warehouse_proof

    eng = get_engine()
    tenants = eng.store.list_tenants()
    tenant = next((t for t in tenants if t.repo or t.connected), tenants[0] if tenants else None)
    return warehouse_proof(eng, tenant, metric=metric)


@app.get("/api/activity")
def activity_feed(limit: int = Query(default=60, ge=1, le=200)):
    from .activity import list_activity

    return {"events": list_activity(limit=limit)}


@app.post("/api/demo/run")
def demo_run():
    """One-click tenant signal demo — real pipeline, paced so you can watch it."""
    from loop.runtime_mode import require_eval

    from .tenant import seed_placeholder
    from .world import ensure_api_ready, ingest_tenant_signal

    require_eval("guided demo")
    eng = get_engine()
    ensure_api_ready(eng)
    tenant = seed_placeholder(eng.store)
    import os

    from .activity import emit_activity

    prev_staged = os.environ.get("LOOP_DEMO_STAGED")
    prev_ms = os.environ.get("LOOP_DEMO_STAGE_MS")
    os.environ["LOOP_DEMO_STAGED"] = "1"
    # Visible pacing between real investigator steps (~0.9s each)
    os.environ.setdefault("LOOP_DEMO_STAGE_MS", "900")
    # Return as soon as the room opens; finish fan-out in a background thread
    async_finish = os.environ.get("LOOP_DEMO_ASYNC", "1") == "1"
    emit_activity(agent_id="demo", message="Demo signal started — collecting live warehouse facts", stage="signal", tenant_id=tenant.id)
    try:
        out = ingest_tenant_signal(
            eng,
            tenant,
            metric="checkout_conversion",
            magnitude=-0.14,
            baseline=0.72,
            note="Demo: checkout conversion dropped after deploy",
            source="demo.run",
            async_finish=async_finish,
        )
    finally:
        if prev_staged is None:
            os.environ.pop("LOOP_DEMO_STAGED", None)
        else:
            os.environ["LOOP_DEMO_STAGED"] = prev_staged
        if prev_ms is None and "LOOP_DEMO_STAGE_MS" in os.environ and os.environ.get("LOOP_DEMO_STAGE_MS") == "900":
            # only clear if we set the default and there was no prior value — keep if caller set
            pass
    emit_activity(
        agent_id="signal_agent",
        message="Room open — investigators working (watch Live work + Traces)",
        room_id=out.get("room_id", ""),
        stage="investigate",
        tenant_id=tenant.id,
    )
    return {
        "demo": True,
        "tenant_id": tenant.id,
        "room_id": out.get("room_id"),
        "investigation_id": out.get("investigation_id"),
        "joined": out.get("joined", False),
        "async": bool(out.get("async")),
    }


@app.get("/api/config")
def public_config():
    from loop.runtime_mode import FIXTURE_SCENARIOS, is_eval_mode

    return {
        "eval_mode": is_eval_mode(),
        "hosted": bool(os.environ.get("K_SERVICE")),
        "fixture_scenarios": list(FIXTURE_SCENARIOS),
    }


@app.get("/api/rooms/{room_id}")
def room_detail(
    room_id: str,
    _actor: AdminUnlessEval,
    slim: bool = Query(default=True),
    full: bool = Query(default=False),
):
    from .tenant import resolve_tenant

    eng = get_engine()
    room = eng.store.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    inv = eng.store.get_investigation(room.investigation_id) if room.investigation_id else None
    messages = list(eng.store.list_messages(room_id))
    message_count = len(messages)
    msg_cap = 60 if (slim and not full) else 80
    if message_count > msg_cap:
        messages = messages[-msg_cap:]
    bundle = _bundle(eng, room.investigation_id, slim=(slim and not full)) if inv else None
    tenant = resolve_tenant(eng.store, investigation=inv, room=room)
    from .workflow import workflow_from_store

    actions = eng.store.list_actions(inv.id) if inv else []
    return {
        "room": room.model_dump(mode="json"),
        "messages": [m.model_dump(mode="json") for m in messages],
        "message_count": message_count,
        "bundle": bundle,
        "members": room.members,
        "presence": HUB.agents_in(room_id),
        "funnel": workflow_from_store(eng.store, room, inv, messages=messages, actions=actions),
        "tenant": (
            {"id": tenant.id, "name": tenant.name, "product": tenant.product, "repo": tenant.repo}
            if tenant
            else None
        ),
    }


@app.post("/api/rooms/{room_id}/messages")
def room_post(room_id: str, body: RoomPostBody, _actor: AdminUnlessEval):
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
def registry(_actor: AdminUnlessEval):
    return {"agents": [e.model_dump(mode="json") for e in ENTRIES]}


@app.get("/api/memory")
def memory(_actor: AdminUnlessEval, q: str = "", type: str | None = None, tenant_id: str | None = None):
    from loop import firestore_memory

    eng = get_engine()
    mirror = firestore_memory.status()
    by_kind: dict[str, list] = {"customer": [], "product": [], "engineering": [], "organizational": []}
    items = eng.store.list_memory(type, tenant_id=tenant_id) if type else eng.store.list_memory(tenant_id=tenant_id)
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
    return {
        "memory": by_kind,
        "lessons": [lesson.model_dump(mode="json") for lesson in eng.store.list_lessons()],
        "mirror": mirror,
        "source": "sqlite" if not mirror.get("operational") else "sqlite+firestore",
    }


@app.post("/api/memory")
def memory_remember(body: MemoryInBody, _actor: AdminUnlessEval):
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
    from loop.runtime_mode import is_eval_mode
    from loop.world import scenario_index

    eng = get_engine()
    rows = list(scenario_index(eng))
    if is_eval_mode() and not any(str(r.get("id")) == "checkout_abandon" for r in rows):
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
def traces(_actor: AdminUnlessEval):
    """Workflow group chats — natural language end-to-end, not handoff pairs."""
    from .narrate import build_workflow_chat, humanize_handoff

    eng = get_engine()
    rooms_by_inv = {r.investigation_id: r for r in eng.store.list_rooms() if r.investigation_id}
    calls: list[dict] = []
    threads: list[dict] = []
    for inv in eng.store.list_investigations():
        room = rooms_by_inv.get(inv.id)
        agent_calls = list(eng.store.list_agent_calls(inv.id))
        for c in agent_calls:
            row = c.model_dump(mode="json")
            row["summary"] = humanize_handoff(c.from_agent, c.to_agent, c.summary)
            if room:
                row["room_id"] = room.id
                row["room_title"] = room.title
            calls.append(row)
        messages = list(eng.store.list_messages(room.id)) if room else []
        events = build_workflow_chat(
            investigation_id=inv.id,
            room=room,
            agent_calls=agent_calls,
            messages=messages,
        )
        if not events:
            continue
        # Members who spoke in this workflow
        members = []
        seen: set[str] = set()
        for e in events:
            a = e.get("author")
            if a and a not in seen and e.get("kind") == "chat":
                seen.add(str(a))
                members.append(str(a))
        threads.append(
            {
                "investigation_id": inv.id,
                "room_id": room.id if room else None,
                "title": (room.title if room else None) or inv.title or inv.id,
                "kind": room.kind.value if room else None,
                "events": events,
                "members": members,
                "latest_at": events[-1].get("at"),
            }
        )
    threads.sort(key=lambda t: str(t.get("latest_at") or ""), reverse=True)
    return {
        "traces": calls,
        "threads": threads,
        "verdicts": [v.model_dump(mode="json") for v in eng.store.list_verdicts()],
    }


@app.get("/api/traces/{trace_id}")
def trace_detail(trace_id: str, _actor: AdminUnlessEval):
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
def signals(_actor: AdminUnlessEval):
    from .engine import dedupe_signals

    raw = get_engine().store.list_signals()
    return {"signals": [s.model_dump(mode="json") for s in dedupe_signals(raw)]}


@app.post("/api/signals")
def post_signal(_actor: AdminUnlessEval, body: SignalInBody):
    """Ingest a signal → investigation pipeline with live WS events (eval/admin only when hosted)."""
    from .unified_runner import run_signal_pipeline

    eng = get_engine()
    from loop.world import ensure_api_ready

    ensure_api_ready(eng)
    fork = (body.fork or ("FEATURE" if body.polarity == "positive" else "BUG")).upper()
    scenario = body.scenario or f"signal:{body.metric}"
    sig = {
        "source": body.source,
        "polarity": body.polarity,
        "domain": body.domain,
        "metric": body.metric,
        "delta": body.delta,
        "dimensions": body.dimensions,
        "fork": fork,
        "scenario": scenario,
        "title": body.title or f"{body.metric} ({body.polarity})",
    }
    try:
        from .connectors.warehouse import publish_signal

        publish_signal({**sig, "path": "api.signals"})
    except Exception:
        pass
    result = run_signal_pipeline(
        eng,
        None,
        sig,
        fork=fork,
        probe_exfil=body.scenario in {"security_exfil", "pii-exfil-deny"},
    )
    return {
        "signalId": f"sig-{str(result.get('trace_id', ''))[:8]}",
        "roomId": result.get("room_id"),
        "room_id": result.get("room_id"),
        "trace_id": result.get("trace_id"),
        "fork": result.get("fork"),
        "pipeline": result.get("pipeline"),
        "steps": result.get("steps"),
        "investigation_id": result.get("investigation_id"),
        "reused": result.get("reused", False),
    }


@app.get("/api/investigations")
def investigations(_actor: AdminUnlessEval):
    eng = get_engine()
    items = []
    for inv in eng.store.list_investigations():
        items.append(_summary(eng, inv.id))
    return {"investigations": items}


@app.get("/api/investigations/{inv_id}")
def investigation(inv_id: str, _actor: AdminUnlessEval):
    eng = get_engine()
    if not eng.store.get_investigation(inv_id):
        raise HTTPException(404, "investigation not found")
    return _bundle(eng, inv_id)


def _publish_incident_for_investigation(eng, inv_id: str) -> None:
    inv = eng.store.get_investigation(inv_id)
    if inv and inv.tenant_id:
        try:
            from .incident_lifecycle import publish_incident_lifecycle

            publish_incident_lifecycle(eng, inv.tenant_id)
        except Exception:
            pass


def _publish_human_input_after_approve(eng, action, rid: str | None) -> None:
    """After HIGH approve — prompt OAuth or calendar slot on homepage (HITL in workflow)."""
    from .connectors import calendar as cal
    from .connectors import google_oauth

    oauth = google_oauth.status()
    if not oauth.get("connected"):
        HUB.publish_global(
            {
                "type": "human_input_required",
                "kind": "oauth",
                "reason": "Calendar holds and mail to your connected inbox need Workspace OAuth once.",
                "authorize_url": oauth.get("authorize_url") or "/api/oauth/google/start",
                "redirect_uri": oauth.get("redirect_uri"),
                "room_id": rid,
                "action_id": getattr(action, "id", None),
            }
        )
        return
    suggested = cal.suggest_times(limit=5)
    slots = suggested.get("slots") or []
    if not slots:
        return
    room = eng.store.get_room(rid) if rid else None
    title = room.title if room else "Post-approve review"
    HUB.publish_global(
        {
            "type": "human_input_required",
            "kind": "calendar",
            "room_id": rid,
            "action_id": getattr(action, "id", None),
            "title": title,
            "slots": slots,
        }
    )


@app.get("/api/approvals")
def approvals(_actor: AdminUnlessEval):
    from .room_ui import visible_pending_approvals

    eng = get_engine()
    gate = _gate(eng)
    pending = [_action_row(eng, a) for a in visible_pending_approvals(eng.store)]
    history = [a.model_dump(mode="json") for a in eng.store.list_approvals()]
    return {"pending": pending, "history": history, "gate": gate}


@app.post("/api/approvals/{action_id}")
def decide(
    action_id: str,
    body: ApproveBody,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    from .audit import record
    from .auth import require_approval

    require_approval(authorization, actor=body.approver)
    eng = get_engine()
    action = eng.store.get_action(action_id)
    if not action:
        raise HTTPException(404, "action not found")
    # Skip-if-done HITL (before_tool_callback pattern).
    if body.decision == "approve" and action.status == "executed":
        execution = (action.artifacts or {}).get("execution") or {}
        inv_id = action.investigation_id
        has_outcome = any(o.investigation_id == inv_id for o in eng.store.list_outcomes())
        outcome_payload = None
        if not has_outcome:
            outcome = eng.verify(inv_id)
            outcome_payload = outcome.model_dump(mode="json")
        return _approve_payload(
            eng,
            action_id,
            inv_id,
            execution=execution,
            outcome=outcome_payload,
            approval="approve",
            reused=True,
        )
    if body.decision == "approve":
        outcome = eng.resume_after_approval(action_id, body.approver, body.rationale)
        fresh = eng.store.get_action(action_id)
        execution = ((fresh.artifacts or {}).get("execution") if fresh else None) or {}
        if isinstance(outcome, dict) and outcome.get("deferred"):
            from .live import room_id_for_investigation

            rid = room_id_for_investigation(eng.store, action.investigation_id)
            if rid:
                HUB.publish(
                    rid,
                    {
                        "type": "approval_resolved",
                        "approval": {"id": action_id, "status": "approved", "deferred_verify": True},
                    },
                )
                HUB.publish_global(
                    {
                        "type": "approval_resolved",
                        "approval": {"action_id": action_id, "room_id": rid, "status": "approved"},
                    }
                )
                background_tasks.add_task(_publish_human_input_after_approve, eng, fresh or action, rid)
            background_tasks.add_task(_publish_incident_for_investigation, eng, action.investigation_id)
            record(
                eng.store,
                actor=body.approver,
                action="approval.approve",
                resource=f"action:{action_id}",
                detail={"rationale": body.rationale, "execution": execution, "deferred_verify": True},
            )
            return _approve_payload(
                eng,
                action_id,
                action.investigation_id,
                execution=execution,
                approval="approve",
                deferred_verify=True,
                verify_job_id=outcome.get("verify_job_id"),
            )
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
            HUB.publish_global(
                {
                    "type": "approval_resolved",
                    "approval": {"action_id": action_id, "room_id": rid, "status": "approved"},
                }
            )
            if execution.get("pr_url"):
                room = eng.store.get_room(rid)
                HUB.publish_global(
                    {
                        "type": "payoff",
                        "kind": "pr_opened",
                        "room_id": rid,
                        "pr_url": execution.get("pr_url"),
                        "title": room.title if room else "",
                    }
                )
                from .proof import github_pr_proof
                from .world import post as room_post

                tenant = eng.store.get_tenant(room.tenant_id) if room and room.tenant_id else None
                proof = github_pr_proof(str(execution.get("pr_url")), tenant=tenant)
                if fresh:
                    exe = dict((fresh.artifacts or {}).get("execution") or {})
                    exe["proof"] = proof
                    fresh.artifacts["execution"] = exe
                    eng.store.put_action(fresh)
                room_post(
                    eng,
                    rid,
                    author="code_agent",
                    author_kind="agent",
                    kind="artifact",
                    text=f"Opened PR: {execution.get('pr_url')}",
                    artifact_type="pr",
                    artifact={
                        "pr_url": execution.get("pr_url"),
                        "url": execution.get("pr_url"),
                        "status": "open",
                        "proof": proof,
                    },
                )
            background_tasks.add_task(_publish_human_input_after_approve, eng, fresh or action, rid)
        background_tasks.add_task(_publish_incident_for_investigation, eng, action.investigation_id)
        record(
            eng.store,
            actor=body.approver,
            action="approval.approve",
            resource=f"action:{action_id}",
            detail={"rationale": body.rationale, "execution": execution},
        )
        outcome_payload = outcome.model_dump(mode="json") if hasattr(outcome, "model_dump") else outcome
        return _approve_payload(
            eng,
            action_id,
            action.investigation_id,
            execution=execution,
            outcome=outcome_payload,
            approval="approve",
        )
    approval = eng.approve(action_id, body.approver, "deny", body.rationale)
    record(
        eng.store,
        actor=body.approver,
        action="approval.deny",
        resource=f"action:{action_id}",
        detail={"rationale": body.rationale},
    )
    return _approve_payload(
        eng,
        action_id,
        action.investigation_id,
        approval=approval.model_dump(mode="json"),
    )


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


@app.post("/api/internal/state/persist")
def persist_state(
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
):
    """Flush live sqlite to GCS before package/deploy. No-op when GCS URI is unset."""
    from loop.state_persist import persist_now

    from .auth import require_admin_or_internal

    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    eng = get_engine()
    ok = persist_now(eng.store.path)
    return {"ok": bool(ok), "uri_configured": bool(os.environ.get("LOOP_STATE_GCS_URI"))}


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
    detected = eng.detect_all_signals()
    from .auto_investigate import count_applied, open_signal_ids_for_auto_investigate

    open_ids = open_signal_ids_for_auto_investigate(eng, detected)
    investigated: list[dict] = []
    if os.environ.get("LOOP_AUTO_INVESTIGATE", "1") == "1" and open_ids:
        from .auto_investigate import auto_investigate_new_signals

        investigated = auto_investigate_new_signals(eng, open_ids)
    elif os.environ.get("LOOP_AUTO_INVESTIGATE", "1") == "1":
        from .auto_investigate import finish_stalled_investigations

        investigated = finish_stalled_investigations(eng)
    processed: list[dict] = []
    for _ in range(limit):
        result = process_one(eng.store, eng)
        if not result:
            break
        processed.append(result)
    payload = {
        "processed": processed,
        "count": len(processed),
        "detected": len(detected),
        "investigated": investigated,
        "auto_investigated": count_applied(investigated),
    }
    from .worker_heartbeat import record_tick

    record_tick(payload)
    return payload


@app.post("/api/internal/pubsub/signals")
def pubsub_signals_push(
    body: dict,
    authorization: str | None = Header(default=None),
    x_loop_worker: str | None = Header(default=None, alias="X-Loop-Worker"),
):
    from .auth import require_admin_or_internal
    from .pubsub_consumer import decode_push, handle_signal_push

    require_admin_or_internal(authorization, internal_header=x_loop_worker)
    payload = decode_push(body) or body
    if not isinstance(payload, dict):
        raise HTTPException(400, "invalid pubsub payload")
    result = handle_signal_push(get_engine(), payload)
    return {"result": result}


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
    from loop.runtime_mode import require_eval

    from .unified_runner import run_signal_pipeline

    require_eval("fixture scenario runner")
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
    import os

    prev_staged = os.environ.get("LOOP_DEMO_STAGED")
    os.environ["LOOP_DEMO_STAGED"] = "1"
    try:
        result = run_signal_pipeline(
            eng,
            room.id,
            signal,
            fork=fork,
            probe_exfil=slug in {"security_exfil", "pii-exfil-deny"},
            tenant_id=room.tenant_id,
            live_progress=True,
        )
    finally:
        if prev_staged is None:
            os.environ.pop("LOOP_DEMO_STAGED", None)
        else:
            os.environ["LOOP_DEMO_STAGED"] = prev_staged
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


@app.get("/api/workflows/links")
def workflow_links():
    """Openable Calendar / Meet / Gmail / PR links from coordination + actions."""
    from .workflow_links import collect_workflow_links

    eng = get_engine()
    return collect_workflow_links(eng)


class AgentCallbackBody(BaseModel):
    room_id: str = ""
    tenant_id: str = ""
    agent_id: str = "orchestrator"
    status: str = "thinking"
    message: str = ""
    kind: str = "agent_presence"
    stage: str = ""
    data: dict = {}
    artifact: dict = {}


@app.post("/api/agent_callback")
def agent_callback(body: AgentCallbackBody, _actor: AdminUnlessEval):
    """Live push: agents POST updates → WebSocket fans out."""
    from .activity import emit_activity

    rid = body.room_id
    if not rid:
        raise HTTPException(400, "room_id required")
    if body.kind == "agent_presence" or body.status:
        HUB.set_presence(rid, body.agent_id, body.status or "thinking", {"label": body.agent_id})
    if body.message or body.stage:
        emit_activity(
            agent_id=body.agent_id,
            message=body.message or f"{body.agent_id} · {body.stage or body.status}",
            room_id=rid,
            stage=body.stage or body.status,
            tenant_id=body.tenant_id,
            artifact=body.artifact or None,
        )
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


@app.get("/ws", include_in_schema=False)
def ws_http_probe() -> None:
    """Plain HTTP GET must not fall through to the SPA — browsers upgrade via WebSocket."""
    raise HTTPException(
        405,
        "WebSocket upgrade required — connect with wss://",
        headers={"Upgrade": "websocket"},
    )


@app.get("/ws/rooms/{room_id}", include_in_schema=False)
def ws_room_http_probe(room_id: str) -> None:
    raise HTTPException(
        405,
        "WebSocket upgrade required — connect with wss://",
        headers={"Upgrade": "websocket"},
    )


@app.websocket("/ws")
async def ws_global(ws: WebSocket):
    import json

    from .activity import list_activity

    await HUB.connect_global(ws)
    try:
        eng = get_engine()
        await ws.send_text(
            json.dumps(
                {
                    "type": "initial_state",
                    "status": _status_payload(eng),
                    "activity": list_activity(25),
                    "pipeline": {"cards": _pipeline_cards(eng)},
                },
                default=str,
            )
        )
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
def office(_actor: AdminUnlessEval):
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


def _investigation_verdicts(eng: LoopEngine, inv_id: str) -> list[dict]:
    agents = {
        name
        for call in eng.store.list_agent_calls(inv_id)
        for name in (call.from_agent, call.to_agent)
        if name
    }
    recent = eng.store.list_recent_verdicts(48) if hasattr(eng.store, "list_recent_verdicts") else eng.store.list_verdicts()[-48:]
    return [
        v.model_dump(mode="json")
        for v in recent
        if v.agent_identity in agents
    ]


def _approve_payload(
    eng: LoopEngine,
    action_id: str,
    inv_id: str,
    *,
    execution: dict | None = None,
    outcome: dict | None = None,
    **extra,
) -> dict:
    """Small approve response — avoid shipping full investigation bundles over slow links."""
    inv = eng.store.get_investigation(inv_id)
    exec_blob = dict(execution or {})
    payload: dict = {
        "action_id": action_id,
        "investigation_id": inv_id,
        "room_id": inv.room_id if inv else None,
        "execution": exec_blob,
        "pr_url": exec_blob.get("pr_url"),
    }
    if outcome is not None:
        payload["outcome"] = outcome
    payload.update(extra)
    return payload


def _bundle(eng: LoopEngine, inv_id: str, *, slim: bool = False) -> dict:
    from .room_ui import visible_pending_actions

    inv = eng.store.get_investigation(inv_id)
    assert inv
    pending = visible_pending_actions(eng.store, inv_id)
    evidence = eng.store.list_evidence(inv_id)
    if slim:
        evidence = evidence[-24:]
    timeline_cap = 24 if slim else 48
    calls_cap = 24 if slim else 48
    hypotheses = eng.store.list_hypotheses(inv_id)
    if slim:
        hypotheses = hypotheses[:3]
    actions = eng.store.list_actions(inv_id)
    return {
        "investigation": inv.model_dump(mode="json"),
        "signals": [
            s.model_dump(mode="json")
            for s in (eng.store.get_signal(i) for i in inv.originating_signal_ids)
            if s
        ],
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "hypotheses": [h.model_dump(mode="json") for h in hypotheses],
        "actions": [_action_row(eng, a) for a in actions],
        "pending_actions": [_action_row(eng, a) for a in pending],
        "approvals": (
            []
            if slim
            else [
                ap.model_dump(mode="json")
                for a in actions
                for ap in eng.store.list_approvals(a.id)
            ]
        ),
        "timeline": [t.model_dump(mode="json") for t in eng.store.list_timeline(inv_id)[-timeline_cap:]],
        "agent_calls": [
            c.model_dump(mode="json") for c in eng.store.list_agent_calls(inv_id)[-calls_cap:]
        ],
        "outcomes": [o.model_dump(mode="json") for o in eng.store.list_outcomes_for_investigation(inv_id)],
        "lessons": [lesson.model_dump(mode="json") for lesson in eng.store.list_lessons_for_investigation(inv_id)],
        "verdicts": _investigation_verdicts(eng, inv_id),
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
    if rel in {"ws"} or rel.startswith("ws/"):
        return None
    if rel.split("/", 1)[0] in {"shop", "company"}:
        return None
    if rel == "connect" or rel.startswith("connect/"):
        for candidate in (
            _STATIC / "connect" / "index.html",
            _STATIC / "connect.html",
            _STATIC / "settings" / "index.html",
            _STATIC / "settings.html",
        ):
            if candidate.is_file():
                return FileResponse(candidate)
    if not rel:
        return FileResponse(_STATIC / "index.html")
    first, _sep, rest = rel.partition("/")
    if _sep and first in {"rooms", "investigations", "agents"} and rest not in {"", "_"}:
        for placeholder in (
            _STATIC / first / "_" / "index.html",
            _STATIC / first / "_.html",
        ):
            if placeholder.is_file():
                return FileResponse(placeholder)
    # Flat export pages (rooms.html) must win over the rooms/ placeholder directory.
    flat_index = _STATIC / f"{rel}.html"
    if flat_index.is_file():
        return FileResponse(flat_index)
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
