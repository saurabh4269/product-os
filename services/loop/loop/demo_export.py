"""Export a generic Remotion bundle from the real pipeline — no fixture fallbacks."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop.config import settings
from loop.engine import LoopEngine
from loop.store import Store
from loop.warehouse import Warehouse

WAITING = {
    "signal": "Signal stage is waiting — no metric from the pipeline yet.",
    "evidence": "Evidence stage is waiting — specialists have not grouped sources yet.",
    "root_cause": "Root cause stage is waiting — hypothesis not locked yet.",
    "approval": "Approval stage is waiting — no HIGH consequence drafted yet.",
    "verified": "Verify stage is waiting — outcome not measured yet.",
    "lesson": "Memory stage is waiting — lesson not captured yet.",
}


def _signal_metric(bundle: dict[str, Any]) -> str:
    sig = (bundle.get("signals") or [None])[0]
    if sig and sig.get("metric"):
        return str(sig["metric"])
    inv = bundle.get("investigation") if isinstance(bundle.get("investigation"), dict) else {}
    scenario = str(inv.get("scenario_id") or "")
    if scenario.startswith("t:") and scenario.count(":") >= 2:
        return scenario.split(":", 2)[2]
    return ""


def lesson_scene_body(bundle: dict[str, Any]) -> str:
    """Lesson scene copy from this investigation only — not cross-metric recall."""
    lesson = (bundle.get("lessons") or [None])[0] if bundle.get("lessons") else None
    if lesson and lesson.get("statement"):
        return str(lesson["statement"])
    metric = _signal_metric(bundle)
    if metric:
        return f"Memory stage is waiting — lesson not captured yet for {metric}."
    return WAITING["lesson"]


def _bundle(engine: LoopEngine, inv_id: str) -> dict[str, Any]:
    from loop.api import _bundle as api_bundle

    return api_bundle(engine, inv_id)


def build_demo_scenes(type_a: dict[str, Any], type_b: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Six Remotion scenes derived from a real investigation bundle — honest waiting when empty."""
    del type_b  # export payload may include Type B; scenes focus on the primary Type A loop.

    sig = (type_a.get("signals") or [None])[0]
    if sig and sig.get("metric"):
        signal_body = (
            f"{sig['metric']} moved {float(sig.get('magnitude') or 0):+.1%} vs baseline "
            f"{float(sig.get('baseline') or 0):.1%} — detected from the pipeline."
        )
    else:
        signal_body = WAITING["signal"]

    evidence = [
        e
        for e in (type_a.get("evidence") or [])
        if str(e.get("trust_level") or "trusted") != "untrusted"
    ]
    groups = sorted({str(e.get("independence_group")) for e in evidence if e.get("independence_group")})
    if groups:
        evidence_body = (
            f"Parallel specialists · {' · '.join(groups[:6])}. "
            "Three-source gate before root cause."
        )
    else:
        evidence_body = WAITING["evidence"]

    hyp = (type_a.get("hypotheses") or [None])[0]
    root_body = str(hyp["statement"]) if hyp and hyp.get("statement") else WAITING["root_cause"]

    high_actions = [
        a for a in (type_a.get("actions") or []) if str(a.get("risk_tier") or "").upper() == "HIGH"
    ]
    action = high_actions[0] if high_actions else None
    if action and (action.get("consequence") or action.get("tier_rationale")):
        approval_body = str(action.get("consequence") or action.get("tier_rationale"))
    else:
        approval_body = WAITING["approval"]

    outcome = (type_a.get("outcomes") or [None])[0] if type_a.get("outcomes") else None
    metric = _signal_metric(type_a)
    if outcome and outcome.get("verdict") and str(outcome.get("verdict")).upper() != "NOT_RESOLVED":
        verified_body = (
            f"{outcome.get('verdict')}: {outcome.get('metric', metric or 'metric')} "
            f"{float(outcome.get('pre_value') or 0):.3g} → {float(outcome.get('post_value') or 0):.3g}."
        )
    elif metric:
        verified_body = f"Verify stage is waiting — {metric} outcome not measured yet."
    else:
        verified_body = WAITING["verified"]

    lesson_body = lesson_scene_body(type_a)

    return [
        {"title": "Signal", "body": signal_body},
        {"title": "Evidence", "body": evidence_body},
        {"title": "Root cause", "body": root_body},
        {"title": "HIGH approval", "body": approval_body},
        {"title": "Verified", "body": verified_body},
        {"title": "Lesson", "body": lesson_body},
    ]


