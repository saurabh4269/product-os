"""FastAPI control plane for the console."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
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


@app.get("/api/health")
def health():
    return {"ok": True, "service": "loop", "hosted": bool(os.environ.get("K_SERVICE")), "region": settings().region}


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


@app.get("/api/company")
def company():
    """The dummy tenant Product OS is operating: shop, ads, flags, loop health."""
    eng = get_engine()
    raw = eng.wh.ads_rows()
    stats = [r for r in raw if r.get("_table") == "ads_CampaignStats"]
    dims = [r for r in raw if r.get("_table") == "ads_Campaign"]
    latest = max((s.get("_DATA_DATE") or "" for s in stats), default="")
    campaigns = []
    seen: set[str] = set()
    for d in dims:
        cid = str(d.get("campaign_id") or "")
        if not cid or cid in seen:
            continue
        if latest and d.get("_DATA_DATE") != latest:
            continue
        seen.add(cid)
        st = next(
            (s for s in stats if s.get("campaign_id") == cid and s.get("_DATA_DATE") == d.get("_DATA_DATE")),
            {},
        )
        campaigns.append(
            {
                "id": cid,
                "name": d.get("campaign_name"),
                "impressions": st.get("impressions"),
                "clicks": st.get("clicks"),
                "cost": st.get("cost"),
                "conversions": st.get("conversions"),
                "date": d.get("_DATA_DATE"),
            }
        )
    outcomes = eng.store.list_outcomes()
    return {
        "company": {
            "id": "northstar",
            "name": "Northstar",
            "product": "Home goods from one shop",
            "tagline": "Quiet things for a house",
        },
        "shop": {"path": "/shop/"},
        "flags": {
            "pay_sdk_4_3": eng.store.get_flag("pay_sdk_4_3") or "on",
            "onboarding_copy_exp_b": eng.store.get_flag("onboarding_copy_exp_b") or "on",
            "show_delivery_date_earlier": eng.store.get_flag("show_delivery_date_earlier") or "off",
        },
        "ads": campaigns,
        "loop": {
            "investigations": len(eng.store.list_investigations()),
            "pending": len(eng.store.pending_approvals()),
            "resolved": sum(1 for o in outcomes if "RESOLVED" in str(o.verdict).upper()),
            "failOpen": False,
        },
    }


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


def _shop_dir() -> Path | None:
    env = os.environ.get("LOOP_SHOP_DIR")
    candidates = [
        Path(env) if env else None,
        REPO_ROOT / "apps" / "northstar-shop" / "web",
        Path("/app/static/shop"),
        (_STATIC / "shop") if _STATIC else None,
    ]
    for c in candidates:
        if c and (c / "index.html").exists():
            return c
    return None


_SHOP = _shop_dir()


@app.get("/shop", include_in_schema=False)
@app.get("/shop/", include_in_schema=False)
def shop_root():
    if _SHOP is None:
        raise HTTPException(404, "shop not packaged")
    return FileResponse(_SHOP / "index.html")


@app.get("/shop/{path:path}", include_in_schema=False)
def shop_file(path: str):
    if _SHOP is None:
        raise HTTPException(404, "shop not packaged")
    rel = path.strip("/")
    if not rel or rel.endswith("/"):
        target = _SHOP / rel / "index.html" if rel else _SHOP / "index.html"
    else:
        target = _SHOP / rel
        if target.is_dir():
            target = target / "index.html"
    try:
        target.resolve().relative_to(_SHOP.resolve())
    except ValueError:
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    raise HTTPException(404)


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
