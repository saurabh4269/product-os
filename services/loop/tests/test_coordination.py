"""Developer coordination infra — risk-aware HITL, not a hardcoded payment review."""

from __future__ import annotations

from loop.connectors import calendar as cal
from loop.connectors.mail import send
from loop.coordination import (
    CoordinationRequest,
    build_plan,
    example_high_risk_payment_pr,
    example_low_risk_pr,
    resolve_owners,
    run_coordination,
)


def test_calendar_suggest_without_oauth():
    out = cal.suggest_times(duration_minutes=20, limit=3)
    assert out["connector"] == "calendar.suggest"
    assert out["status"] == "simulated"
    assert len(out["slots"]) >= 1
    assert out["slots"][0]["duration_minutes"] == 20


def test_low_risk_notify_only_no_merge(engine):
    req = example_low_risk_pr()
    req.room_id = engine.store.list_rooms()[0].id if engine.store.list_rooms() else None
    if req.room_id is None:
        engine.seed_world()
        req.room_id = next(r.id for r in engine.store.list_rooms())
    out = run_coordination(engine, req)
    plan = out["coordination"]["plan"]
    assert plan["notify_only"] is True
    assert plan["auto_merge"] is False
    assert out["pipeline"] == ["identify_owners", "notify", "wait"]
    assert out["coordination"]["slot"] is None
    gmail = next(
        n
        for n in out["coordination"]["notifications"]
        if n["channel"] in {"gmail_draft", "gmail"}
    )
    assert gmail["send_denied_third_party"]["status"] == "denied"
    assert gmail["send_denied_third_party"]["detail"] == "GMAIL_SEND_SELF_ONLY"


def test_high_risk_schedules_and_never_merges(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "android_sdk")
    req = example_high_risk_payment_pr()
    req.room_id = room.id
    out = run_coordination(engine, req)
    assert out["risk_tier"] == "HIGH"
    assert out["auto_merge"] is False
    assert "schedule_review" in out["pipeline"]
    assert out["coordination"]["slot"]["start"] == "2026-08-29T16:00:00Z"
    owners = out["coordination"]["owners"]
    assert any("payments-owner" in o["email"] for o in owners)
    kinds = {m.artifact_type for m in engine.store.list_messages(room.id) if m.artifact_type}
    assert "coordination" in kinds


def test_surface_codeowners_resolution():
    req = CoordinationRequest(
        kind="review_request",
        title="t",
        surface="payment checkout",
        risk_tier="HIGH",
        dimensions={"codeowners": {"payment": ["pay@x.dev"], "copy": ["copy@x.dev"], "*": ["oncall@x.dev"]}},
    )
    owners = resolve_owners(req)
    assert owners[0].email == "pay@x.dev"
    assert build_plan(req).with_meet is True
    assert build_plan(req).duration_minutes == 20


def test_gmail_send_third_party_denied():
    assert send("other@example.com", "hi", "body").status == "denied"
    assert send("other@example.com", "hi", "body").detail == "GMAIL_SEND_SELF_ONLY"


def test_android_fixture_uses_coordination_infra(engine):
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.scenario_id == "android_sdk")
    msgs = [m for m in engine.store.list_messages(room.id) if m.artifact_type == "coordination"]
    assert msgs
    art = msgs[-1].artifact or {}
    assert art.get("auto_merge") is False
    assert art.get("risk_tier") == "HIGH"
    assert any("android-payments" in (o.get("email") or "") for o in (art.get("owners") or []))