def build_demo_export(data_dir: Path | None = None) -> dict[str, Any]:
    """Run generic Type A + Type B recipes and gateway deny; return Remotion payload."""
    from loop.investigation import run_investigation
    from loop.models import LoopType, PathKind, RoomKind
    from loop.scenario_pack import recipe_by_id, recipe_geo_5xx, run_recipe
    from loop.world import _run_security_exfil, ensure_standing_world

    cfg = settings()
    tmp: tempfile.TemporaryDirectory[str] | None = None
    if data_dir is None:
        tmp = tempfile.TemporaryDirectory(prefix="loop-demo-export-")
        data_dir = Path(tmp.name)

    store = Store(data_dir / "loop.db")
    wh = Warehouse(cfg.warehouse_path())
    engine = LoopEngine(store, wh)

    ensure_standing_world(engine)

    type_b_recipe = recipe_by_id("settings_workaround")
    assert type_b_recipe

    geo = recipe_geo_5xx()
    geo_dims = {
        **dict(geo.dimensions),
        "needs_call": True,
        "voice_subject": {"failure": "service unavailable", "device": "EU-West mobile"},
    }
    geo_event = geo.model_copy(update={"dimensions": geo_dims})
    type_a_result = run_investigation(
        engine,
        geo_event,
        scenario_id="demo:geo_5xx",
        propose_action=True,
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.INCIDENT,
        live_progress=False,
    )
    type_a_inv_id = str(type_a_result["investigation_id"])

    type_b_result = run_recipe(engine, type_b_recipe)
    type_b_inv_id = str(type_b_result.get("investigation_id") or "")
    type_b_bundle = _bundle(engine, type_b_inv_id) if type_b_inv_id else {}

    _run_security_exfil(engine)
    deny = next((v for v in engine.store.list_verdicts() if v.verdict == "DENY"), None)

    type_a_bundle = _bundle(engine, type_a_inv_id)
    gateway_payload = deny.model_dump(mode="json") if deny else None
    scenes = build_demo_scenes(type_a_bundle)

    payload: dict[str, Any] = {
        "meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": "generic",
            "type_a_recipe": "geo_5xx",
            "type_b_recipe": type_b_recipe.id,
            "loop_type": "type_a",
        },
        "scenes": scenes,
        "type_a": type_a_bundle,
        "type_b": type_b_bundle,
        "gateway_deny": gateway_payload,
        "loop_chip": "Type A · fix",
        **type_a_bundle,
    }
    if tmp is not None:
        tmp.cleanup()
    return payload


def write_demo_export(dest: Path, *, data_dir: Path | None = None) -> Path:
    payload = build_demo_export(data_dir=data_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    return dest


def _loop_chip(loop_type: str | None) -> str:
    raw = (loop_type or "type_a").lower()
    if raw in {"type_b", "b", "feature"}:
        return "Type B · improve"
    return "Type A · fix"


def build_hosted_demo_export(room_payload: dict[str, Any]) -> dict[str, Any]:
    """Remotion payload from a hosted room GET — never silent local geo_5xx."""
    bundle = dict(room_payload.get("bundle") or {})
    room = dict(room_payload.get("room") or {})
    inv = bundle.get("investigation") if isinstance(bundle.get("investigation"), dict) else {}
    loop_type = str(inv.get("loop_type") or room.get("loop_type") or "type_a")
    scenes = build_demo_scenes(bundle)
    return {
        "meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": "generic",
            "source": "hosted_room",
            "room_id": room.get("id"),
            "loop_type": loop_type,
        },
        "scenes": scenes,
        "type_a": bundle,
        "type_b": {},
        "gateway_deny": None,
        "loop_chip": _loop_chip(loop_type),
        **bundle,
    }


def fetch_hosted_room(room_id: str, *, api_base: str, token: str, timeout_s: int = 60) -> dict[str, Any]:
    """GET /api/rooms/{id} from a hosted control plane. Never prints the bearer."""
    import urllib.error
    import urllib.request

    base = (api_base or "").strip().rstrip("/")
    if not base:
        raise ValueError("hosted API base URL is required")
    if not token:
        raise ValueError("LOOP_ADMIN_TOKEN is required to export a hosted room")
    url = f"{base}/api/rooms/{room_id}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"hosted room GET {exc.code}") from exc
    data = json.loads(raw)
    if not isinstance(data, dict) or not data.get("bundle"):
        raise RuntimeError("hosted room has no investigation bundle")
    return data


def write_hosted_demo_export(dest: Path, room_payload: dict[str, Any]) -> Path:
    payload = build_hosted_demo_export(room_payload)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    return dest
