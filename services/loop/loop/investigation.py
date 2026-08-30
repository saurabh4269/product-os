"""Investigation infrastructure — broad signals → parallel probes → evidence → hypothesis → briefs.

Not a Safari/payment special case. Recipes supply AnomalyEvent / feature mentions;
the pipeline stays generic:

  Signal catalog (funnel · technical · business · customer)
       ↓
  Parallel investigators (analytics · logs · deploy · db · customer · code)
       ↓
  Evidence Agent (aggregate + confidence + correlation)
       ↓
  Root-cause hypothesis (≥3 independence groups)
       ↓
  Voice diagnostic context  |  Code issue brief  |  Risk policy
       ↓
  (optional) Product intelligence: N requests → one proposal (not N issues)

ADK 2 alignment: fan-out/join shape matches workflows.investigation_fanout.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from loop.models import (
    Classification,
    Direction,
    InvestigationState,
    LoopType,
    PathKind,
    RiskTier,
    Room,
    RoomKind,
    Segment,
    Signal,
    SignalFamily,
    SignalStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


# --- signal catalog (what Signal Agent can watch) -----------------------------

SIGNAL_CATALOG: dict[str, list[dict[str, str]]] = {
    "funnel": [
        {"id": "signup", "metric": "signup_rate", "label": "Signup"},
        {"id": "onboarding", "metric": "onboarding_completion", "label": "Onboarding"},
        {"id": "activation", "metric": "activation_rate", "label": "Activation"},
        {"id": "checkout", "metric": "checkout_start", "label": "Checkout"},
        {"id": "payment", "metric": "payment_success", "label": "Payment"},
        {"id": "retention", "metric": "d7_retention", "label": "Retention"},
        {"id": "payment_abandoned", "metric": "payment_abandon", "label": "Payment abandoned"},
    ],
    "technical": [
        {"id": "http_5xx", "metric": "http_5xx_rate", "label": "HTTP 5xx spikes"},
        {"id": "latency", "metric": "p95_latency_ms", "label": "Latency"},
        {"id": "error_rate", "metric": "error_rate", "label": "Error rates"},
        {"id": "api_failures", "metric": "api_fail_rate", "label": "Failed API calls"},
        {"id": "deploy_change", "metric": "deploy_event", "label": "Deployment changes"},
        {"id": "crashes", "metric": "crash_rate", "label": "Crash logs"},
        {"id": "db_errors", "metric": "db_error_rate", "label": "Database errors"},
    ],
    "business": [
        {"id": "conversion_drop", "metric": "purchase_conversion", "label": "Conversion drop"},
        {"id": "revenue_drop", "metric": "revenue", "label": "Revenue drop"},
        {"id": "churn_spike", "metric": "churn_rate", "label": "Churn spike"},
        {"id": "refunds", "metric": "refund_rate", "label": "Refund increase"},
        {"id": "feature_abandon", "metric": "feature_abandon_rate", "label": "Feature abandonment"},
        {"id": "geo_anomaly", "metric": "conversion_by_geo", "label": "Geographic anomalies"},
        {"id": "device_anomaly", "metric": "conversion_by_device", "label": "Device/browser anomalies"},
    ],
    "customer": [
        {"id": "support_tickets", "metric": "ticket_volume", "label": "Support tickets"},
        {"id": "app_reviews", "metric": "review_score", "label": "App reviews"},
        {"id": "chat", "metric": "chat_friction_mentions", "label": "Chat conversations"},
        {"id": "nps", "metric": "nps", "label": "NPS/CSAT"},
        {"id": "surveys", "metric": "survey_friction", "label": "Survey responses"},
        {"id": "phone_feedback", "metric": "voice_friction", "label": "Phone feedback"},
        {"id": "feature_request", "metric": "feature_request", "label": "Feature requests"},
    ],
}


def catalog() -> dict[str, Any]:
    return {
        "families": SIGNAL_CATALOG,
        "investigators": [i["id"] for i in INVESTIGATOR_SPECS],
        "pipeline": [
            "detect",
            "fan_out",
            "evidence_aggregate",
            "hypothesis",
            "voice_context",
            "code_brief",
            "risk",
            "propose",
        ],
    }


# --- schemas -----------------------------------------------------------------


class AnomalyEvent(BaseModel):
    """Something anomalous — any catalog metric / family. Recipes fill dimensions."""

    kind: str
    metric: str
    title: str = ""
    family: Literal["funnel", "technical", "business", "customer"] = "business"
    magnitude: float = 0.0
    baseline: float = 0.0
    funnel_position: str = "product"
    confidence: float = 0.8
    source: str = "signal_agent"
    polarity: Literal["negative", "positive"] | None = None
    loop_type: LoopType | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    # dimensions.probes: {analytics_agent: {claim, ...}, ...}
    # dimensions.segments: {browser, device, geo, ...}
    # dimensions.deploy: {service, version, minutes_ago}
    # dimensions.voice_subject: {name, amount, device, failure, attempts, known_issue}
    # dimensions.code: {files, expected_behavior, regression_scenario}
    # dimensions.hypothesis: {statement}
    # dimensions.correlation: template fields
    memory_conditions: list[str] = Field(default_factory=list)


class InvestigatorClaim(BaseModel):
    agent: str
    source_type: str
    independence_group: str
    claim: str
    detail: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.8


class EvidencePack(BaseModel):
    claims: list[InvestigatorClaim]
    independence_groups: list[str]
    confidence: float
    correlation_summary: str
    checklist: dict[str, bool] = Field(default_factory=dict)


class VoiceDiagnosticContext(BaseModel):
    """Context the Customer Voice Agent receives before an adaptive diagnostic call."""

    user_label: str = "customer"
    attempt_summary: str = ""
    device: str = ""
    failure: str = ""
    previous_attempts: int = 0
    known_issue: str = ""
    hypothesis_hint: str = ""
    opening: str = ""
    adaptive_questions: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class CodeIssueBrief(BaseModel):
    """What Code Agent gets — not 'fix payment bug'."""

    issue: str
    evidence_summary: list[str] = Field(default_factory=list)
    likely_files: list[str] = Field(default_factory=list)
    expected_behavior: str = ""
    regression_test: str = ""
    surface: str = ""
    hypothesis: str = ""
    confidence: float = 0.0


class RiskDecision(BaseModel):
    tier: RiskTier
    auto_test_pr: bool
    developer_approval: bool
    human_approval: bool
    rationale: str
    surface: str


class FeatureMention(BaseModel):
    text: str
    user_id: str = ""
    channel: str = "voice"  # voice | review | chat | survey | ticket
    revenue_hint_usd: float | None = None


class FeatureCluster(BaseModel):
    theme: str
    frequency: int
    revenue_affected_usd: float = 0.0
    churn_risk: Literal["low", "medium", "high"] = "medium"
    competitor_capability: bool = False
    implementation_estimate: Literal["low", "medium", "high"] = "medium"
    sample_quotes: list[str] = Field(default_factory=list)
    mention_ids: list[str] = Field(default_factory=list)


class ProductProposal(BaseModel):
    title: str
    cluster: FeatureCluster
    recommendation: str
    next_step: str = "pm_approval_then_github_issue"


# --- investigators (parallel fan-out) ----------------------------------------

InvestigatorFn = Callable[[AnomalyEvent], InvestigatorClaim | None]

INVESTIGATOR_SPECS: list[dict[str, str]] = [
    {"id": "analytics_agent", "source_type": "analytics", "group": "analytics"},
    {"id": "logs_agent", "source_type": "logs", "group": "logs"},
    {"id": "deployment_agent", "source_type": "deployment", "group": "deploys"},
    {"id": "database_agent", "source_type": "database", "group": "database"},
    {"id": "customer_voice_agent", "source_type": "customer_voice", "group": "customer_voice"},
    {"id": "code_agent", "source_type": "code", "group": "code"},
]


def _probe_from_dims(event: AnomalyEvent, agent: str, source_type: str, group: str) -> InvestigatorClaim | None:
    probes = event.dimensions.get("probes") or {}
    raw = probes.get(agent) or probes.get(source_type)
    if isinstance(raw, dict) and raw.get("claim"):
        return InvestigatorClaim(
            agent=agent,
            source_type=source_type,
            independence_group=str(raw.get("independence_group") or group),
            claim=str(raw["claim"]),
            detail={k: v for k, v in raw.items() if k != "claim"},
            confidence=float(raw.get("confidence") or 0.85),
        )
    return None


def _default_analytics(event: AnomalyEvent) -> InvestigatorClaim:
    seg = event.dimensions.get("segments") or {}
    claim = event.dimensions.get("analytics_claim") or (
        f"{event.metric} at {event.magnitude} (baseline {event.baseline})"
        + (f" · segment={seg}" if seg else "")
    )
    return InvestigatorClaim(
        agent="analytics_agent",
        source_type="analytics",
        independence_group="analytics",
        claim=str(claim),
        detail={"metric": event.metric, "magnitude": event.magnitude, "baseline": event.baseline, "segments": seg},
        confidence=0.88,
    )


def _default_logs(event: AnomalyEvent) -> InvestigatorClaim:
    claim = event.dimensions.get("logs_claim") or (
        f"Error/timeout cluster near {event.funnel_position} aligned with {event.metric} movement."
    )
    return InvestigatorClaim(
        agent="logs_agent",
        source_type="logs",
        independence_group="logs",
        claim=str(claim),
        detail=dict(event.dimensions.get("logs") or {}),
        confidence=0.84,
    )


def _default_deploy(event: AnomalyEvent) -> InvestigatorClaim:
    dep = dict(event.dimensions.get("deploy") or {})
    claim = event.dimensions.get("deploy_claim") or (
        f"Deploy {dep.get('service', 'app')} {dep.get('version', '?')} "
        f"{dep.get('minutes_ago', '?')} min before anomaly onset."
        if dep
        else f"No deploy correlation declared for {event.kind}."
    )
    return InvestigatorClaim(
        agent="deployment_agent",
        source_type="deployment",
        independence_group="deploys",
        claim=str(claim),
        detail=dep,
        confidence=0.9 if dep else 0.55,
    )


def _default_database(event: AnomalyEvent) -> InvestigatorClaim:
    claim = event.dimensions.get("database_claim") or (
        "DB error rate flat in window — not primary suspect."
        if not event.dimensions.get("database")
        else str((event.dimensions.get("database") or {}).get("claim") or "Database anomalies in window.")
    )
    return InvestigatorClaim(
        agent="database_agent",
        source_type="database",
        independence_group="database",
        claim=str(claim),
        detail=dict(event.dimensions.get("database") or {}),
        confidence=0.8,
    )


def _default_customer(event: AnomalyEvent) -> InvestigatorClaim:
    voice = event.dimensions.get("voice_subject") or {}
    claim = event.dimensions.get("customer_claim") or (
        f"Customer reports friction: {voice.get('failure') or event.kind}."
        if voice
        else f"Customer channels mention friction around {event.funnel_position}."
    )
    return InvestigatorClaim(
        agent="customer_voice_agent",
        source_type="customer_voice",
        independence_group="customer_voice",
        claim=str(claim),
        detail=dict(voice) if isinstance(voice, dict) else {},
        confidence=0.82,
    )


def _default_code(event: AnomalyEvent) -> InvestigatorClaim:
    code = dict(event.dimensions.get("code") or {})
    files = code.get("files") or code.get("likely_files") or []
    claim = event.dimensions.get("code_claim") or (
        f"Likely surfaces: {', '.join(files)}." if files else f"Code surfaces for {event.funnel_position} under review."
    )
    return InvestigatorClaim(
        agent="code_agent",
        source_type="code",
        independence_group="code",
        claim=str(claim),
        detail=code,
        confidence=0.75 if files else 0.5,
    )


_DEFAULTS: dict[str, Callable[[AnomalyEvent], InvestigatorClaim]] = {
    "analytics_agent": _default_analytics,
    "logs_agent": _default_logs,
    "deployment_agent": _default_deploy,
    "database_agent": _default_database,
    "customer_voice_agent": _default_customer,
    "code_agent": _default_code,
}


def run_investigators(event: AnomalyEvent) -> list[InvestigatorClaim]:
    """Parallel-shaped fan-out: one claim per specialist (deterministic join)."""
    out: list[InvestigatorClaim] = []
    for spec in INVESTIGATOR_SPECS:
        claim = _probe_from_dims(event, spec["id"], spec["source_type"], spec["group"])
        if claim is None:
            claim = _DEFAULTS[spec["id"]](event)
        out.append(claim)
    return out


# --- evidence agent ----------------------------------------------------------


def correlate(event: AnomalyEvent, claims: list[InvestigatorClaim]) -> str:
    """Human-readable multi-source correlation — not a bare 'conversion dropped'."""
    custom = event.dimensions.get("correlation_summary")
    if custom:
        return str(custom)
    seg = event.dimensions.get("segments") or {}
    dep = event.dimensions.get("deploy") or {}
    pct = abs(event.magnitude)
    if event.baseline and event.baseline != 0 and abs(event.magnitude) <= 1.5:
        # treat magnitude as absolute rate or signed delta fraction
        if abs(event.magnitude) < 1:
            pct = abs(event.magnitude) * 100
        else:
            pct = abs((event.magnitude - event.baseline) / event.baseline) * 100
    parts = [f"{event.metric} moved (Δ≈{pct:.0f}% vs baseline {event.baseline})"]
    if seg:
        focus = ", ".join(f"{k}={v}" for k, v in seg.items() if v)
        if focus:
            parts.append(f"concentrated on {focus}")
    if dep.get("version"):
        parts.append(
            f"immediately after {dep.get('service', 'deploy')} {dep.get('version')}"
            + (f" ({dep.get('minutes_ago')} min prior)" if dep.get("minutes_ago") is not None else "")
        )
    logs = next((c for c in claims if c.agent == "logs_agent"), None)
    if logs and logs.confidence >= 0.7:
        parts.append(f"logs: {logs.claim[:80]}")
    return ". ".join(parts) + "."


def aggregate_evidence(event: AnomalyEvent, claims: list[InvestigatorClaim]) -> EvidencePack:
    groups = sorted({c.independence_group for c in claims})
    # Confidence: agreement across groups × mean claim confidence
    mean_c = sum(c.confidence for c in claims) / max(len(claims), 1)
    group_bonus = min(len(groups) / 6.0, 1.0)
    confidence = round(min(0.97, 0.45 * mean_c + 0.55 * group_bonus * mean_c + 0.15 * min(len(groups), 5) / 5), 3)
    checklist = {
        "customer_reports": any(c.source_type == "customer_voice" for c in claims),
        "error_logs": any(c.source_type == "logs" for c in claims),
        "deployment_timing": any(c.source_type == "deployment" for c in claims),
        "segmentation": bool(event.dimensions.get("segments")),
        "historical_baseline": event.baseline != 0 or "baseline" in event.dimensions,
        "code_surfaces": any(c.source_type == "code" and c.confidence >= 0.7 for c in claims),
        "database": any(c.source_type == "database" for c in claims),
    }
    return EvidencePack(
        claims=claims,
        independence_groups=groups,
        confidence=confidence,
        correlation_summary=correlate(event, claims),
        checklist=checklist,
    )


# --- voice + code briefs + risk ----------------------------------------------


def build_voice_context(event: AnomalyEvent, pack: EvidencePack, hypothesis: str) -> VoiceDiagnosticContext:
    sub = dict(event.dimensions.get("voice_subject") or {})
    device = str(sub.get("device") or (event.dimensions.get("segments") or {}).get("device") or "")
    failure = str(sub.get("failure") or sub.get("reason") or "")
    questions = list(sub.get("adaptive_questions") or [])
    if not questions:
        questions = [
            "When you tried to continue, did you see an error message, or did the screen keep loading?",
            "Did you try again on the same device?",
            "Have you completed this successfully before on another browser or app?",
        ]
        if device:
            questions.append(f"Were you on {device} the whole time?")
    opening = str(
        sub.get("opening")
        or (
            f"Hi{(' ' + sub['name']) if sub.get('name') else ''} — we saw a problem on your recent "
            f"{event.funnel_position} attempt"
            + (f" ({sub.get('attempt_summary')})" if sub.get("attempt_summary") else "")
            + ". Thirty seconds to help us diagnose?"
        )
    )
    return VoiceDiagnosticContext(
        user_label=str(sub.get("name") or sub.get("user_label") or "customer"),
        attempt_summary=str(sub.get("attempt_summary") or sub.get("amount") or ""),
        device=device,
        failure=failure,
        previous_attempts=int(sub.get("previous_attempts") or sub.get("attempts") or 0),
        known_issue=str(sub.get("known_issue") or ""),
        hypothesis_hint=hypothesis,
        opening=opening,
        adaptive_questions=questions,
        raw=sub,
    )


def voice_system_prompt(ctx: VoiceDiagnosticContext) -> str:
    return (
        "You are the Customer Voice Agent doing diagnostic research — not a survey. "
        f"User={ctx.user_label}. Attempt={ctx.attempt_summary}. Device={ctx.device}. "
        f"Suspected failure={ctx.failure}. Prior attempts={ctx.previous_attempts}. "
        f"Known issue hint={ctx.known_issue}. Hypothesis={ctx.hypothesis_hint}. "
        "Ask one short adaptive question at a time based on their last answer. "
        "Disambiguate error vs loading vs wrong browser. Never invent facts. Never offer discounts."
    )


def build_code_brief(event: AnomalyEvent, pack: EvidencePack, hypothesis: str) -> CodeIssueBrief:
    code = dict(event.dimensions.get("code") or {})
    files = list(code.get("files") or code.get("likely_files") or [])
    return CodeIssueBrief(
        issue=str(code.get("issue") or pack.correlation_summary),
        evidence_summary=[c.claim for c in pack.claims],
        likely_files=files,
        expected_behavior=str(code.get("expected_behavior") or "Restore prior successful path for affected segment."),
        regression_test=str(
            code.get("regression_test")
            or f"Reproduce {event.metric} failure for segment {event.dimensions.get('segments') or {}}."
        ),
        surface=str(code.get("surface") or event.funnel_position),
        hypothesis=hypothesis,
        confidence=pack.confidence,
    )


def assess_risk(surface: str, statement: str = "", action_type: str = "code_change") -> RiskDecision:
    """Governed autonomy — surface drives tier, not model confidence."""
    from loop.engine import assign_risk_tier

    blob = f"{surface} {statement} {action_type}".lower()
    tier = assign_risk_tier(surface, statement)
    # Extra policy layer for documentation / test-only
    if action_type in {"docs", "test_fix"} or any(k in blob for k in ("typo", "readme", "docs only")):
        tier = RiskTier.LOW
    auto = tier == RiskTier.LOW
    return RiskDecision(
        tier=tier,
        auto_test_pr=auto,
        developer_approval=tier == RiskTier.MEDIUM,
        human_approval=tier == RiskTier.HIGH,
        rationale=(
            "LOW: auto-test + PR only. "
            if auto
            else "MEDIUM: developer approval. "
            if tier == RiskTier.MEDIUM
            else "HIGH: mandatory human approval (auth/payment/financial/destructive). "
        )
        + f"Surface={surface}. Never auto-merge.",
        surface=surface,
    )


# --- product intelligence ----------------------------------------------------


def _normalize_theme(text: str) -> str:
    t = text.lower().strip()
    for noise in ("i want", "please add", "support", "need", "can you", "wish"):
        t = t.replace(noise, " ")
    return " ".join(t.split())[:80] or "feature"


def cluster_feature_requests(
    mentions: list[FeatureMention],
    *,
    competitor_capability: bool | None = None,
    implementation_estimate: Literal["low", "medium", "high"] = "medium",
    theme_override: str | None = None,
) -> list[FeatureCluster]:
    """N conversations → ranked clusters (not N GitHub issues)."""
    buckets: dict[str, list[FeatureMention]] = {}
    for m in mentions:
        key = theme_override or _normalize_theme(m.text)
        # crude token overlap merge into existing keys
        matched = None
        for existing in buckets:
            a, b = set(existing.split()), set(key.split())
            if a and b and len(a & b) / max(len(a | b), 1) >= 0.4:
                matched = existing
                break
        buckets.setdefault(matched or key, []).append(m)

    clusters: list[FeatureCluster] = []
    for theme, items in buckets.items():
        rev = sum(m.revenue_hint_usd or 0 for m in items)
        freq = len(items)
        churn: Literal["low", "medium", "high"] = "high" if freq >= 20 else "medium" if freq >= 8 else "low"
        clusters.append(
            FeatureCluster(
                theme=theme_override or theme,
                frequency=freq,
                revenue_affected_usd=float(rev),
                churn_risk=churn,
                competitor_capability=bool(competitor_capability) if competitor_capability is not None else freq >= 10,
                implementation_estimate=implementation_estimate,
                sample_quotes=[m.text for m in items[:5]],
                mention_ids=[m.user_id or m.text[:24] for m in items],
            )
        )
    clusters.sort(key=lambda c: (c.frequency, c.revenue_affected_usd), reverse=True)
    return clusters


def build_product_proposal(cluster: FeatureCluster) -> ProductProposal:
    return ProductProposal(
        title=cluster.theme.title() if cluster.theme.islower() else cluster.theme,
        cluster=cluster,
        recommendation=(
            f"Cluster of {cluster.frequency} requests"
            + (f" · ~${cluster.revenue_affected_usd:,.0f} revenue affected" if cluster.revenue_affected_usd else "")
            + f" · churn {cluster.churn_risk}"
            + (" · competitor already has it" if cluster.competitor_capability else "")
            + f" · estimate {cluster.implementation_estimate}. One proposal — not {cluster.frequency} issues."
        ),
        next_step="pm_approval_then_github_issue",
    )


def run_product_intelligence(
    engine: Any,
    mentions: list[FeatureMention],
    *,
    theme: str | None = None,
    scenario_id: str | None = None,
    title: str | None = None,
    competitor_capability: bool | None = None,
    implementation_estimate: Literal["low", "medium", "high"] = "medium",
    revenue_affected_usd: float | None = None,
) -> dict[str, Any]:
    """Customer → Product → Engineering bridge."""
    from loop.world import post

    clusters = cluster_feature_requests(
        mentions,
        competitor_capability=competitor_capability,
        implementation_estimate=implementation_estimate,
        theme_override=theme,
    )
    if not clusters:
        return {"clusters": [], "proposal": None}
    top = clusters[0]
    if revenue_affected_usd is not None:
        top.revenue_affected_usd = revenue_affected_usd
    if theme:
        top.theme = theme
    proposal = build_product_proposal(top)

    scenario = scenario_id or f"product:{_normalize_theme(top.theme).replace(' ', '_')}"
    existing = next((r for r in engine.store.list_rooms() if r.scenario_id == scenario), None)
    if existing:
        return {
            "scenario": scenario,
            "room_id": existing.id,
            "clusters": [c.model_dump() for c in clusters],
            "proposal": proposal.model_dump(),
            "reused": True,
        }

    event = AnomalyEvent(
        kind="feature_request_cluster",
        metric="feature_request",
        title=title or f"{top.frequency} customers asked for {top.theme}",
        family="customer",
        magnitude=float(top.frequency),
        baseline=0,
        polarity="positive",
        funnel_position="product",
        dimensions={
            "probes": {
                "customer_voice_agent": {
                    "claim": f"{top.frequency} distinct mentions of '{top.theme}'.",
                    "independence_group": "customer_voice",
                },
                "analytics_agent": {
                    "claim": f"Revenue affected estimate ${top.revenue_affected_usd:,.0f}."
                    if top.revenue_affected_usd
                    else "Demand clustered from customer channels.",
                    "independence_group": "analytics",
                },
                "code_agent": {
                    "claim": "No bug — product opportunity cluster.",
                    "independence_group": "product_research",
                },
            },
            "hypothesis": {
                "statement": (
                    f"{top.theme} is a ranked opportunity: frequency {top.frequency}, "
                    f"revenue ${top.revenue_affected_usd:,.0f}, churn {top.churn_risk}."
                )
            },
        },
    )
    # Force three groups for gate
    out = run_investigation(
        engine,
        event,
        scenario_id=scenario,
        propose_action=True,
        action_type="product_proposal",
        classification=Classification.OPPORTUNITY,
        loop_type=LoopType.TYPE_B,
        path=PathKind.FEATURE,
        room_kind=RoomKind.OPPORTUNITY,
        surface="feature proposal / prd / github issue",
        extra_artifacts={
            "prd": proposal.model_dump(),
            "cluster": top.model_dump(),
        },
    )
    room_id = out["room_id"]
    post(
        engine,
        room_id,
        author="product_agent",
        author_kind="agent",
        kind="artifact",
        text=proposal.recommendation,
        artifact_type="prd",
        artifact=proposal.model_dump(),
    )
    return {
        **out,
        "clusters": [c.model_dump() for c in clusters],
        "proposal": proposal.model_dump(),
        "reused": False,
    }


# --- main investigation pipeline ---------------------------------------------


def resolve_loop(event: AnomalyEvent) -> tuple[LoopType, PathKind, RoomKind, Classification, Direction]:
    if event.loop_type is not None:
        lt = event.loop_type
    elif event.polarity == "positive":
        lt = LoopType.TYPE_B
    elif event.polarity == "negative":
        lt = LoopType.TYPE_A
    else:
        lt = LoopType.TYPE_A if event.magnitude < 0 else LoopType.TYPE_B
    path = PathKind.BUG if lt == LoopType.TYPE_A else PathKind.FEATURE
    kind = RoomKind.INCIDENT if lt == LoopType.TYPE_A else RoomKind.OPPORTUNITY
    classification = Classification.BUG if lt == LoopType.TYPE_A else Classification.OPPORTUNITY
    direction = Direction.NEGATIVE if lt == LoopType.TYPE_A else Direction.POSITIVE
    return lt, path, kind, classification, direction


def _family(name: str) -> SignalFamily:
    # funnel maps onto business for storage enum
    mapping = {"funnel": SignalFamily.BUSINESS, "technical": SignalFamily.TECHNICAL, "business": SignalFamily.BUSINESS, "customer": SignalFamily.CUSTOMER}
    return mapping.get(name, SignalFamily.BUSINESS)


def run_investigation(
    engine: Any,
    event: AnomalyEvent,
    *,
    scenario_id: str | None = None,
    propose_action: bool = True,
    action_type: str = "code_change",
    classification: Classification | None = None,
    loop_type: LoopType | None = None,
    path: PathKind | None = None,
    room_kind: RoomKind | None = None,
    surface: str | None = None,
    extra_artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect → fan-out → evidence → hypothesis → voice/code briefs → risk → propose."""
    from loop.world import _add_facts, post

    lt, pth, rk, clas, direction = resolve_loop(event)
    if loop_type is not None:
        lt = loop_type
    if path is not None:
        pth = path
    if room_kind is not None:
        rk = room_kind
    if classification is not None:
        clas = classification

    scenario = scenario_id or f"invest:{event.kind}"
    claims = run_investigators(event)
    pack = aggregate_evidence(event, claims)
    hyp_statement = str(
        (event.dimensions.get("hypothesis") or {}).get("statement") or pack.correlation_summary
    )

    existing = next((r for r in engine.store.list_rooms() if r.scenario_id == scenario), None)
    if existing and existing.investigation_id:
        inv = engine.store.get_investigation(existing.investigation_id)
        if inv and inv.linked_hypothesis_ids:
            return {
                "scenario": scenario,
                "room_id": existing.id,
                "investigation_id": inv.id,
                "reused": True,
                "evidence": pack.model_dump(),
                "pipeline": catalog()["pipeline"],
            }

    sig = Signal(
        id=_id("sig"),
        family=_family(event.family),
        direction=direction,
        funnel_position=event.funnel_position,
        metric=event.metric,
        magnitude=event.magnitude,
        baseline=event.baseline,
        affected_segments=[
            Segment(
                browser=str((event.dimensions.get("segments") or {}).get("browser") or ""),
                os=str((event.dimensions.get("segments") or {}).get("os") or ""),
                platform=str((event.dimensions.get("segments") or {}).get("platform") or "web"),
                geo=str((event.dimensions.get("segments") or {}).get("geo") or ""),
            )
        ],
        detection_window=event.dimensions.get("detection_window")
        or {"start": "2026-08-26", "end": "2026-08-28", "baseline_start": "2026-08-06", "baseline_end": "2026-08-19"},
        confidence=event.confidence,
        source=event.source,
        status=SignalStatus.OPEN,
        detected_at=_now(),
    )
    engine.store.put_signal(sig)
    inv = engine.open_investigation(sig)
    assert inv
    inv.scenario_id = scenario
    inv.loop_type = lt
    title = event.title or f"{event.metric} anomaly"
    members = [
        "orchestrator",
        "signal_agent",
        "investigator_agent",
        "analytics_agent",
        "logs_agent",
        "deployment_agent",
        "database_agent",
        "customer_voice_agent",
        "code_agent",
        "evidence_agent",
        "root_cause_agent",
        "risk_agent",
        "you",
    ]
    room = Room(
        id=_id("room"),
        kind=rk,
        title=title,
        topic=pack.correlation_summary,
        status="open",
        created_at=_now(),
        members=members,
        investigation_id=inv.id,
        scenario_id=scenario,
        loop_type=lt,
        path=pth,
    )
    inv.room_id = room.id
    inv.title = title
    engine.store.put_investigation(inv)
    engine.store.put_room(room)

    post(
        engine,
        room.id,
        author="signal_agent",
        author_kind="agent",
        kind="artifact",
        text=title,
        artifact_type="signal",
        artifact={
            "kind": event.kind,
            "family": event.family,
            "metric": event.metric,
            "catalog": event.family,
            "magnitude": event.magnitude,
            "baseline": event.baseline,
        },
    )
    post(
        engine,
        room.id,
        author="investigator_agent",
        author_kind="agent",
        kind="chat",
        text="Dispatching analytics · logs · deploy · database · customer · code in parallel.",
    )

    # Fan-out posts (join later)
    for claim in claims:
        engine.a2a(inv.id, "investigator_agent", claim.agent, "TB-2", claim.source_type)
        post(
            engine,
            room.id,
            author=claim.agent,
            author_kind="agent",
            kind="artifact",
            text=claim.claim,
            artifact_type="evidence",
            artifact=claim.model_dump(),
        )

    facts = [
        {
            "source_type": c.source_type,
            "source_reference": c.independence_group,
            "claim": c.claim,
            "independence_group": c.independence_group,
            "collected_by": c.agent,
            "confidence": c.confidence,
        }
        for c in claims
    ]
    # Deduplicate independence groups for the ≥3 gate — keep first 6 unique groups
    seen: set[str] = set()
    uniq_facts = []
    for f in facts:
        if f["independence_group"] in seen:
            continue
        seen.add(f["independence_group"])
        uniq_facts.append(f)
    _add_facts(engine, inv, uniq_facts[:6])

    post(
        engine,
        room.id,
        author="evidence_agent",
        author_kind="agent",
        kind="artifact",
        text=pack.correlation_summary,
        artifact_type="evidence_pack",
        artifact=pack.model_dump(),
    )

    hyp = engine.form_hypothesis(inv, statement=hyp_statement, classification=clas)
    voice_ctx = build_voice_context(event, pack, hyp_statement)
    code_brief = build_code_brief(event, pack, hyp_statement)
    surf = surface or str((event.dimensions.get("code") or {}).get("surface") or event.funnel_position)
    risk = assess_risk(surf, hyp_statement, action_type)

    result: dict[str, Any] = {
        "scenario": scenario,
        "event": event.model_dump(mode="json"),
        "room_id": room.id,
        "investigation_id": inv.id,
        "evidence": pack.model_dump(),
        "hypothesis": hyp.model_dump(mode="json") if hyp else None,
        "voice_context": voice_ctx.model_dump(),
        "voice_system_prompt": voice_system_prompt(voice_ctx),
        "code_brief": code_brief.model_dump(),
        "risk": risk.model_dump(mode="json"),
        "pipeline": catalog()["pipeline"],
        "fan_out": [s["id"] for s in INVESTIGATOR_SPECS],
        "reused": False,
    }

    if not hyp:
        post(
            engine,
            room.id,
            author="root_cause_agent",
            author_kind="agent",
            kind="chat",
            text="Three-source gate refused — need more independent evidence.",
        )
        return result

    # Stamp hypothesis confidence from evidence pack
    hyp.confidence = pack.confidence
    engine.store.put_hypothesis(hyp)

    post(
        engine,
        room.id,
        author="root_cause_agent",
        author_kind="agent",
        kind="artifact",
        text=hyp.statement,
        artifact_type="hypothesis",
        artifact={
            **hyp.model_dump(mode="json"),
            "evidence_checklist": pack.checklist,
            "confidence": pack.confidence,
        },
    )
    post(
        engine,
        room.id,
        author="customer_voice_agent",
        author_kind="agent",
        kind="artifact",
        text=f"Diagnostic context ready for {voice_ctx.user_label} · {voice_ctx.failure or 'friction'}",
        artifact_type="voice_context",
        artifact=voice_ctx.model_dump(),
    )
    post(
        engine,
        room.id,
        author="code_agent",
        author_kind="agent",
        kind="artifact",
        text=code_brief.issue[:200],
        artifact_type="code_brief",
        artifact=code_brief.model_dump(),
    )
    post(
        engine,
        room.id,
        author="risk_agent",
        author_kind="agent",
        kind="artifact",
        text=f"{risk.tier.value} · {risk.rationale}",
        artifact_type="risk_decision",
        artifact=risk.model_dump(mode="json"),
    )

    action = None
    if propose_action:
        artifacts = {
            "code_brief": code_brief.model_dump(),
            "voice_context": voice_ctx.model_dump(),
            "pr": {
                "title": f"Fix: {event.kind}",
                "body": hyp.statement,
                "files": code_brief.likely_files,
                "tests": code_brief.regression_test,
            },
            **(extra_artifacts or {}),
        }
        if action_type == "product_proposal":
            artifacts.pop("pr", None)
        action = engine.propose_action(
            inv,
            hyp,
            surface=surf,
            action_type=action_type,
            artifacts=artifacts,
            consequence=risk.rationale,
            semantic=f"invest-{event.kind}-{risk.tier.value.lower()}",
        )
        result["action"] = action.model_dump(mode="json")

    return result


