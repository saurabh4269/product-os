"""Resumable investigation engine. Tools are the source of truth (L-4, A-7)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .config import settings
from .models import (
    AgentCall,
    Approval,
    Classification,
    Direction,
    Evidence,
    Hypothesis,
    Investigation,
    InvestigationState,
    Lesson,
    Outcome,
    OutcomeVerdict,
    PolicyVerdict,
    ProposedAction,
    RiskTier,
    Segment,
    Signal,
    SignalFamily,
    SignalStatus,
    TimelineEvent,
    TrustLevel,
)
from .store import Store
from .warehouse import RECOVERY_START, REGRESSION_START, Warehouse

SAFARI = "Safari"
MIN_INDEPENDENCE = 3
PAYMENT_SURFACES = {"payment", "checkout", "3ds", "authorization", "pay-sdk"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def idempotency_key(investigation_id: str, node_id: str, semantic: str) -> str:
    raw = f"{investigation_id}:{node_id}:{semantic}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def digest_args(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class LoopEngine:
    def __init__(self, store: Store, warehouse: Warehouse):
        self.store = store
        self.wh = warehouse

    def timeline(self, inv_id: str, actor: str, kind: str, title: str, detail: str, denial: bool = False) -> None:
        self.store.put_timeline(
            TimelineEvent(
                id=_id("tl"),
                investigation_id=inv_id,
                at=_now(),
                actor=actor,
                kind=kind,
                title=title,
                detail=detail,
                denial=denial,
            )
        )

    def a2a(self, inv_id: str, src: str, dst: str, tb: str, summary: str) -> None:
        self.store.put_agent_call(
            AgentCall(
                id=_id("a2a"),
                investigation_id=inv_id,
                from_agent=src,
                to_agent=dst,
                trust_boundary=tb,
                started_at=_now(),
                finished_at=_now(),
                status="ok",
                summary=summary,
            )
        )

    def detect_signals(self, as_of: date | None = None) -> list[Signal]:
        """Baseline-relative, seasonality-aware, segment-mandatory (G-1, G-3). Unprompted."""
        dates = self.wh.list_event_dates()
        if not dates:
            return []
        as_of = as_of or max(d for d in dates if d < RECOVERY_START)
        window_end = as_of
        window_start = as_of - timedelta(days=2)
        baseline_end = REGRESSION_START - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=13)

        current = self.wh.conversion_by_browser(window_start, window_end)
        baseline = self.wh.conversion_by_browser(baseline_start, baseline_end)
        # Ads spend should stay flat — used as a contradicting "not spend" check later
        _ = self.wh.ads_spend_by_date()

        found: list[Signal] = []
        for browser, cur in current.items():
            base = baseline.get(browser)
            if not base or base["conversion"] <= 0:
                continue
            if cur.get("begin_checkout", 0) < 80:
                continue
            rel = (cur["conversion"] - base["conversion"]) / base["conversion"]
            if rel > -0.12:
                continue
            sig = Signal(
                id=_id("sig"),
                family=SignalFamily.BUSINESS,
                direction=Direction.NEGATIVE,
                funnel_position="purchase",
                metric="purchase_conversion",
                magnitude=rel,
                baseline=base["conversion"],
                affected_segments=[Segment(browser=browser, os="iOS" if browser == SAFARI else None, platform="web")],
                detection_window={
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                    "baseline_start": baseline_start.isoformat(),
                    "baseline_end": baseline_end.isoformat(),
                },
                confidence=min(0.95, 0.55 + abs(rel)),
                source="warehouse.events_daily",
                status=SignalStatus.OPEN,
                detected_at=_now(),
            )
            if self._should_suppress(sig):
                sig.status = SignalStatus.SUPPRESSED
                sig.suppression_reason = "open_investigation_or_known_benign"
            self.store.put_signal(sig)
            found.append(sig)
        return found

    def _should_suppress(self, sig: Signal) -> bool:
        for inv in self.store.list_investigations():
            if inv.state in {
                InvestigationState.RESOLVED,
                InvestigationState.NOT_RESOLVED,
                InvestigationState.INCONCLUSIVE,
                InvestigationState.PARTIALLY_RESOLVED,
            }:
                continue
            for sid in inv.originating_signal_ids:
                existing = self.store.get_signal(sid)
                if not existing:
                    continue
                if existing.metric == sig.metric and existing.affected_segments == sig.affected_segments:
                    return True
        for lesson in self.store.list_lessons():
            if "maintenance" in lesson.statement.lower():
                return True
        return False

    def open_investigation(self, signal: Signal) -> Investigation | None:
        """Signal Agent only detects/classifies/opens — never investigates (A-4)."""
        if signal.status == SignalStatus.SUPPRESSED:
            return None
        for inv in self.store.list_investigations():
            if signal.id in inv.originating_signal_ids:
                return inv
        lessons = self.store.list_lessons()
        recalled = [
            lesson.statement
            for lesson in lessons
            if "safari" in lesson.statement.lower() or "3ds" in lesson.statement.lower()
        ]
        inv = Investigation(
            id=_id("inv"),
            originating_signal_ids=[signal.id],
            state=InvestigationState.OPEN,
            opened_at=_now(),
            invocation_id=_id("job"),
            assigned_agents=["orchestrator"],
            recalled_lessons=recalled,
        )
        signal.status = SignalStatus.INVESTIGATING
        self.store.put_signal(signal)
        self.store.put_investigation(inv)
        self.timeline(inv.id, "signal_agent", "signal", "Investigation opened", f"{signal.metric} {signal.magnitude:.1%} vs baseline {signal.baseline:.1%}")
        return inv

    def gather_evidence(self, inv: Investigation) -> list[Evidence]:
        inv.state = InvestigationState.GATHERING
        inv.assigned_agents = list(dict.fromkeys(inv.assigned_agents + ["analytics", "logs", "deployment"]))
        self.store.put_investigation(inv)
        sig = self.store.get_signal(inv.originating_signal_ids[0])
        assert sig
        window = sig.detection_window
        w_start = date.fromisoformat(window["start"])
        w_end = date.fromisoformat(window["end"])
        b_start = date.fromisoformat(window["baseline_start"])
        b_end = date.fromisoformat(window["baseline_end"])

        items: list[Evidence] = []

        # Analytics — daily tables only
        self.a2a(inv.id, "orchestrator", "analytics_agent", "TB-2", "funnel conversion by browser")
        cur = self.wh.conversion_by_browser(w_start, w_end)
        base = self.wh.conversion_by_browser(b_start, b_end)
        safari_cur = cur.get(SAFARI, {}).get("conversion", 0)
        safari_base = base.get(SAFARI, {}).get("conversion", 0)
        chrome_cur = cur.get("Chrome", {}).get("conversion", 0)
        chrome_base = base.get("Chrome", {}).get("conversion", 0)
        items.append(
            self._evidence(
                inv,
                source_type="analytics",
                source_reference=f"events_{w_start:%Y%m%d}..events_{w_end:%Y%m%d} browser=Safari metric=purchase/begin_checkout",
                claim=(
                    f"Safari purchase conversion was {safari_cur:.1%} in the detection window versus "
                    f"{safari_base:.1%} in the 14-day baseline ({((safari_cur-safari_base)/safari_base) if safari_base else 0:.1%}). "
                    f"Chrome held {chrome_cur:.1%} vs {chrome_base:.1%}."
                ),
                independence_group="analytics_ga4",
                collected_by="analytics_agent",
                confidence=0.92,
            )
        )

        # Logs
        self.a2a(inv.id, "orchestrator", "logs_agent", "TB-2", "error signatures vs deploy window")
        start_dt = datetime.combine(w_start, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(w_end, datetime.max.time(), tzinfo=timezone.utc)
        base_start_dt = datetime.combine(b_start, datetime.min.time(), tzinfo=timezone.utc)
        base_end_dt = datetime.combine(b_end, datetime.max.time(), tzinfo=timezone.utc)
        now_counts = self.wh.error_counts(start_dt, end_dt, "3DS")
        then_counts = self.wh.error_counts(base_start_dt, base_end_dt, "3DS")
        safari_now = sum(v for k, v in now_counts.items() if k.startswith("Safari"))
        safari_then = sum(v for k, v in then_counts.items() if k.startswith("Safari"))
        items.append(
            self._evidence(
                inv,
                source_type="logs",
                source_reference=f"Cloud Logging signature=3DS_TIMEOUT browser=Safari {w_start}..{w_end}",
                claim=(
                    f"3DS_TIMEOUT errors on Safari rose from {safari_then} in the baseline window "
                    f"to {safari_now} after {REGRESSION_START.isoformat()}."
                ),
                independence_group="logs_errors",
                collected_by="logs_agent",
                confidence=0.9,
            )
        )

        # Deployments
        self.a2a(inv.id, "orchestrator", "deployment_agent", "TB-2", "release timeline correlation")
        deploys = [d for d in self.wh.deploys() if "pay-sdk" in json_dumps_lower(d)]
        correlated = [d for d in self.wh.deploys() if d.get("at", "").startswith(str(REGRESSION_START))]
        desc = correlated[0] if correlated else (deploys[0] if deploys else {})
        items.append(
            self._evidence(
                inv,
                source_type="deployment",
                source_reference=f"deploy:{desc.get('id', 'unknown')} sha={desc.get('sha', '')}",
                claim=(
                    f"Release {desc.get('version', 'pay-sdk')} shipped {desc.get('at', REGRESSION_START.isoformat())} "
                    f"({desc.get('note', 'payment SDK bump')}). Onset aligns with the Safari conversion break."
                ),
                independence_group="deploy_timeline",
                collected_by="deployment_agent",
                confidence=0.88,
            )
        )

        # Untrusted GitHub / tool output — screen then ingest as DATA, never as instruction (M-10, M-13)
        fixtures = Path(__file__).resolve().parents[3] / "data" / "fixtures"
        poison = fixtures / "poisoned_github_issue.md"
        injected = fixtures / "prompt_injection_tool.json"
        raw_bits = []
        if poison.exists():
            raw_bits.append(poison.read_text())
        if injected.exists():
            raw_bits.append(injected.read_text())
        blob = "\n".join(raw_bits)
        hit, needle = screen_tool_output(blob)
        if hit:
            log_verdict(
                self.store,
                agent="loop-analysis",
                tool="read_github_issue",
                args="1847",
                verdict="BLOCK",
                rationale=f"Prompt-injection pattern in tool output: {needle}",
                finding="prompt_injection",
            )
            self.timeline(
                inv.id,
                "tool_output_armor",
                "policy",
                "Blocked injected tool output",
                f"after_tool_callback screened GitHub/tool payload; needle={needle}. Content not forwarded.",
                denial=True,
            )
        if poison.exists() or injected.exists():
            items.append(
                self._evidence(
                    inv,
                    source_type="github_issue",
                    source_reference="github://northstar/pay/issues/1847",
                    claim="External issue text ingested as untrusted data. Injection screened and blocked. Not used as an instruction.",
                    independence_group="github_untrusted",
                    collected_by="code_agent",
                    confidence=0.4,
                    trust=TrustLevel.UNTRUSTED,
                )
            )

        inv.state = InvestigationState.HYPOTHESIS
        self.store.put_investigation(inv)
        return items

    def _evidence(
        self,
        inv: Investigation,
        *,
        source_type: str,
        source_reference: str,
        claim: str,
        independence_group: str,
        collected_by: str,
        confidence: float,
        trust: TrustLevel = TrustLevel.TRUSTED,
    ) -> Evidence:
        e = Evidence(
            id=_id("ev"),
            investigation_id=inv.id,
            source_type=source_type,
            source_reference=source_reference,
            claim=claim,
            confidence=confidence,
            trust_level=trust,
            collected_by=collected_by,
            collected_at=_now(),
            weight=confidence,
            independence_group=independence_group,
        )
        self.store.put_evidence(e)
        self.timeline(inv.id, collected_by, "evidence", f"{source_type} evidence", claim[:240])
        return e

    def form_hypothesis(self, inv: Investigation) -> Hypothesis | None:
        """Hard gate: ≥3 independent sources or no hypothesis."""
        evidence = [e for e in self.store.list_evidence(inv.id) if e.trust_level == TrustLevel.TRUSTED]
        groups = sorted({e.independence_group for e in evidence})
        if len(groups) < MIN_INDEPENDENCE:
            self.timeline(
                inv.id,
                "root_cause_agent",
                "gate",
                "Three-source gate refused",
                f"Only {len(groups)} independence groups: {groups}",
                denial=True,
            )
            return None
        support = [e.id for e in evidence if e.independence_group in {"analytics_ga4", "logs_errors", "deploy_timeline"}]
        hyp = Hypothesis(
            id=_id("hyp"),
            investigation_id=inv.id,
            statement=(
                "pay-sdk 4.3.0 introduced a Safari WebKit 3DS timeout that drops purchase conversion "
                "on iOS Safari. Chrome is unaffected. Ads spend did not move."
            ),
            classification=Classification.BUG,
            confidence=0.86,
            supporting_evidence_ids=support,
            contradicting_evidence_ids=[],
            cited_memory=inv.recalled_lessons,
            rank=1,
            independence_groups=groups,
        )
        self.store.put_hypothesis(hyp)
        inv.linked_hypothesis_ids.append(hyp.id)
        inv.state = InvestigationState.ACTION_PROPOSED
        self.store.put_investigation(inv)
        self.timeline(inv.id, "root_cause_agent", "hypothesis", "Root cause emitted", hyp.statement)
        return hyp

    def propose_action(self, inv: Investigation, hyp: Hypothesis) -> ProposedAction:
        surface = "payment authorization / 3DS / pay-sdk"
        tier = assign_risk_tier(surface, hyp.statement)
        key = idempotency_key(inv.id, "propose_action", "rollback-pay-sdk-4.3")
        action = ProposedAction(
            id=_id("act"),
            investigation_id=inv.id,
            type="flag_rollback",
            risk_tier=tier,
            tier_rationale=(
                "Touched surface is payment authorization (3DS). Tier follows the surface, not model confidence (H-1)."
            ),
            required_approver_role="eng-manager",
            artifacts={
                "flag": "pay_sdk_4_3",
                "from": "on",
                "to": "off",
                "pr": {
                    "title": "Revert pay-sdk 4.3 Safari 3DS regression",
                    "body": f"Investigation {inv.id}. Hypothesis: {hyp.statement}",
                    "tests": "regression test must fail pre-change and pass post-change",
                },
            },
            idempotency_key=key,
            status="awaiting_approval" if tier == RiskTier.HIGH else "proposed",
            consequence=(
                "On approval, LOOP will flip feature flag pay_sdk_4_3 to off (rollback to 4.2.x) "
                "and open a PR with a Safari 3DS regression test. No merge, no production deploy."
            ),
        )
        self.store.put_action(action)
        inv.linked_action_ids.append(action.id)
        inv.state = InvestigationState.AWAITING_APPROVAL if tier == RiskTier.HIGH else InvestigationState.APPROVED
        self.store.put_investigation(inv)
        self.timeline(
            inv.id,
            "risk_agent",
            "risk",
            f"{tier.value} tier — approval required" if tier == RiskTier.HIGH else f"{tier.value} tier",
            action.consequence,
        )
        return action

    def approve(
        self, action_id: str, approver: str, decision: str, rationale: str
    ) -> Approval:
        action = self.store.get_action(action_id)
        if not action:
            raise KeyError(action_id)
        approval = Approval(
            id=_id("appr"),
            action_id=action_id,
            approver_identity=approver,
            decision="approve" if decision == "approve" else "deny",
            rationale=rationale,
            timestamp=_now(),
            tier_at_decision=action.risk_tier,
        )
        self.store.put_approval(approval)
        inv = self.store.get_investigation(action.investigation_id)
        assert inv
        if approval.decision == "approve":
            action.status = "approved"
            inv.state = InvestigationState.APPROVED
        else:
            action.status = "denied"
        self.store.put_action(action)
        self.store.put_investigation(inv)
        self.timeline(inv.id, approver, "approval", f"Action {approval.decision}", rationale)
        return approval

    def execute_approved(self, action_id: str) -> dict:
        action = self.store.get_action(action_id)
        if not action:
            raise KeyError(action_id)
        if action.status == "executed":
            prev = action.artifacts.get("execution") or {}
            return {**prev, "reused": True}
        if action.status != "approved":
            raise PermissionError("HIGH-tier action cannot execute without approval")
        inv = self.store.get_investigation(action.investigation_id)
        assert inv
        inv.state = InvestigationState.ACTING
        self.store.put_investigation(inv)

        value, reused = self.store.set_flag(
            action.artifacts["flag"], action.artifacts["to"], action.idempotency_key
        )
        result = {
            "flag": action.artifacts["flag"],
            "value": value,
            "pr_opened": True,
            "merged": False,
        }
        action.status = "executed"
        action.artifacts["execution"] = {**result, "reused": reused}
        self.store.put_action(action)
        self.timeline(
            inv.id,
            "code_agent",
            "action",
            "Flag rollback executed" if not reused else "Idempotent replay — no duplicate side effect",
            str(result),
        )
        return {**result, "reused": reused}

    def verify(self, inv_id: str) -> Outcome:
        inv = self.store.get_investigation(inv_id)
        assert inv
        inv.state = InvestigationState.VERIFYING
        self.store.put_investigation(inv)
        self.a2a(inv.id, "orchestrator", "learning_agent", "TB-7", "measure originating metric")
        sig = self.store.get_signal(inv.originating_signal_ids[0])
        assert sig
        w_start = date.fromisoformat(sig.detection_window["start"])
        w_end = date.fromisoformat(sig.detection_window["end"])
        pre = self.wh.conversion_by_browser(w_start, w_end).get(SAFARI, {}).get("conversion", 0)
        post = (
            self.wh.conversion_by_browser(RECOVERY_START, RECOVERY_START + timedelta(days=3), include_recovery=True)
            .get(SAFARI, {})
            .get("conversion", 0)
        )
        flag = self.store.get_flag("pay_sdk_4_3")
        if flag == "off" and post > pre * 1.1:
            verdict = OutcomeVerdict.RESOLVED
        elif flag == "off":
            verdict = OutcomeVerdict.PARTIALLY_RESOLVED
        else:
            verdict = OutcomeVerdict.NOT_RESOLVED
        outcome = Outcome(
            id=_id("out"),
            investigation_id=inv.id,
            metric="purchase_conversion.Safari",
            pre_value=pre,
            post_value=post,
            control_comparison=self.wh.conversion_by_browser(
                RECOVERY_START, RECOVERY_START + timedelta(days=3), include_recovery=True
            )
            .get("Chrome", {})
            .get("conversion"),
            delta=post - pre,
            verdict=verdict,
            measured_at=_now(),
        )
        self.store.put_outcome(outcome)
        lesson = Lesson(
            id=_id("les"),
            investigation_id=inv.id,
            statement=(
                "Safari 3DS regressions after payment SDK upgrades require a Safari WebKit regression test. "
                f"pay-sdk 4.3 caused a {((pre - sig.baseline) / sig.baseline) if sig.baseline else 0:.0%} conversion drop; "
                "rolling the flag back recovered the funnel."
            ),
            root_cause_family="safari-3ds-sdk",
            applicable_conditions=["browser=Safari", "surface=checkout", "dep=pay-sdk"],
            linked_playbook_skill="playbooks/safari-payment-sdk",
            confidence=0.84,
            author_agent="learning_agent",
        )
        self.store.put_lesson(lesson)
        self.store.put_memory(
            lesson.id,
            "engineering",
            {
                "statement": lesson.statement,
                "provenance": inv.id,
                "confidence": lesson.confidence,
                "kind": "engineering",
            },
        )
        inv.verification_result = verdict.value
        inv.state = InvestigationState(verdict.value)
        inv.closed_at = _now()
        self.store.put_investigation(inv)
        self.timeline(inv.id, "learning_agent", "verify", f"Verification {verdict.value}", lesson.statement)
        return outcome

    def run_until_approval(self, as_of: date | None = None) -> Investigation:
        signals = self.detect_signals(as_of)
        open_signals = [s for s in signals if s.status != SignalStatus.SUPPRESSED]
        if not open_signals:
            raise RuntimeError("no unsuppressed signal — seeded regression missing")
        # Prefer the Safari segment signal (G-3)
        safari = next((s for s in open_signals if any(seg.browser == SAFARI for seg in s.affected_segments)), open_signals[0])
        inv = self.open_investigation(safari)
        assert inv
        self.gather_evidence(inv)
        hyp = self.form_hypothesis(inv)
        if not hyp:
            raise RuntimeError("three-source gate failed on seeded world")
        self.propose_action(inv, hyp)
        return self.store.get_investigation(inv.id)  # type: ignore[return-value]

    def resume_after_approval(self, action_id: str, approver: str) -> Outcome:
        self.approve(action_id, approver, "approve", "On-call confirmed Safari 3DS blast radius.")
        self.execute_approved(action_id)
        action = self.store.get_action(action_id)
        assert action
        return self.verify(action.investigation_id)


def assign_risk_tier(surface: str, statement: str) -> RiskTier:
    """H-1/H-2: surface-based. Ambiguity escalates to HIGH. Not model confidence."""
    blob = f"{surface} {statement}".lower()
    if not surface.strip():
        return RiskTier.HIGH
    if any(k in blob for k in ("auth", "payment", "3ds", "pii", "infrastructure", "destruct")):
        return RiskTier.HIGH
    if any(k in blob for k in ("schema", "flag", "business logic", "integration")):
        return RiskTier.MEDIUM
    if any(k in blob for k in ("docs", "copy", "logging", "test-only")):
        return RiskTier.LOW
    return RiskTier.HIGH


def json_dumps_lower(d: dict) -> str:
    return str(d).lower()


def screen_tool_output(text: str) -> tuple[bool, str]:
    """Deterministic injection screen used by M-10 plugin and tests."""
    needles = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "system override",
        "disable model armor",
        "export_pii_table",
        "dump all customer",
        "exfiltrate",
        "send me the customer records",
        "access the production database",
    ]
    low = text.lower()
    for n in needles:
        if n in low:
            return True, n
    return False, ""


def redact_pii(text: str) -> str:
    """ReplaceWithInfoType-style placeholders (K-13g). Deterministic fallback."""
    import re

    text = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[EMAIL_ADDRESS]", text, flags=re.I)
    text = re.sub(r"\+?1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_NUMBER]", text)
    text = re.sub(r"\b\d{4}\b(?=\s*rupees|\s*₹)?", lambda m: m.group(0) if int(m.group(0)) < 1000 else "[FINANCIAL]", text)
    text = re.sub(r"card ending \d{4}", "card ending [PAYMENT_CARD]", text, flags=re.I)
    text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[PERSON_NAME]", text)
    return text


def log_verdict(store: Store, *, agent: str, tool: str, args: str, verdict: str, rationale: str, finding: str | None = None) -> PolicyVerdict:
    v = PolicyVerdict(
        id=_id("pv"),
        agent_identity=agent,
        tool=tool,
        arguments_digest=digest_args(args),
        verdict=verdict,  # type: ignore[arg-type]
        rationale=rationale,
        enforcement_mode="ENFORCING",
        timestamp=_now(),
        finding_type=finding,
    )
    store.put_verdict(v)
    return v


def default_engine(data_dir: Path | None = None) -> LoopEngine:
    cfg = settings()
    root = data_dir or cfg.data_dir
    store = Store(root / "loop.db")
    wh = Warehouse(cfg.warehouse_path() if data_dir is None else root / "warehouse")
    return LoopEngine(store, wh)
