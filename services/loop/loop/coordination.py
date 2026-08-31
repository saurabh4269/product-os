"""Developer coordination infrastructure — HITL in the company workflow.

Not a hardcoded PR-review demo. Recipes supply a CoordinationRequest; the pipeline:

  need human attention
       ↓
  resolve owners (CODEOWNERS / surface map / explicit)
       ↓
  risk policy (LOW notify+wait · MEDIUM slot · HIGH schedule+Meet)
       ↓
  calendar availability → suggest → create (OAuth or simulated)
       ↓
  notify (Gmail to your inbox only · chat/room)
       ↓
  leave awaiting human (never auto-merge)

Calendar tools live in connectors/calendar.py (list / freebusy / suggest / create).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from loop.models import RiskTier


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


# --- schemas -----------------------------------------------------------------


class Owner(BaseModel):
    id: str
    email: str = ""
    role: str = "reviewer"
    source: str = "explicit"  # explicit | codeowners | surface_map


class CoordinationRequest(BaseModel):
    """Something that needs a human in the real workflow (not only a UI button)."""

    kind: str  # review_request | approval_meeting | incident_sync | …
    title: str
    subject: str = ""
    surface: str = ""  # payment, auth, copy, experiment, …
    risk_tier: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    owners: list[str] = Field(default_factory=list)  # emails or handles
    duration_minutes: int | None = None
    prefer_meet: bool | None = None
    notify_channels: list[str] = Field(default_factory=lambda: ["gmail_draft", "room"])
    room_id: str | None = None
    action_id: str | None = None
    investigation_id: str | None = None
    pr_url: str | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    # dimensions.codeowners: {glob_or_surface: [emails]}
    # dimensions.busy / time_min / time_max for calendar window
    # dimensions.notify: {subject, body} overrides


class CoordinationPlan(BaseModel):
    risk_tier: str
    path: list[str]
    duration_minutes: int
    with_meet: bool
    notify_only: bool
    await_human: bool = True
    auto_merge: bool = False  # always false — PRD


class CoordinationResult(BaseModel):
    request_id: str
    plan: CoordinationPlan
    owners: list[Owner]
    slot: dict[str, Any] | None = None
    calendar: dict[str, Any] = Field(default_factory=dict)
    notifications: list[dict[str, Any]] = Field(default_factory=list)
    status: str  # awaiting_human | notified | scheduled | skipped
    detail: str = ""


# --- intelligence (generic policies, not payment-hardcoded) ------------------


def estimate_duration(req: CoordinationRequest) -> int:
    if req.duration_minutes is not None:
        return max(15, int(req.duration_minutes))
    # Surface hints can bump duration without special-casing one product.
    surface = (req.surface or "").lower()
    base = {"LOW": 15, "MEDIUM": 25, "HIGH": 20}[req.risk_tier]
    if any(k in surface for k in ("payment", "auth", "security", "billing")):
        base = max(base, 20)
    return base


def build_plan(req: CoordinationRequest) -> CoordinationPlan:
    duration = estimate_duration(req)
    with_meet = req.prefer_meet if req.prefer_meet is not None else req.risk_tier == "HIGH"
    if req.risk_tier == "LOW":
        path = ["identify_owners", "notify", "wait"]
        return CoordinationPlan(
            risk_tier=req.risk_tier,
            path=path,
            duration_minutes=duration,
            with_meet=False,
            notify_only=True,
            await_human=True,
            auto_merge=False,
        )
    if req.risk_tier == "MEDIUM":
        path = ["identify_owners", "check_calendar", "suggest_slot", "optional_hold", "notify", "wait"]
    else:
        path = [
            "identify_owners",
            "check_calendar",
            "suggest_slot",
            "schedule_review",
            "meet" if with_meet else "hold",
            "notify",
            "await_approval",
        ]
    return CoordinationPlan(
        risk_tier=req.risk_tier,
        path=path,
        duration_minutes=duration,
        with_meet=with_meet,
        notify_only=False,
        await_human=True,
        auto_merge=False,
    )


def resolve_owners(req: CoordinationRequest) -> list[Owner]:
    if req.owners:
        return [
            Owner(
                id=o.split("@")[0] if "@" in o else o,
                email=o if "@" in o else f"{o}@example.com",
                role="reviewer",
                source="explicit",
            )
            for o in req.owners
        ]

    mapping: dict[str, list[str]] = dict(req.dimensions.get("codeowners") or {})
    surface = (req.surface or req.kind or "").lower()
    matched: list[str] = []
    for key, emails in mapping.items():
        if key == "*" or key.lower() in surface or surface in key.lower():
            matched.extend(emails)
    if not matched and mapping:
        # Fall back to catch-all or first team
        matched = list(mapping.get("*") or next(iter(mapping.values()), []))
    if not matched:
        # Generic default — recipes should supply codeowners; infra stays honest
        matched = list(req.dimensions.get("default_owners") or ["eng-oncall@example.com"])

    seen: set[str] = set()
    out: list[Owner] = []
    for e in matched:
        if e in seen:
            continue
        seen.add(e)
        out.append(
            Owner(
                id=e.split("@")[0],
                email=e if "@" in e else f"{e}@example.com",
                role="codeowner",
                source="codeowners" if mapping else "default",
            )
        )
    return out


# --- notify adapters ---------------------------------------------------------


def _notify_gmail_draft(req: CoordinationRequest, owners: list[Owner], slot: dict | None, plan: CoordinationPlan) -> dict[str, Any]:
    from loop.connectors.mail import connected_email, draft, send, send_to_self

    # Prove third-party send stays denied
    denied = send("someone-else@example.com", "probe", "should fail").model_dump()
    me = connected_email()
    owners_line = ", ".join(o.email for o in owners) or "reviewers"
    n = dict(req.dimensions.get("notify") or {})
    subject = str(n.get("subject") or f"[LOOP] {req.title}")
    body_lines = [
        n.get("body")
        or (
            f"{req.subject or req.title}\n"
            f"Risk: {plan.risk_tier}. Duration ~{plan.duration_minutes}m.\n"
            f"PR: {req.pr_url or '(none)'}\n"
            f"Surface: {req.surface or '(general)'}\n"
        )
    ]
    if slot:
        body_lines.append(f"Proposed slot: {slot.get('start')} → {slot.get('end')} UTC")
    if plan.with_meet:
        body_lines.append("Meet link appears on the calendar event when create succeeds.")
    body_lines.append(f"\nIntended reviewers: {owners_line}")
    body_lines.append("This copy was sent only to your connected Gmail inbox.")
    text = "\n".join(str(x) for x in body_lines if x)

    report = send_to_self(subject, text)
    channel = "gmail"
    if report.status != "applied":
        report = draft(me or owners_line, subject, text)
        channel = "gmail_draft"

    out: dict[str, Any] = {
        "channel": channel,
        "report": report.model_dump(),
        "send_denied_third_party": denied,
        "to": me or owners_line,
        "subject": subject,
    }
    if getattr(report, "url", None):
        out["gmail_url"] = report.url
    return out



def _notify_chat(req: CoordinationRequest, owners: list[Owner], detail: str) -> dict[str, Any]:
    # No Chat API wired — honest skip with payload other agents can consume
    return {
        "channel": "chat",
        "report": {
            "status": "skipped",
            "connector": "chat.notify",
            "detail": "Google Chat connector not configured — room artifact carries the ask",
        },
        "to": [o.email for o in owners],
        "text": detail,
    }


def _notify_room(engine: Any, req: CoordinationRequest, artifact: dict[str, Any], text: str) -> dict[str, Any]:
    if not req.room_id or not engine:
        return {"channel": "room", "report": {"status": "skipped", "connector": "room.post", "detail": "no room_id"}}
    from loop.world import post

    post(
        engine,
        req.room_id,
        author="coordination_agent",
        author_kind="agent",
        kind="artifact",
        text=text,
        artifact_type="coordination",
        artifact=artifact,
    )
    return {"channel": "room", "report": {"status": "applied", "connector": "room.post", "detail": "coordination artifact posted"}}


# --- pipeline ----------------------------------------------------------------


def run_coordination(
    engine: Any | None,
    req: CoordinationRequest,
    *,
    apply_calendar: bool = True,
) -> dict[str, Any]:
    """Owners → calendar → schedule → notify. Never merges."""
    from loop.connectors import calendar as cal

    request_id = _id("coord")
    plan = build_plan(req)
    owners = resolve_owners(req)
    notifications: list[dict[str, Any]] = []
    slot: dict[str, Any] | None = None
    calendar_meta: dict[str, Any] = {"capabilities": cal.capabilities()}

    if not plan.notify_only:
        time_min = str(req.dimensions.get("time_min") or "")
        time_max = str(req.dimensions.get("time_max") or "")
        suggested = cal.suggest_times(
            duration_minutes=plan.duration_minutes,
            calendars=req.dimensions.get("calendars"),
            time_min=time_min,
            time_max=time_max,
        )
        calendar_meta["suggest"] = suggested
        if req.dimensions.get("forced_slot"):
            slot = dict(req.dimensions["forced_slot"])
        else:
            slots = suggested.get("slots") or []
            slot = slots[0] if slots else None

        if apply_calendar and slot and slot.get("start"):
            if plan.with_meet or req.risk_tier == "HIGH":
                report = cal.create_event(
                    req.title,
                    str(slot["start"]),
                    duration_minutes=plan.duration_minutes,
                    description=req.subject or req.title,
                    attendees=[o.email for o in owners],
                    with_meet=plan.with_meet,
                )
            else:
                report = cal.hold(req.title, str(slot["start"]), duration_minutes=plan.duration_minutes)
            calendar_meta["create"] = report.model_dump()
            if report.url:
                slot = {**slot, "event_url": report.url}
            from loop.receipts import calendar_proof, post_receipt

            post_receipt(
                engine,
                req.room_id,
                kind="workspace",
                title=req.title or "Calendar hold",
                agent="coordination_agent",
                status="done" if report.status == "applied" else ("failed" if report.status == "failed" else "done"),
                detail=str(report.detail or ""),
                open_url=str(report.url) if report.url else None,
                proof=calendar_proof(slot, report=report.model_dump()),
            )
        elif plan.notify_only is False:
            calendar_meta["create"] = {
                "status": "skipped",
                "connector": "calendar.create",
                "detail": "no free slot in window",
            }

    status = "notified" if plan.notify_only else ("scheduled" if slot else "awaiting_human")
    detail = (
        f"{plan.risk_tier}: "
        + (", ".join(o.email for o in owners) or "no owners")
        + (f" · slot {slot.get('start')}" if slot else " · no slot")
        + " · await human (never auto-merge)"
    )

    artifact = {
        "request_id": request_id,
        "kind": req.kind,
        "risk_tier": plan.risk_tier,
        "path": plan.path,
        "owners": [o.model_dump() for o in owners],
        "slot": slot,
        "calendar": calendar_meta,
        "pr_url": req.pr_url,
        "action_id": req.action_id,
        "auto_merge": False,
        "await_human": True,
    }

    for channel in req.notify_channels:
        if channel == "gmail_draft":
            notifications.append(_notify_gmail_draft(req, owners, slot, plan))
        elif channel == "chat":
            notifications.append(_notify_chat(req, owners, detail))

    for n in notifications:
        if n.get("channel") in {"gmail_draft", "gmail"}:
            url = n.get("gmail_url") or (n.get("report") or {}).get("url")
            if url:
                artifact["gmail_url"] = url

    if req.room_id and engine:
        notifications.append(_notify_room(engine, req, artifact, detail))
        # Dedicated mail receipt so the live board can pile a Verify / Mail card
        for n in notifications:
            if n.get("channel") not in {"gmail", "gmail_draft"}:
                continue
            rep = n.get("report") or {}
            to = n.get("to") or ""
            subj = n.get("subject") or req.title
            status = rep.get("status") or "skipped"
            if status == "applied" and n.get("channel") == "gmail":
                mail_text = f"Mail sent to {to}: {subj}"
                mail_type = "mail"
                badge_channel = "gmail"
            elif status == "applied":
                mail_text = f"Gmail draft ready: {subj}"
                mail_type = "mail"
                badge_channel = "gmail_draft"
            else:
                mail_text = f"Mail skipped ({rep.get('detail') or status}): {subj}"
                mail_type = "mail"
                badge_channel = n.get("channel")
            from loop.world import post as room_post

            room_post(
                engine,
                req.room_id,
                author="coordination_agent",
                author_kind="agent",
                kind="artifact",
                text=mail_text[:200],
                artifact_type=mail_type,
                artifact={
                    "channel": badge_channel,
                    "to": to,
                    "subject": subj,
                    "report": rep,
                    "gmail_url": n.get("gmail_url") or rep.get("url"),
                    "pr_url": req.pr_url,
                    "proof": {
                        "kind": "gmail",
                        "status": status,
                        "title": subj,
                        "subtitle": to,
                        "detail": rep.get("detail") or badge_channel,
                        "url": n.get("gmail_url") or rep.get("url"),
                        "console_url": n.get("gmail_url") or rep.get("url"),
                        "to": to,
                        "channel": badge_channel,
                    },
                },
            )
            break

    result = CoordinationResult(
        request_id=request_id,
        plan=plan,
        owners=owners,
        slot=slot,
        calendar=calendar_meta,
        notifications=notifications,
        status=status if notifications else "skipped",
        detail=detail,
    )

    # Persist a lightweight memory for other agents
    if engine is not None:
        engine.store.put_memory(
            request_id,
            "coordination",
            {
                "id": request_id,
                "kind": req.kind,
                "risk_tier": plan.risk_tier,
                "owners": [o.email for o in owners],
                "slot": slot,
                "status": result.status,
                "action_id": req.action_id,
                "investigation_id": req.investigation_id,
                "auto_merge": False,
            },
        )

    return {
        "coordination": result.model_dump(mode="json"),
        "risk_tier": plan.risk_tier,
        "pipeline": plan.path,
        "auto_merge": False,
    }


def coordinate_for_action(engine: Any, action_id: str, **overrides: Any) -> dict[str, Any]:
    """Bridge from a ProposedAction to coordination — risk from the action tier."""
    action = engine.store.get_action(action_id) if hasattr(engine.store, "get_action") else None
    if action is None:
        actions = [a for a in engine.store.list_actions() if a.id == action_id]
        action = actions[0] if actions else None
    if action is None:
        return {"error": "action not found", "action_id": action_id}

    inv = engine.store.get_investigation(action.investigation_id)
    room_id = inv.room_id if inv else None
    tier = action.risk_tier.value if isinstance(action.risk_tier, RiskTier) else str(action.risk_tier)
    arts = action.artifacts or {}
    req = CoordinationRequest(
        kind=str(overrides.get("kind") or "action_review"),
        title=str(overrides.get("title") or f"Review: {action.type}"),
        subject=action.consequence or action.type,
        surface=str(overrides.get("surface") or arts.get("surface") or action.type),
        risk_tier=tier if tier in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM",  # type: ignore[arg-type]
        owners=list(overrides.get("owners") or arts.get("codeowners") or []),
        duration_minutes=overrides.get("duration_minutes"),
        prefer_meet=overrides.get("prefer_meet"),
        room_id=room_id,
        action_id=action.id,
        investigation_id=action.investigation_id,
        pr_url=(arts.get("pr") or {}).get("url") if isinstance(arts.get("pr"), dict) else arts.get("pr_url"),
        dimensions=dict(overrides.get("dimensions") or arts.get("coordination") or {}),
        notify_channels=list(overrides.get("notify_channels") or ["gmail_draft", "room"]),
    )
    # Normalize codeowners list into map if needed
    if isinstance(req.dimensions.get("codeowners"), list) and not req.owners:
        req.owners = list(req.dimensions["codeowners"])
    apply_calendar = overrides.pop("apply_calendar", True)
    return run_coordination(engine, req, apply_calendar=apply_calendar)


# --- example recipes (payload only) ------------------------------------------


def example_low_risk_pr() -> CoordinationRequest:
    return CoordinationRequest(
        kind="review_request",
        title="Low-risk copy PR needs a look",
        subject="Docs/copy tweak on settings empty state",
        surface="copy",
        risk_tier="LOW",
        owners=["design-reviewer@acme.dev"],
        notify_channels=["gmail_draft", "room"],
        dimensions={
            "notify": {
                "subject": "[LOOP] Please review low-risk copy PR",
                "body": "Small copy change. Reply when done — no meeting needed.",
            }
        },
        pr_url="https://github.com/example/y/pull/42",
    )


def example_high_risk_payment_pr() -> CoordinationRequest:
    """Recipe: HIGH payment surface — calendar + Meet + await approval. Still not auto-merge."""
    return CoordinationRequest(
        kind="review_request",
        title="HIGH payment PR — schedule review",
        subject="Flag rollback on pay path — needs payment owner + live review",
        surface="payment authorization",
        risk_tier="HIGH",
        prefer_meet=True,
        duration_minutes=20,
        notify_channels=["gmail_draft", "chat", "room"],
        pr_url="https://github.com/example/y/pull/99",
        dimensions={
            "codeowners": {
                "payment": ["payments-owner@acme.dev", "eng-manager@acme.dev"],
                "android": ["android-payments@acme.dev"],
                "*": ["eng-oncall@acme.dev"],
            },
            "forced_slot": {
                "start": "2026-08-29T16:00:00Z",
                "end": "2026-08-29T16:20:00Z",
                "duration_minutes": 20,
            },
            "notify": {
                "subject": "[LOOP] HIGH: payment review in 20m",
                "body": "Payment-surface PR. Calendar + Meet. Human approval required. OS will not merge.",
            },
        },
    )
