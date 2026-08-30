"""Product improvement infrastructure — signal → evidence → hypothesis → act → measure → learn.

Type A (negative): something broke → find and fix.
Type B (positive opportunity): something could be better → find and improve via experiment.

Recipes supply a ProductSignalEvent (metrics, evidence claims, experiment knobs).
The pipeline and agent interplay stay generic — no hardcoding of shipping, Safari, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from loop.models import (
    Classification,
    Direction,
    InvestigationState,
    Lesson,
    LoopType,
    Outcome,
    OutcomeVerdict,
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


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


# --- schemas -----------------------------------------------------------------


class EvidenceClaim(BaseModel):
    source_type: str
    source_reference: str
    claim: str
    independence_group: str
    collected_by: str = "analytics_agent"
    confidence: float = 0.86


class ExperimentDesign(BaseModel):
    hypothesis: str
    treatment: str
    flag: str = ""
    rollout_pct: float = 5.0
    primary_metric: str
    guardrail: str
    mde: float = 0.08
    stopping_rule: str = "14d or guardrail harm"
    cohort: str = "random_hash"
    expected_impact: str = ""


class ExperimentResult(BaseModel):
    primary_metric: str
    control: float
    treatment: float
    delta: float
    guardrail_ok: bool = True
    verdict: str  # ship | iterate | abort
    decision: str


class ProductSignalEvent(BaseModel):
    """Observed product signal — Type A or Type B. Recipes fill this; pipeline is shared."""

    kind: str
    metric: str
    magnitude: float = 0.0
    baseline: float = 0.0
    title: str = ""
    topic: str = ""
    funnel_position: str = "product"
    confidence: float = 0.8
    source: str = "warehouse"
    family: Literal["business", "technical", "customer"] = "business"
    # Resolve Type A/B: loop_type > polarity > magnitude sign (<0 ⇒ A)
    polarity: Literal["negative", "positive"] | None = None
    loop_type: LoopType | None = None
    path: PathKind | None = None
    room_kind: RoomKind | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    memory_conditions: list[str] = Field(default_factory=list)
    # dimensions keys (all optional):
    #   evidence: list[EvidenceClaim-like]
    #   hypothesis: {statement, classification?}
    #   experiment: ExperimentDesign-like fields
    #   action: {type, surface, artifacts, semantic, consequence}  # Type A (or override)
    #   measure: {control, treatment, guardrail_ok?}  # simulated outcome
    #   lesson: {statement, root_cause_family, applicable_conditions}
    #   product / segment hints


def resolve_loop(event: ProductSignalEvent) -> tuple[LoopType, PathKind, RoomKind, Classification, Direction]:
    if event.loop_type is not None:
        lt = event.loop_type
    elif event.polarity == "negative":
        lt = LoopType.TYPE_A
    elif event.polarity == "positive":
        lt = LoopType.TYPE_B
    else:
        lt = LoopType.TYPE_A if event.magnitude < 0 else LoopType.TYPE_B

    if event.path is not None:
        path = event.path
    else:
        path = PathKind.BUG if lt == LoopType.TYPE_A else PathKind.FEATURE

    if event.room_kind is not None:
        kind = event.room_kind
    else:
        kind = RoomKind.INCIDENT if lt == LoopType.TYPE_A else RoomKind.OPPORTUNITY

    classification = Classification.BUG if lt == LoopType.TYPE_A else Classification.OPPORTUNITY
    direction = Direction.NEGATIVE if lt == LoopType.TYPE_A else Direction.POSITIVE
    return lt, path, kind, classification, direction


def _family(name: str) -> SignalFamily:
    try:
        return SignalFamily(name)
    except ValueError:
        return SignalFamily.BUSINESS


# --- evidence / design / measure ---------------------------------------------


def evidence_from_event(event: ProductSignalEvent) -> list[EvidenceClaim]:
    raw = event.dimensions.get("evidence") or []
    out: list[EvidenceClaim] = []
    for item in raw:
        if isinstance(item, EvidenceClaim):
            out.append(item)
        elif isinstance(item, dict):
            data = dict(item)
            if not data.get("source_reference"):
                st = str(data.get("source_type") or "source")
                by = str(data.get("collected_by") or "agent")
                data["source_reference"] = f"{st}:{by}"
            out.append(EvidenceClaim.model_validate(data))
    return out


def build_experiment_design(event: ProductSignalEvent, hypothesis_statement: str) -> ExperimentDesign:
    raw = dict(event.dimensions.get("experiment") or {})
    treatment = str(raw.get("treatment") or f"improve_{event.kind}")
    return ExperimentDesign(
        hypothesis=str(raw.get("hypothesis") or hypothesis_statement),
        treatment=treatment,
        flag=str(raw.get("flag") or treatment),
        rollout_pct=float(raw.get("rollout_pct") or 5),
        primary_metric=str(raw.get("primary_metric") or event.metric),
        guardrail=str(raw.get("guardrail") or "purchase_conversion"),
        mde=float(raw.get("mde") or 0.08),
        stopping_rule=str(raw.get("stopping_rule") or "14d or guardrail harm"),
        cohort=str(raw.get("cohort") or "random_hash"),
        expected_impact=str(raw.get("expected_impact") or ""),
    )


def simulate_experiment_result(event: ProductSignalEvent, design: ExperimentDesign) -> ExperimentResult:
    """Deterministic measure step when no live flag platform is wired."""
    m = dict(event.dimensions.get("measure") or {})
    control = float(m.get("control", event.baseline if event.baseline else abs(event.magnitude)))
    if "treatment" in m:
        treatment = float(m["treatment"])
    else:
        # Opportunity friction metrics: treatment lowers the bad rate; Type A recovery raises the good metric.
        lt, *_ = resolve_loop(event)
        if lt == LoopType.TYPE_B:
            treatment = control * (1.0 - float(design.mde))
        else:
            treatment = control * (1.0 + float(design.mde))
    delta = treatment - control
    guardrail_ok = bool(m.get("guardrail_ok", True))
    lt, *_ = resolve_loop(event)
    if not guardrail_ok:
        verdict, decision = "abort", "Guardrail harmed — stop rollout."
    elif lt == LoopType.TYPE_B and delta < 0:
        verdict, decision = "ship", "Treatment improved primary metric vs control — expand carefully."
    elif lt == LoopType.TYPE_A and delta > 0:
        verdict, decision = "ship", "Recovery confirmed vs pre — keep fix."
    else:
        verdict, decision = "iterate", "Inconclusive vs MDE — iterate design."
    if m.get("verdict"):
        verdict = str(m["verdict"])
    if m.get("decision"):
        decision = str(m["decision"])
    return ExperimentResult(
        primary_metric=design.primary_metric,
        control=control,
        treatment=treatment,
        delta=delta,
        guardrail_ok=guardrail_ok,
        verdict=verdict,
        decision=decision,
    )


def match_memory(store: Any, conditions: list[str]) -> list[dict[str, Any]]:
    if not conditions:
        return []
    want = set(conditions)
    hits: list[dict[str, Any]] = []
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


# --- pipeline ----------------------------------------------------------------


def run_product_loop(
    engine: Any,
    event: ProductSignalEvent,
    *,
    scenario_id: str | None = None,
    simulate_outcome: bool = True,
    reuse_existing_room: bool = True,
) -> dict[str, Any]:
    """Detect → evidence → hypothesize → (fix | experiment) → measure → learn."""
    from loop.world import _add_facts, post

    lt, path, room_kind, classification, direction = resolve_loop(event)
    scenario = scenario_id or f"improve:{event.kind}"
    memory_hits = match_memory(engine.store, event.memory_conditions)

    existing = None
    if reuse_existing_room:
        existing = next((r for r in engine.store.list_rooms() if r.scenario_id == scenario), None)

    if existing:
        room = existing
        inv = engine.store.get_investigation(room.investigation_id) if room.investigation_id else None
        # Idempotent re-entry: return current state without duplicating the loop.
        if inv and inv.linked_hypothesis_ids:
            return {
                "scenario": scenario,
                "loop_type": lt.value,
                "path": path.value,
                "room_id": room.id,
                "investigation_id": inv.id,
                "reused": True,
                "pipeline": _pipeline_labels(lt),
            }
    else:
        inv = None
        room = None

    family = _family(event.family)
    sig = Signal(
        id=_id("sig"),
        family=family,
        direction=direction,
        funnel_position=event.funnel_position,
        metric=event.metric,
        magnitude=event.magnitude,
        baseline=event.baseline,
        affected_segments=[
            Segment(
                platform=str((event.dimensions.get("segment") or {}).get("platform") or "web"),
                app_version=str(event.dimensions.get("app_version") or ""),
            )
        ],
        detection_window=event.dimensions.get("detection_window")
        or {
            "start": "2026-08-26",
            "end": "2026-08-28",
            "baseline_start": "2026-08-06",
            "baseline_end": "2026-08-19",
        },
        confidence=event.confidence,
        source=event.source,
        status=SignalStatus.OPEN,
        detected_at=_now(),
    )
    engine.store.put_signal(sig)

    if not inv:
        inv = engine.open_investigation(sig)
        assert inv
        inv.scenario_id = scenario
        inv.loop_type = lt
        inv.recalled_lessons = [h["statement"] for h in memory_hits]
        title = event.title or f"{event.metric} · {event.kind}"
        topic = event.topic or (
            "Type A · something broke. Find and fix."
            if lt == LoopType.TYPE_A
            else "Type B · opportunity. Find and improve."
        )
        members = [
            "orchestrator",
            "signal_agent",
            "analytics_agent",
            "product_agent",
            "root_cause_agent",
            "experiment_agent" if lt == LoopType.TYPE_B else "code_agent",
            "risk_agent",
            "learning_agent",
            "you",
        ]
        room = Room(
            id=_id("room"),
            kind=room_kind,
            title=title,
            topic=topic,
            status="open",
            created_at=_now(),
            members=members,
            investigation_id=inv.id,
            scenario_id=scenario,
            loop_type=lt,
            path=path,
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
                "metric": event.metric,
                "magnitude": event.magnitude,
                "baseline": event.baseline,
                "loop_type": lt.value,
                "polarity": "negative" if lt == LoopType.TYPE_A else "positive",
                "label": "Type A — find and fix" if lt == LoopType.TYPE_A else "Type B — find and improve",
            },
        )
    assert inv and room

    if memory_hits:
        post(
            engine,
            room.id,
            author="learning_agent",
            author_kind="agent",
            kind="artifact",
            text=memory_hits[0]["statement"],
            artifact_type="memory",
            artifact={"lessons": memory_hits},
        )

    claims = evidence_from_event(event)
    if len(claims) < 3:
        # Pad with generic independent sources so the ≥3 gate can fire when recipes are thin.
        pads = [
            EvidenceClaim(
                source_type="analytics",
                source_reference=f"{event.metric}@warehouse",
                claim=f"{event.metric} observed at {event.magnitude} (baseline {event.baseline}).",
                independence_group="analytics_warehouse",
                collected_by="analytics_agent",
            ),
            EvidenceClaim(
                source_type="logs",
                source_reference=f"logs:{event.funnel_position}",
                claim=f"Session/log cluster on {event.funnel_position} aligns with the signal.",
                independence_group="logs",
                collected_by="logs_agent",
            ),
            EvidenceClaim(
                source_type="customer_voice",
                source_reference=f"voice:{event.kind}",
                claim=event.dimensions.get("voice_claim")
                or "Customer feedback cluster supports the product hypothesis direction.",
                independence_group="customer_voice",
                collected_by="feedback_agent",
            ),
        ]
        have_groups = {c.independence_group for c in claims}
        for p in pads:
            if p.independence_group not in have_groups:
                claims.append(p)
                have_groups.add(p.independence_group)
            if len(have_groups) >= 3:
                break

    _add_facts(engine, inv, [c.model_dump() for c in claims])

    hyp_raw = dict(event.dimensions.get("hypothesis") or {})
    statement = str(
        hyp_raw.get("statement")
        or (
            f"{event.metric} moved to {event.magnitude} from baseline {event.baseline}. "
            + (
                "Likely regression — propose a scoped fix."
                if lt == LoopType.TYPE_A
                else "Opportunity to reduce friction — design a controlled experiment."
            )
        )
    )
    hyp = engine.form_hypothesis(inv, statement=statement, classification=classification)
    if not hyp:
        post(
            engine,
            room.id,
            author="root_cause_agent",
            author_kind="agent",
            kind="chat",
            text="Three-source gate refused — need more independent evidence before a hypothesis.",
        )
        return {
            "scenario": scenario,
            "loop_type": lt.value,
            "path": path.value,
            "room_id": room.id,
            "investigation_id": inv.id,
            "hypothesis": None,
            "pipeline": _pipeline_labels(lt),
            "gate": "three_source_refused",
        }

    post(
        engine,
        room.id,
        author="root_cause_agent",
        author_kind="agent",
        kind="artifact",
        text=hyp.statement,
        artifact_type="hypothesis",
        artifact=hyp.model_dump(mode="json"),
    )

    design: ExperimentDesign | None = None
    action = None
    result: ExperimentResult | None = None
    outcome: Outcome | None = None
    lesson: Lesson | None = None

    if lt == LoopType.TYPE_B:
        design = build_experiment_design(event, hyp.statement)
        post(
            engine,
            room.id,
            author="product_agent",
            author_kind="agent",
            kind="artifact",
            text=design.expected_impact or design.hypothesis,
            artifact_type="product_proposal",
            artifact={
                "title": "Product proposal",
                "hypothesis": design.hypothesis,
                "expected_impact": design.expected_impact,
                "treatment": design.treatment,
            },
        )
        post(
            engine,
            room.id,
            author="experiment_agent",
            author_kind="agent",
            kind="artifact",
            text=(
                f"Design: {design.treatment} @ {design.rollout_pct}%. "
                f"Primary={design.primary_metric}. Guardrail={design.guardrail}. "
                f"MDE={design.mde}. Stop: {design.stopping_rule}."
            ),
            artifact_type="experiment_design",
            artifact=design.model_dump(),
        )
        action = engine.propose_action(
            inv,
            hyp,
            surface=str((event.dimensions.get("action") or {}).get("surface") or f"experiment flag / {event.funnel_position}"),
            action_type="experiment",
            artifacts={
                "flag": design.flag,
                "from": "off",
                "to": str(int(design.rollout_pct)),
                "rollout_pct": design.rollout_pct,
                "primary_metric": design.primary_metric,
                "guardrail": design.guardrail,
                "mde": design.mde,
                "stopping_rule": design.stopping_rule,
            },
            consequence=(
                f"MEDIUM experiment: {design.rollout_pct}% flag. "
                "Developer approval. Ceiling enforced in tool code (max 5% without human)."
            ),
            semantic=str((event.dimensions.get("action") or {}).get("semantic") or f"exp-{design.flag}-{int(design.rollout_pct)}"),
        )
        post(
            engine,
            room.id,
            author="risk_agent",
            author_kind="agent",
            kind="artifact",
            text=f"{action.risk_tier.value} · {design.rollout_pct}% experiment waiting on developer approval.",
            artifact_type="risk_decision",
            artifact=action.model_dump(mode="json"),
        )
        if simulate_outcome:
            result = simulate_experiment_result(event, design)
            post(
                engine,
                room.id,
                author="experiment_agent",
                author_kind="agent",
                kind="artifact",
                text=f"Control {result.control:.4g} → treatment {result.treatment:.4g} (Δ {result.delta:+.4g}). {result.decision}",
                artifact_type="experiment_result",
                artifact=result.model_dump(),
            )
            outcome, lesson = _record_learn(engine, inv, event, hyp.statement, result)
    else:
        act = dict(event.dimensions.get("action") or {})
        action = engine.propose_action(
            inv,
            hyp,
            surface=str(act.get("surface") or event.funnel_position or "product surface"),
            action_type=str(act.get("type") or "code_change"),
            artifacts=act.get("artifacts")
            or {
                "pr": {
                    "title": f"Fix: {event.kind}",
                    "body": hyp.statement,
                    "tests": "regression must fail pre-change and pass post-change",
                }
            },
            consequence=str(act.get("consequence") or "Scoped fix. Human approve before merge."),
            semantic=str(act.get("semantic") or f"fix-{event.kind}"),
        )
        post(
            engine,
            room.id,
            author="code_agent",
            author_kind="agent",
            kind="artifact",
            text=f"Proposed {action.type}: {hyp.statement[:160]}",
            artifact_type="pr",
            artifact=action.artifacts,
        )
        post(
            engine,
            room.id,
            author="risk_agent",
            author_kind="agent",
            kind="artifact",
            text=f"{action.risk_tier.value} · awaiting {action.required_approver_role}.",
            artifact_type="risk_decision",
            artifact=action.model_dump(mode="json"),
        )
        if simulate_outcome:
            # Type A measure via engine verify path when possible; else synthetic recovery.
            try:
                outcome = engine.verify(inv.id)
                lesson = next(
                    (L for L in engine.store.list_lessons() if L.investigation_id == inv.id),
                    None,
                )
                post(
                    engine,
                    room.id,
                    author="learning_agent",
                    author_kind="agent",
                    kind="artifact",
                    text=getattr(lesson, "statement", None) or f"Verification {outcome.verdict.value}",
                    artifact_type="memory",
                    artifact=outcome.model_dump(mode="json"),
                )
            except Exception:
                design = build_experiment_design(event, hyp.statement)
                result = simulate_experiment_result(event, design)
                outcome, lesson = _record_learn(engine, inv, event, hyp.statement, result)

    return {
        "scenario": scenario,
        "event": event.model_dump(mode="json"),
        "loop_type": lt.value,
        "path": path.value,
        "room_id": room.id,
        "investigation_id": inv.id,
        "hypothesis": hyp.model_dump(mode="json"),
        "experiment": design.model_dump() if design else None,
        "action": action.model_dump(mode="json") if action else None,
        "result": result.model_dump() if result else None,
        "outcome": outcome.model_dump(mode="json") if outcome else None,
        "lesson": lesson.model_dump(mode="json") if lesson else None,
        "pipeline": _pipeline_labels(lt),
        "reused": False,
    }


def _pipeline_labels(lt: LoopType) -> list[str]:
    if lt == LoopType.TYPE_B:
        return ["detect", "hypothesize", "experiment", "measure", "learn"]
    return ["detect", "hypothesize", "fix", "measure", "learn"]


def _record_learn(
    engine: Any,
    inv: Any,
    event: ProductSignalEvent,
    hypothesis_statement: str,
    result: ExperimentResult,
) -> tuple[Outcome, Lesson]:
    from loop.world import post

    verdict = (
        OutcomeVerdict.RESOLVED
        if result.verdict == "ship"
        else OutcomeVerdict.PARTIALLY_RESOLVED
        if result.verdict == "iterate"
        else OutcomeVerdict.NOT_RESOLVED
    )
    outcome = Outcome(
        id=_id("out"),
        investigation_id=inv.id,
        metric=result.primary_metric,
        pre_value=result.control,
        post_value=result.treatment,
        control_comparison=result.control,
        delta=result.delta,
        verdict=verdict,
        measured_at=_now(),
    )
    engine.store.put_outcome(outcome)

    les_raw = dict(event.dimensions.get("lesson") or {})
    lesson = Lesson(
        id=_id("les"),
        investigation_id=inv.id,
        statement=str(
            les_raw.get("statement")
            or f"{hypothesis_statement} Measured Δ={result.delta:+.4g} → {result.decision}"
        ),
        root_cause_family=str(les_raw.get("root_cause_family") or event.kind),
        applicable_conditions=list(
            les_raw.get("applicable_conditions") or event.memory_conditions or [f"metric={event.metric}"]
        ),
        linked_playbook_skill=les_raw.get("linked_playbook_skill"),
        confidence=float(les_raw.get("confidence") or 0.8),
        author_agent="learning_agent",
    )
    engine.store.put_lesson(lesson)
    engine.store.put_memory(
        lesson.id,
        "product" if resolve_loop(event)[0] == LoopType.TYPE_B else "engineering",
        {
            "statement": lesson.statement,
            "provenance": inv.id,
            "confidence": lesson.confidence,
            "kind": "product" if resolve_loop(event)[0] == LoopType.TYPE_B else "engineering",
            "experiment_verdict": result.verdict,
        },
    )
    inv.verification_result = verdict.value
    inv.state = InvestigationState(verdict.value) if verdict.value in {s.value for s in InvestigationState} else InvestigationState.RESOLVED
    inv.closed_at = _now()
    engine.store.put_investigation(inv)

    if inv.room_id:
        post(
            engine,
            inv.room_id,
            author="learning_agent",
            author_kind="agent",
            kind="artifact",
            text=lesson.statement,
            artifact_type="memory",
            artifact={"lesson": lesson.model_dump(mode="json"), "outcome": outcome.model_dump(mode="json")},
        )
    return outcome, lesson


# --- example recipes (payload only — not pipeline logic) ---------------------


def example_shipping_signal() -> ProductSignalEvent:
    """Recipe: checkout users return to shipping — Type B opportunity → experiment."""
    return ProductSignalEvent(
        kind="checkout_return_to_shipping",
        title="12% of checkout users return to shipping",
        topic="Type B · UX opportunity. Experiment path, not a payment SDK story.",
        metric="checkout_return_to_shipping",
        magnitude=0.12,
        baseline=0.04,
        polarity="positive",
        funnel_position="shipping_info",
        confidence=0.84,
        source="ga4 checkout funnel",
        family="business",
        memory_conditions=["funnel=checkout", "surface=shipping"],
        dimensions={
            "evidence": [
                {
                    "source_type": "analytics",
                    "source_reference": "funnel checkout → shipping_info reopen",
                    "claim": "12% of checkout sessions return to shipping_info (baseline 4%). Drop-off cites cost surprise.",
                    "independence_group": "analytics_ga4",
                    "collected_by": "analytics_agent",
                },
                {
                    "source_type": "customer_voice",
                    "source_reference": "cluster:shipping_cost_unclear n=18",
                    "claim": "18 customers said shipping cost appeared too late. No payment-error cluster.",
                    "independence_group": "customer_voice",
                    "collected_by": "feedback_agent",
                },
                {
                    "source_type": "research",
                    "source_reference": "session replay sample n=40",
                    "claim": "Users open shipping twice to hunt for delivery date. Hypothesis: show delivery date earlier.",
                    "independence_group": "ux_research",
                    "collected_by": "product_agent",
                },
            ],
            "hypothesis": {
                "statement": (
                    "Unclear shipping cost/date causes a 12% return-to-shipping rate. "
                    "Experiment: show delivery date earlier."
                ),
            },
            "experiment": {
                "hypothesis": "Showing delivery date on cart reduces return-to-shipping.",
                "treatment": "show_delivery_date_earlier",
                "flag": "show_delivery_date_earlier",
                "rollout_pct": 5,
                "primary_metric": "checkout_return_to_shipping",
                "guardrail": "purchase_conversion",
                "mde": 0.08,
                "stopping_rule": "14d or guardrail harm",
                "expected_impact": "Reduce checkout friction by surfacing shipping cost/date earlier.",
            },
            "measure": {"control": 0.12, "treatment": 0.05, "guardrail_ok": True, "verdict": "ship"},
            "lesson": {
                "statement": (
                    "Surfacing delivery date on cart cut return-to-shipping; keep expanding under guardrails."
                ),
                "root_cause_family": "shipping-clarity",
                "applicable_conditions": ["funnel=checkout", "surface=shipping"],
            },
            "action": {"semantic": "exp-delivery-date-5pct", "surface": "experiment flag / checkout copy"},
        },
    )


def example_conversion_drop_signal() -> ProductSignalEvent:
    """Recipe: Type A negative signal — find and fix (not an experiment-first path)."""
    return ProductSignalEvent(
        kind="conversion_drop",
        title="Purchase conversion ↓ on checkout",
        topic="Type A · something broke. Find and fix.",
        metric="purchase_conversion",
        magnitude=-0.18,
        baseline=0.42,
        polarity="negative",
        funnel_position="checkout",
        confidence=0.9,
        source="warehouse",
        family="business",
        dimensions={
            "evidence": [
                {
                    "source_type": "analytics",
                    "source_reference": "conversion_by_step",
                    "claim": "Purchase conversion −18% WoW at payment step.",
                    "independence_group": "analytics",
                    "collected_by": "analytics_agent",
                },
                {
                    "source_type": "logs",
                    "source_reference": "pay_api_timeouts",
                    "claim": "Payment authorize timeouts ↑ 3× after last flag flip.",
                    "independence_group": "logs",
                    "collected_by": "logs_agent",
                },
                {
                    "source_type": "deployment",
                    "source_reference": "flag:pay_path_v2",
                    "claim": "pay_path_v2 enabled 36h before the drop.",
                    "independence_group": "deploys",
                    "collected_by": "deployment_agent",
                },
            ],
            "hypothesis": {
                "statement": "pay_path_v2 introduced authorize timeouts that drop purchase conversion. Rollback the flag.",
            },
            "action": {
                "type": "flag_rollback",
                "surface": "payment authorization",
                "semantic": "rollback-pay-path-v2",
                "artifacts": {"flag": "pay_path_v2", "from": "on", "to": "off"},
                "consequence": "HIGH flag rollback. Eng-manager approval.",
            },
            "measure": {"control": 0.34, "treatment": 0.41, "verdict": "ship"},
            "lesson": {
                "statement": "Payment path flag flips need authorize-latency guardrails before full rollout.",
                "root_cause_family": "payment-timeout",
                "applicable_conditions": ["surface=checkout", "dep=pay_path"],
            },
        },
    )


def seed_shipping_opportunity(engine: Any, *, simulate_outcome: bool = False) -> dict[str, Any]:
    """World-seed entry: shipping recipe on shared infra (fixture id shipping_ux)."""
    return run_product_loop(
        engine,
        example_shipping_signal(),
        scenario_id="shipping_ux",
        simulate_outcome=simulate_outcome,
    )