# --- example recipes (payload only) ------------------------------------------


def example_segmented_conversion_anomaly() -> AnomalyEvent:
    """Recipe: conversion drop with segment + deploy correlation (not the only signal type)."""
    return AnomalyEvent(
        kind="conversion_drop_segmented",
        metric="purchase_conversion",
        title="Purchase conversion ↓ with segment concentration",
        family="business",
        magnitude=-0.18,
        baseline=0.42,
        polarity="negative",
        funnel_position="payment",
        dimensions={
            "segments": {"browser": "Safari", "os": "iOS"},
            "deploy": {"service": "pay-sdk", "version": "v2.14", "minutes_ago": 42},
            "logs": {"cluster": "3ds_timeout", "count": 140},
            "voice_subject": {
                "name": "Alex",
                "attempt_summary": "checkout attempt",
                "device": "iPhone / Safari",
                "failure": "authentication timeout",
                "previous_attempts": 2,
                "known_issue": "Possible browser-specific regression after pay-sdk change",
            },
            "code": {
                "files": ["payment/callback.ts", "payment/3ds.ts"],
                "expected_behavior": "3DS callback completes and order confirms",
                "regression_test": "Safari + 3DS callback timeout scenario",
                "surface": "payment authorization / 3DS",
            },
            "probes": {
                "analytics_agent": {
                    "claim": "Purchase conversion −18% overall; Safari segment −23% vs Chrome flat.",
                    "independence_group": "analytics",
                },
                "logs_agent": {
                    "claim": "3DS timeout spike; 140 events in window.",
                    "independence_group": "logs",
                },
                "deployment_agent": {
                    "claim": "pay-sdk v2.14 shipped 42 minutes before onset.",
                    "independence_group": "deploys",
                },
                "customer_voice_agent": {
                    "claim": "Customers report payment page kept loading — no error text.",
                    "independence_group": "customer_voice",
                },
            },
            "correlation_summary": (
                "Payment failures increased ~23% specifically for Safari users "
                "immediately after deployment pay-sdk v2.14."
            ),
            "hypothesis": {
                "statement": (
                    "pay-sdk v2.14 introduced a Safari 3DS callback regression. "
                    "Chrome unaffected. Deploy timing + logs + segment + voice agree."
                )
            },
        },
    )


def example_feature_mentions() -> list[FeatureMention]:
    """Recipe: many requests → one product proposal."""
    quotes = [
        "I want Apple Pay",
        "Please add Apple Pay on iOS",
        "Apple Pay support please",
        "Checkout needs Apple Pay",
        "Why no Apple Pay?",
    ]
    # Expand to frequency without 37 literal loops in architecture
    mentions = [
        FeatureMention(text=quotes[i % len(quotes)], user_id=f"u_{i}", channel="review", revenue_hint_usd=2200)
        for i in range(37)
    ]
    return mentions
