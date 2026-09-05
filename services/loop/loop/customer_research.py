"""Customer research infrastructure — events → probes → brief → call → structured evidence.

Not a single hardcoded loop. Recipes (e.g. checkout abandon) supply an event +
memory conditions; the pipeline and agent interplay stay generic.

Telephony:
  - Google Telephony Platform / CX Phone Gateway: **inbound only** (PRD K-6).
  - Outbound to an ADK/Live agent is not a Google product — Twilio/LiveKit are
    what Google documents for dial-out. We keep outbound as an optional adapter.
  - Default without a carrier: simulated research dialogue (still produces
    structured evidence the fleet can consume).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from loop.models import (
    Classification,
    Direction,
    InvestigationState,
    LoopType,
    PathKind,
    Room,
    RoomKind,
    Segment,
    Signal,
    SignalFamily,
    SignalStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- schemas -----------------------------------------------------------------


class ResearchEvent(BaseModel):
    """Something observed about a user that may warrant investigation + voice."""

    kind: str
    user_id: str
    title: str = ""
    topic: str = ""
    phone: str = ""
    metric: str = "customer_research"
    funnel_position: str = "product"
    dimensions: dict[str, Any] = Field(default_factory=dict)
    memory_conditions: list[str] = Field(default_factory=list)
    loop_type: LoopType = LoopType.TYPE_A
    path: PathKind = PathKind.BUG
    room_kind: RoomKind = RoomKind.RESEARCH


class SourceResult(BaseModel):
    source: str
    agent: str
    claim: str
    detail: dict[str, Any] = Field(default_factory=dict)


class CustomerContextBrief(BaseModel):
    title: str = "Customer Context Brief"
    user_id: str
    event_kind: str
    acquisition: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    app_version: str | None = None
    journey: list[str] = Field(default_factory=list)
    observed: dict[str, Any] = Field(default_factory=dict)
    technical: dict[str, Any] = Field(default_factory=dict)
    previous_behavior: dict[str, Any] = Field(default_factory=dict)
    memory_applied: dict[str, Any] = Field(default_factory=dict)
    hypothesis: dict[str, Any] = Field(default_factory=dict)
    call_plan: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceResult] = Field(default_factory=list)
    confidence: float = 0.5
    raw: dict[str, Any] = Field(default_factory=dict)


class StructuredCallEvidence(BaseModel):
    reason: str
    severity: str
    purchase_intent: str
    friction: str
    competitor_mentioned: bool = False
    feature_request: str | None = None
    willing_to_retry: bool = True
    confidence: float = 0.7
    extras: dict[str, Any] = Field(default_factory=dict)


# --- source probes (pluggable) -----------------------------------------------

ProbeFn = Callable[[ResearchEvent], SourceResult]


def _probe_user(event: ResearchEvent) -> SourceResult:
    return SourceResult(
        source="User ID",
        agent="orchestrator",
        claim=f"Subject user {event.user_id}",
        detail={"user_id": event.user_id, **{k: v for k, v in event.dimensions.items() if k.startswith("user_")}},
    )


def _probe_ga4(event: ResearchEvent) -> SourceResult:
    events = event.dimensions.get("ga4_events") or event.dimensions.get("events") or []
    missing = event.dimensions.get("ga4_missing") or []
    return SourceResult(
        source="GA4 events",
        agent="analytics_agent",
        claim=event.dimensions.get("ga4_claim")
        or (f"events={events}; missing={missing}" if events else "GA4 session inspected"),
        detail={"events": events, "missing": missing},
    )


def _probe_ads(event: ResearchEvent) -> SourceResult:
    acq = event.dimensions.get("acquisition") or {}
    return SourceResult(
        source="Google Ads campaign",
        agent="analytics_agent",
        claim=event.dimensions.get("ads_claim")
        or f"Acquisition = {acq.get('channel', 'unknown')} / {acq.get('campaign', 'unknown')}",
        detail=dict(acq) if isinstance(acq, dict) else {"raw": acq},
    )


def _probe_device(event: ResearchEvent) -> SourceResult:
    device = event.dimensions.get("device") or {}
    return SourceResult(
        source="device",
        agent="logs_agent",
        claim=event.dimensions.get("device_claim")
        or f"{device.get('model', 'unknown')} · {device.get('os', '')}".strip(" ·"),
        detail=dict(device) if isinstance(device, dict) else {},
    )


def _probe_app_version(event: ResearchEvent) -> SourceResult:
    ver = event.dimensions.get("app_version") or event.dimensions.get("version")
    return SourceResult(
        source="app version",
        agent="deployment_agent",
        claim=event.dimensions.get("app_version_claim") or f"App version {ver or 'unknown'}",
        detail={"app_version": ver, "pay_sdk": event.dimensions.get("pay_sdk")},
    )


def _probe_session(event: ResearchEvent) -> SourceResult:
    journey = event.dimensions.get("journey") or []
    return SourceResult(
        source="session events",
        agent="analytics_agent",
        claim=event.dimensions.get("session_claim")
        or (" → ".join(str(j) for j in journey) if journey else "session path inspected"),
        detail={
            "journey": journey,
            "returned": event.dimensions.get("returned"),
            "days_since_event": event.dimensions.get("days_since_event"),
        },
    )


def _probe_payments(event: ResearchEvent) -> SourceResult:
    tech = event.dimensions.get("technical") or {}
    return SourceResult(
        source="payment logs",
        agent="logs_agent",
        claim=event.dimensions.get("payment_claim")
        or f"retries={tech.get('api_retries', '?')} timeout={tech.get('payment_timeout', '?')}",
        detail=dict(tech) if isinstance(tech, dict) else {},
    )


def _probe_crashes(event: ResearchEvent) -> SourceResult:
    tech = event.dimensions.get("technical") or {}
    crashes = tech.get("crash", tech.get("crashes", 0))
    return SourceResult(
        source="crash reports",
        agent="logs_agent",
        claim="No crash in session window" if not crashes else f"Crashes observed: {crashes}",
        detail={"crashes": crashes},
    )


def _probe_support(event: ResearchEvent) -> SourceResult:
    prev = event.dimensions.get("previous_behavior") or {}
    return SourceResult(
        source="previous support interactions",
        agent="customer_voice_agent",
        claim=event.dimensions.get("support_claim")
        or f"prior_purchases={prev.get('successful_purchases', prev.get('prior_purchases', '?'))}",
        detail=dict(prev) if isinstance(prev, dict) else {},
    )


DEFAULT_PROBES: list[ProbeFn] = [
    _probe_user,
    _probe_ga4,
    _probe_ads,
    _probe_device,
    _probe_app_version,
    _probe_session,
    _probe_payments,
    _probe_crashes,
    _probe_support,
]


def run_probes(event: ResearchEvent, probes: list[ProbeFn] | None = None) -> list[SourceResult]:
    return [fn(event) for fn in (probes or DEFAULT_PROBES)]


# --- brief / call plan / evidence --------------------------------------------


def match_memory(store: Any, conditions: list[str]) -> list[dict[str, Any]]:
    """Pull organizational lessons whose applicable_conditions overlap the event."""
    if not conditions:
        return []
    hits: list[dict[str, Any]] = []
    want = set(conditions)
    for lesson in store.list_lessons():
        have = set(lesson.applicable_conditions or [])
        if want & have:
            hits.append(
                {
                    "id": lesson.id,
                    "statement": lesson.statement,
                    "root_cause_family": lesson.root_cause_family,
                    "applicable_conditions": lesson.applicable_conditions,
                    "confidence": lesson.confidence,
                }
            )
    return hits


def build_brief(
    event: ResearchEvent,
    sources: list[SourceResult],
    memory_hits: list[dict[str, Any]],
) -> CustomerContextBrief:
    dims = event.dimensions
    hyp = dims.get("hypothesis") or {
        "statement": dims.get("hypothesis_statement")
        or "User hit friction in the journey; purchase intent may still be high.",
        "confidence": float(dims.get("hypothesis_confidence") or 0.7),
    }
    questions = dims.get("call_questions") or [
        "When you tried to continue, did you see an error, or did the screen keep loading?",
        "Did you try again?",
        "Did you eventually finish what you started?",
    ]
    opening = dims.get("call_opening") or (
        f"Hi, this is Lexi from the product team. We noticed something on your recent "
        f"{event.funnel_position} session — do you have thirty seconds?"
    )
    memory_applied = {
        "lessons": memory_hits,
        "implication": dims.get("memory_implication")
        or (memory_hits[0]["statement"] if memory_hits else "No matching lesson — proceed on fresh evidence."),
    }
    if "returned" in dims:
        memory_applied["returned"] = dims.get("returned")
    if "days_since_event" in dims:
        memory_applied["days_since_event"] = dims.get("days_since_event")
    if "expect_return_within_days" in dims:
        memory_applied["expect_return_within_days"] = dims.get("expect_return_within_days")

    return CustomerContextBrief(
        user_id=event.user_id,
        event_kind=event.kind,
        acquisition=dims.get("acquisition") or {},
        device=dims.get("device") or {},
        app_version=dims.get("app_version") or dims.get("version"),
        journey=list(dims.get("journey") or []),
        observed=dims.get("observed") or {},
        technical=dims.get("technical") or {},
        previous_behavior=dims.get("previous_behavior") or {},
        memory_applied=memory_applied,
        hypothesis=hyp if isinstance(hyp, dict) else {"statement": str(hyp), "confidence": 0.7},
        call_plan={"goal": dims.get("call_goal") or "Diagnostic research", "opening": opening, "questions": questions},
        sources=sources,
        confidence=float((hyp if isinstance(hyp, dict) else {}).get("confidence") or 0.7),
        raw={"dimensions": dims},
    )


def call_system_prompt(brief: CustomerContextBrief | dict[str, Any]) -> str:
    b = brief if isinstance(brief, CustomerContextBrief) else CustomerContextBrief.model_validate(brief)
    hyp = (b.hypothesis or {}).get("statement") or "friction in the journey"
    tech = b.technical or {}
    return (
        f"You are Lexi doing targeted customer research — not a survey. "
        f"Event={b.event_kind}. User={b.user_id}. Device={b.device}. App={b.app_version}. "
        f"Technical={tech}. Hypothesis: {hyp}. "
        f"Ask one short diagnostic question at a time from the call plan. "
        f"Never offer discounts. Never invent facts."
    )


DEFAULT_DIAGNOSTIC_QUESTIONS = [
    "When you tried to continue, did you see an error message, or did the screen keep loading?",
    "Did you try again on the same device?",
    "Have you completed this successfully before on another browser or app?",
]

DEFAULT_DEMO_REPLIES = [
    "Sure, go ahead.",
    "It kept loading. My card was not being detected.",
    "Yes, twice.",
    "No, I gave up.",
]


def resolve_diagnostic_plan(
    brief: CustomerContextBrief | dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    """Opening, adaptive questions, and demo replies for simulated / text-fallback calls."""
    b = brief if isinstance(brief, CustomerContextBrief) else CustomerContextBrief.model_validate(brief)
    plan = b.call_plan or {}
    opening = str(plan.get("opening") or "Hi — quick question about your recent session.")
    dims = (b.raw or {}).get("dimensions") or {}
    voice_sub = dims.get("voice_subject") if isinstance(dims.get("voice_subject"), dict) else {}

    questions = list(plan.get("questions") or [])
    if not questions:
        questions = list(plan.get("adaptive_questions") or [])
    if not questions:
        questions = list(voice_sub.get("adaptive_questions") or [])
    if not questions and isinstance(brief, dict):
        questions = list(brief.get("adaptive_questions") or [])
    if not questions:
        questions = list(DEFAULT_DIAGNOSTIC_QUESTIONS)
        device = str(
            voice_sub.get("device")
            or (b.device.get("label") if isinstance(b.device, dict) else b.device)
            or dims.get("device")
            or ""
        ).strip()
        if device and not any(device.lower() in q.lower() for q in questions):
            questions = [*questions, f"Were you on {device} the whole time?"]

    if opening == "Hi — quick question about your recent session." and voice_sub.get("opening"):
        opening = str(voice_sub["opening"])

    replies = list(dims.get("demo_replies") or voice_sub.get("demo_replies") or [])
    if not replies:
        replies = list(DEFAULT_DEMO_REPLIES)
    return opening, questions, replies


def _otp_metric_class(metric: str) -> bool:
    m = (metric or "").lower()
    return "otp" in m and any(w in m for w in ("verify", "hang", "timeout", "code"))


def extract_structured_evidence(
    transcript: list[dict[str, str]],
    *,
    metric: str = "",
) -> StructuredCallEvidence:
    text = " ".join(f"{t.get('role')}: {t.get('message')}" for t in transcript).lower()
    ctx = f"{text} {(metric or '').lower()}"
    otp_metric = _otp_metric_class(metric)
    loading = any(w in text for w in ("loading", "spinner", "kept loading", "hung", "timeout"))
    error_shown = any(w in text for w in ("error", "declined", "invalid card"))
    card_detect = "card" in text and any(w in text for w in ("detect", "not being", "wasn't", "wasnt"))
    tried_again = any(w in text for w in ("twice", "again", "retr"))
    gave_up = any(w in text for w in ("gave up", "gaveup", "i gave"))
    otpish = any(w in ctx for w in ("otp", "verify", "2fa", "two-factor", "two factor", "code"))
    if otp_metric:
        # Signal class wins — never label otp_verify_* hangs as payment_timeout.
        reason = "otp_verify_timeout"
    elif loading or card_detect:
        if otpish and loading:
            reason = "otp_verify_timeout"
        elif loading:
            reason = "payment_timeout"
        else:
            reason = "card_not_detected"
    elif error_shown:
        reason = "payment_error"
    else:
        reason = "unknown_friction"
    return StructuredCallEvidence(
        reason=reason,
        severity="high" if gave_up or loading else "medium",
        purchase_intent="high",
        friction="technical",
        competitor_mentioned=any(w in text for w in ("amazon", "shopify", "competitor")),
        feature_request=None,
        willing_to_retry=True,
        confidence=0.94 if (loading or card_detect) and tried_again and gave_up else 0.7,
        extras={
            "card_not_detected": card_detect,
            "retries_confirmed": tried_again,
            "completed_purchase": False if gave_up else None,
        },
    )


def simulate_research_dialogue(brief: CustomerContextBrief | dict[str, Any]) -> list[dict[str, str]]:
    """Deterministic dialogue for demos without a carrier."""
    opening, q, replies = resolve_diagnostic_plan(brief)
    turns: list[dict[str, str]] = [{"role": "agent", "message": opening}, {"role": "user", "message": replies[0]}]
    for i, question in enumerate(q[:3]):
        turns.append({"role": "agent", "message": question})
        turns.append({"role": "user", "message": replies[min(i + 1, len(replies) - 1)]})
    turns.append(
        {
            "role": "agent",
            "message": "Thanks — that helps. We will take it from here. Have a good one.",
        }
    )
    return turns


# --- telephony adapters ------------------------------------------------------


def telephony_capabilities() -> dict[str, Any]:
    import os

    twilio = bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_FROM_NUMBER")
    )
    google_inbound = bool(os.environ.get("LOOP_GTP_PHONE_NUMBER") or os.environ.get("LOOP_CX_PHONE_NUMBER"))
    gemini = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_CLOUD_PROJECT"))
    return {
        "google_telephony": {
            "inbound": google_inbound,
            "outbound": False,
            "detail": (
                "Google Telephony Platform / CX Phone Gateway handle incoming traffic only. "
                "No Google product originates outbound PSTN to an ADK/Live agent (PRD K-6)."
            ),
            "number": os.environ.get("LOOP_GTP_PHONE_NUMBER") or os.environ.get("LOOP_CX_PHONE_NUMBER") or None,
        },
        "twilio_outbound": twilio,
        "gemini": gemini,
        "default_mode": (
            "twilio_outbound"
            if twilio
            else ("google_inbound_callback" if google_inbound else "simulated")
        ),
    }


# --- pipeline ----------------------------------------------------------------


def run_customer_research(
    engine: Any,
    event: ResearchEvent,
    *,
    probes: list[ProbeFn] | None = None,
    place_real_call: bool = False,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Generic agent interplay: memory → probe fan-out → brief → call → structured evidence."""
    from loop.world import post

    scenario = scenario_id or f"research:{event.kind}"
    tid = str(event.dimensions.get("tenant_id") or "")
    tenant = engine.store.get_tenant(tid) if tid else None
    if tenant:
        from loop.connectors.bigquery import enrich_research_dimensions

        event = event.model_copy(
            update={"dimensions": enrich_research_dimensions(engine.store, tenant, dict(event.dimensions))}
        )
    sources = run_probes(event, probes)
    memory_hits = match_memory(engine.store, event.memory_conditions)
    brief = build_brief(event, sources, memory_hits)

    existing = next((r for r in engine.store.list_rooms() if r.scenario_id == scenario), None)
    if existing:
        room = existing
        inv = engine.store.get_investigation(room.investigation_id) if room.investigation_id else None
    else:
        sig = Signal(
            id=f"sig_research_{uuid4().hex[:8]}",
            family=SignalFamily.CUSTOMER,
            direction=Direction.NEGATIVE if event.loop_type == LoopType.TYPE_A else Direction.POSITIVE,
            funnel_position=event.funnel_position,
            metric=event.metric,
            magnitude=-1.0 if event.loop_type == LoopType.TYPE_A else 0.2,
            baseline=0.0,
            affected_segments=[Segment(channel="tenant", app_version=str(event.dimensions.get("app_version") or ""))],
            detection_window={"kind": event.kind},
            confidence=brief.confidence,
            source=f"research.{event.kind}",
            status=SignalStatus.OPEN,
            detected_at=_now(),
        )
        engine.store.put_signal(sig)
        inv = engine.open_investigation(sig)
        assert inv
        inv.scenario_id = scenario
        inv.recalled_lessons = [h["statement"] for h in memory_hits]
        inv.state = InvestigationState.GATHERING
        inv.loop_type = event.loop_type
        room = Room(
            id=f"room_research_{uuid4().hex[:8]}",
            kind=event.room_kind,
            title=event.title or f"{event.kind} · user {event.user_id}",
            topic=event.topic or f"Research event {event.kind}",
            status="open",
            created_at=_now(),
            members=[
                "orchestrator",
                "investigator_agent",
                "analytics_agent",
                "logs_agent",
                "deployment_agent",
                "customer_voice_agent",
                "learning_agent",
                "outreach_caller",
                "you",
            ],
            scenario_id=scenario,
            loop_type=event.loop_type,
            path=event.path,
            investigation_id=inv.id,
        )
        inv.room_id = room.id
        inv.title = room.title
        engine.store.put_investigation(inv)
        engine.store.put_room(room)
        post(
            engine,
            room.id,
            author="signal_agent",
            author_kind="agent",
            kind="artifact",
            text=event.title or f"{event.kind} · {event.user_id}",
            artifact_type="signal",
            artifact=sig.model_dump(mode="json"),
        )

    assert inv is not None
    inv.recalled_lessons = [h["statement"] for h in memory_hits]
    inv.state = InvestigationState.GATHERING
    engine.store.put_investigation(inv)

    if memory_hits:
        post(
            engine,
            room.id,
            author="learning_agent",
            author_kind="agent",
            kind="artifact",
            text=memory_hits[0]["statement"],
            artifact_type="memory",
            artifact={"lessons": memory_hits, **brief.memory_applied},
        )

    post(
        engine,
        room.id,
        author="orchestrator",
        author_kind="agent",
        kind="chat",
        text=f"Opening research on {event.kind} for user {event.user_id}. Fan-out probes, then diagnostic voice.",
    )

    for src in sources:
        post(
            engine,
            room.id,
            author=src.agent,
            author_kind="agent",
            kind="artifact",
            text=f"{src.source} → {src.claim}",
            artifact_type="evidence",
            artifact={"source": src.source, "claim": src.claim, **src.detail},
        )

    brief_payload = brief.model_dump(mode="json")
    post(
        engine,
        room.id,
        author="evidence_agent",
        author_kind="agent",
        kind="artifact",
        text=(brief.hypothesis or {}).get("statement") or brief.title,
        artifact_type="customer_brief",
        artifact=brief_payload,
    )
    post(
        engine,
        room.id,
        author="root_cause_agent",
        author_kind="agent",
        kind="artifact",
        text=(brief.hypothesis or {}).get("statement") or "Hypothesis pending",
        artifact_type="hypothesis",
        artifact={
            "statement": (brief.hypothesis or {}).get("statement"),
            "classification": Classification.BUG.value
            if event.path == PathKind.BUG
            else Classification.OPPORTUNITY.value,
            "confidence": brief.confidence,
        },
    )

    caps = telephony_capabilities()
    transcript: list[dict[str, str]] = []
    evidence: StructuredCallEvidence | None = None
    call_report: dict[str, Any]

    if place_real_call and event.phone and caps["twilio_outbound"]:
        from loop.connectors.voice import place_call

        product = str(
            event.dimensions.get("product")
            or event.dimensions.get("product_name")
            or "Product"
        )
        report = place_call(
            f"tok_user_{event.user_id}",
            (brief.hypothesis or {}).get("statement") or event.kind,
            to_number=event.phone,
            room_id=room.id,
            product=product,
            brief=brief_payload,
            system_prompt=call_system_prompt(brief),
        )
        call_report = report.model_dump()
        post(
            engine,
            room.id,
            author="outreach_caller",
            author_kind="agent",
            kind="artifact",
            text=report.detail,
            artifact_type="call",
            artifact={**call_report, "backend": "twilio_outbound"},
        )
    elif caps["google_telephony"]["inbound"] and not place_real_call:
        # Google-native path: request inbound callback to GTP number (no dial-out).
        number = caps["google_telephony"]["number"]
        call_report = {
            "status": "callback_requested",
            "connector": "voice.google_inbound",
            "detail": (
                f"Google Telephony is inbound-only. Ask the customer to call {number} "
                f"(or wait for them to return the miss). Brief is loaded for that session."
            ),
            "url": number,
        }
        post(
            engine,
            room.id,
            author="outreach_caller",
            author_kind="agent",
            kind="artifact",
            text=call_report["detail"],
            artifact_type="call",
            artifact={**call_report, "brief_user_id": event.user_id, "backend": "google_inbound"},
        )
        # Still run simulated dialogue so the fleet gets structured evidence in demos.
        transcript = simulate_research_dialogue(brief)
        evidence = extract_structured_evidence(transcript, metric=str(getattr(event, "metric", "") or ""))
    else:
        transcript = simulate_research_dialogue(brief)
        evidence = extract_structured_evidence(transcript, metric=str(getattr(event, "metric", "") or ""))
        call_report = {
            "status": "simulated",
            "connector": "voice.research",
            "detail": (
                "Simulated research call. Google GTP cannot dial out; set Twilio for PSTN outbound, "
                "or LOOP_GTP_PHONE_NUMBER for inbound callback."
            ),
            "backend": caps["default_mode"],
        }
        post(
            engine,
            room.id,
            author="outreach_caller",
            author_kind="agent",
            kind="chat",
            text="Diagnostic call with the brief loaded — not a survey.",
        )

    if transcript and evidence:
        for turn in transcript:
            post(
                engine,
                room.id,
                author="outreach_caller" if turn["role"] == "agent" else f"user_{event.user_id}",
                author_kind="agent" if turn["role"] == "agent" else "human",
                kind="chat",
                text=turn["message"],
            )
        ev = evidence.model_dump(mode="json")
        post(
            engine,
            room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text=(
                f"Structured evidence · {evidence.reason} · intent={evidence.purchase_intent} "
                f"· friction={evidence.friction} · confidence={evidence.confidence}"
            ),
            artifact_type="call_evidence",
            artifact={"structured": ev, "transcript": transcript, "event_kind": event.kind},
        )
        inv.state = InvestigationState.HYPOTHESIS
        engine.store.put_investigation(inv)
        post(
            engine,
            room.id,
            author="code_agent",
            author_kind="agent",
            kind="chat",
            text="Fleet can consume structured evidence for the next gate (fix / experiment / learn).",
        )

    return {
        "scenario": scenario,
        "event": event.model_dump(mode="json"),
        "room_id": room.id,
        "investigation_id": inv.id,
        "brief": brief_payload,
        "call": call_report,
        "transcript": transcript,
        "structured": evidence.model_dump(mode="json") if evidence else None,
        "telephony": caps,
    }
