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


def _bundle(engine: LoopEngine, inv_id: str) -> dict[str, Any]:
    from loop.api import _bundle as api_bundle

    return api_bundle(engine, inv_id)


def build_demo_scenes(
    type_a: dict[str, Any],
    type_b: dict[str, Any],
    gateway_deny: dict[str, Any] | None,
) -> list[dict[str, str]]:
    sig = (type_a.get("signals") or [{}])[0]
    metric = str(sig.get("metric") or "primary_metric")
    mag = float(sig.get("magnitude") or 0)
    baseline = float(sig.get("baseline") or 0)
    evidence = [
        e
        for e in (type_a.get("evidence") or [])
        if str(e.get("trust_level") or "trusted") != "untrusted"
    ]
    groups = sorted({str(e.get("independence_group")) for e in evidence if e.get("independence_group")})
    voice = next((e for e in evidence if e.get("source_type") == "customer_voice"), None)
    ev_bits = groups[:5] if groups else []
    if voice and "customer_voice" not in ev_bits:
        ev_bits.append("customer_voice")

    action = (type_a.get("actions") or [{}])[0]
    type_a_loop = str((type_a.get("investigation") or {}).get("loop_type") or "type_a")
    type_b_loop = str((type_b.get("investigation") or {}).get("loop_type") or "type_b")

    outcome = (type_a.get("outcomes") or [None])[0] if type_a.get("outcomes") else None
    lesson = (type_a.get("lessons") or [None])[0] if type_a.get("lessons") else None
    recalled = (type_a.get("investigation") or {}).get("recalled_lessons") or []

    scenes: list[dict[str, str]] = [
        {
            "title": "Signal",
            "body": (
                f"{metric} moved {mag:+.0%} vs baseline {baseline:.0%} — "
                "detected from warehouse + tenant ingest."
            ),
        },
        {
            "title": "Evidence",
            "body": (
                f"Parallel specialists · {' · '.join(ev_bits) or 'analytics · logs · deploy'}. "
                "Three-source gate before root cause."
            ),
        },
        {
            "title": "Type A vs B",
            "body": (
                f"Type A fixes ({type_a_loop.replace('_', ' ')}) · "
                f"Type B improves ({type_b_loop.replace('_', ' ')}) — one pipeline, different doors."
            ),
        },
        {
            "title": "Risk door",
            "body": (
                f"{action.get('risk_tier', 'MEDIUM')} tier — "
                f"{action.get('consequence') or action.get('tier_rationale') or 'human approval before execute.'}"
            ),
        },
    ]

    if gateway_deny:
        scenes.append(
            {
                "title": "Gateway deny",
                "body": (
                    f"{gateway_deny.get('verdict', 'DENY')} · "
                    f"{gateway_deny.get('tool', 'tool')} blocked by gateway identity — not a prompt."
                ),
            }
        )
    else:
        scenes.append(
            {
                "title": "Gateway deny",
                "body": "Gateway identity blocks cross-boundary tools at execute time. fail_open=false.",
            }
        )

    if outcome and outcome.get("verdict") and str(outcome.get("verdict")).upper() != "NOT_RESOLVED":
        verify_line = (
            f"{outcome.get('verdict')}: {outcome.get('metric')} "
            f"{float(outcome.get('pre_value') or 0):.3g} → {float(outcome.get('post_value') or 0):.3g}."
        )
    else:
        verify_line = "Post-fix verify marks inconclusive when no live metric re-read."

    if recalled:
        lesson_line = str(recalled[0])
    elif lesson and lesson.get("statement"):
        lesson_line = str(lesson["statement"])
    else:
        lesson_line = verify_line
    scenes.append({"title": "Memory lesson", "body": lesson_line})
    return scenes


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
    scenes = build_demo_scenes(type_a_bundle, type_b_bundle, gateway_payload)

    payload: dict[str, Any] = {
        "meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": "generic",
            "type_a_recipe": "geo_5xx",
            "type_b_recipe": type_b_recipe.id,
        },
        "scenes": scenes,
        "type_a": type_a_bundle,
        "type_b": type_b_bundle,
        "gateway_deny": gateway_payload,
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
