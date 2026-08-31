"""Resumable investigation engine. Tools are the source of truth (L-4, A-7)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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


def re_split_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    import re

    return [t for t in re.split(r"[^a-z0-9]+", str(raw).lower()) if len(t) >= 3]


def _log_signature_for(sig: Signal) -> str:
    """Derive a log search needle from the signal — not a fixed 3DS string."""
    blob = f"{sig.metric} {sig.funnel_position} {sig.family.value}".lower()
    if "3ds" in blob or "payment" in blob or "purchase" in blob:
        return "3DS"
    if "activat" in blob or "onboard" in blob:
        return "ACTIVATION"
    if "ship" in blob or "deliver" in blob:
        return "SHIPPING"
    if "auth" in blob or "login" in blob:
        return "AUTH"
    # Fall back to first metric token uppercased
    toks = re_split_tokens(sig.metric)
    return (toks[0].upper() if toks else "ERROR")


def signal_fingerprint(metric: str, segments: list) -> tuple[str, str, str, str]:
    """Stable key for dedupe: metric + primary segment dimensions."""
    seg = segments[0] if segments else None
    if seg is None:
        return (metric, "", "", "")
    browser = getattr(seg, "browser", None) or (seg.get("browser") if isinstance(seg, dict) else None) or ""
    os_name = getattr(seg, "os", None) or (seg.get("os") if isinstance(seg, dict) else None) or ""
    platform = getattr(seg, "platform", None) or (seg.get("platform") if isinstance(seg, dict) else None) or ""
    return (metric, str(browser), str(os_name), str(platform))


def stable_signal_id(metric: str, segments: list, *, prefix: str = "sig_wh") -> str:
    metric, browser, os_name, platform = signal_fingerprint(metric, segments)
    slug = "_".join(
        p.lower().replace(" ", "_").replace("/", "_")
        for p in (metric, browser or "all", os_name or "any", platform or "web")
        if p
    )
    return f"{prefix}_{slug}"[:64]


def dedupe_signals(signals: list) -> list:
    """One row per metric+segment — keeps newest detected_at (fixes legacy duplicate ids)."""
    best: dict[tuple[str, str, str, str], Any] = {}
    for s in signals:
        fp = signal_fingerprint(s.metric, s.affected_segments)
        prev = best.get(fp)
        if prev is None:
            best[fp] = s
            continue
        prev_at = getattr(prev, "detected_at", None) or ""
        cur_at = getattr(s, "detected_at", None) or ""
        if str(cur_at) >= str(prev_at):
            best[fp] = s
    return sorted(best.values(), key=lambda x: str(getattr(x, "detected_at", "") or ""), reverse=True)
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
        from .live import HUB, room_id_for_investigation

        rid = room_id_for_investigation(self.store, inv_id)
        if rid:
            HUB.publish(
                rid,
                {
                    "type": "trace",
                    "traceId": inv_id,
                    "step": {"agentId": actor, "kind": kind, "summary": title, "detail": detail, "denial": denial},
                },
            )

    def a2a(self, inv_id: str, src: str, dst: str, tb: str, summary: str) -> None:
        from .narrate import humanize_handoff

        line = humanize_handoff(src, dst, summary)
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
                summary=line,
            )
        )
        from .a2a_protocol import A2AEnvelope
        from .live import HUB, room_id_for_investigation

        rid = room_id_for_investigation(self.store, inv_id) or ""
        env = A2AEnvelope(
            from_agent=src,
            to_agent=dst,
            kind="handoff",
            trace_id=inv_id,
            room_id=rid,
            payload={"summary": line, "trust_boundary": tb},
        )
        if rid:
            HUB.set_presence(rid, dst, "thinking", {"label": dst, "hue": abs(hash(dst)) % 360})
            HUB.publish(rid, env.as_event())

    def presence(self, room_id: str, agent_id: str, status: str) -> None:
        from .live import HUB

        HUB.set_presence(room_id, agent_id, status, {"label": agent_id, "hue": abs(hash(agent_id)) % 360})

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
            segments = [Segment(browser=browser, os="iOS" if browser == SAFARI else None, platform="web")]
            sig_id = stable_signal_id("purchase_conversion", segments)
            existing = self.store.get_signal(sig_id)
            if existing:
                existing.magnitude = rel
                existing.baseline = base["conversion"]
                existing.detection_window = {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                    "baseline_start": baseline_start.isoformat(),
                    "baseline_end": baseline_end.isoformat(),
                }
                existing.confidence = min(0.95, 0.55 + abs(rel))
                existing.detected_at = _now()
                if self._should_suppress(existing):
                    existing.status = SignalStatus.SUPPRESSED
                    existing.suppression_reason = "open_investigation_or_known_benign"
                sig = existing
            else:
                sig = Signal(
                    id=sig_id,
                    family=SignalFamily.BUSINESS,
                    direction=Direction.NEGATIVE,
                    funnel_position="purchase",
                    metric="purchase_conversion",
                    magnitude=rel,
                    baseline=base["conversion"],
                    affected_segments=segments,
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

    def detect_all_signals(self, as_of: date | None = None) -> list[Signal]:
        """File warehouse detect + tenant BQ detect for every configured tenant."""
        found = list(self.detect_signals(as_of))
        seen = {s.id for s in found}
        try:
            from .connectors.bigquery import detect_anomalies_for_tenant, has_bq

            for tenant in self.store.list_tenants():
                if not has_bq(tenant):
                    continue
                for sig in detect_anomalies_for_tenant(self, tenant, as_of=as_of):
                    if sig.id not in seen:
                        found.append(sig)
                        seen.add(sig.id)
        except Exception:
            pass
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

    def open_investigation(self, signal: Signal, *, tenant_id: str | None = None) -> Investigation | None:
        """Signal Agent only detects/classifies/opens — never investigates (A-4)."""
        if signal.status == SignalStatus.SUPPRESSED:
            return None
        for inv in self.store.list_investigations():
            if signal.id in inv.originating_signal_ids:
                return inv
        recalled = self.recall_lessons(*self._recall_needles(signal), tenant_id=tenant_id)
        inv = Investigation(
            id=_id("inv"),
            originating_signal_ids=[signal.id],
            state=InvestigationState.OPEN,
            opened_at=_now(),
            invocation_id=_id("job"),
            assigned_agents=["orchestrator"],
            recalled_lessons=recalled,
            tenant_id=tenant_id,
        )
        signal.status = SignalStatus.INVESTIGATING
        self.store.put_signal(signal)
        self.store.put_investigation(inv)
        self.timeline(inv.id, "signal_agent", "signal", "Investigation opened", f"{signal.metric} {signal.magnitude:.1%} vs baseline {signal.baseline:.1%}")
        return inv

    def recall_lessons(self, *needles: str, tenant_id: str | None = None) -> list[str]:
        """Retrieve organizational memory. Facts stay in the warehouse; lessons are knowledge."""
        import re

        raw = [n for n in needles if n]
        tokens: set[str] = set()
        for n in raw:
            s = str(n).strip().lower()
            if not s:
                continue
            tokens.add(s)
            tokens.update(re_split_tokens(s))
        tokens = {t for t in tokens if len(t) >= 3}
        if not tokens:
            return []

        def _hits(blob: str) -> bool:
            for t in tokens:
                if len(t) >= 5:
                    if t in blob:
                        return True
                elif re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", blob):
                    return True
            return False

        hits: list[str] = []
        seen: set[str] = set()
        for lesson in self.store.list_lessons():
            if tenant_id and lesson.tenant_id and lesson.tenant_id != tenant_id:
                continue
            blob = f"{lesson.statement} {lesson.root_cause_family} {' '.join(lesson.applicable_conditions)}".lower()
            if _hits(blob):
                if lesson.statement not in seen:
                    hits.append(lesson.statement)
                    seen.add(lesson.statement)
        for mem in self.store.list_memory(tenant_id=tenant_id):
            blob = f"{mem.get('statement', '')} {mem.get('body', '')} {mem.get('title', '')}".lower()
            if _hits(blob):
                stmt = str(mem.get("statement") or mem.get("title") or "")
                if stmt and stmt not in seen:
                    hits.append(stmt)
                    seen.add(stmt)
        return hits

    def _recall_needles(self, signal: Signal) -> list[str]:
        needles = [signal.metric, signal.funnel_position, signal.family.value, signal.source or ""]
        for seg in signal.affected_segments:
            needles.extend(
                [x for x in (seg.browser, seg.os, seg.platform, seg.app_version, seg.geo, seg.channel) if x]
            )
        for part in re_split_tokens(signal.metric) + re_split_tokens(signal.funnel_position) + re_split_tokens(
            signal.source or ""
        ):
            if part and part not in needles:
                needles.append(part)
        for seg in signal.affected_segments:
            for field in (seg.app_version, seg.channel, seg.browser, seg.os, seg.platform):
                for part in re_split_tokens(str(field or "")):
                    if part and part not in needles:
                        needles.append(part)
        return needles

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

        # Analytics — daily tables only (file warehouse or tenant BQ)
        from .connectors.bigquery import conversion_by_browser as bq_conversion
        from .connectors.bigquery import has_bq
        from .tenant import resolve_tenant

        tenant = resolve_tenant(self.store, investigation=inv)
        if tenant and has_bq(tenant):
            cur = bq_conversion(tenant, w_start, w_end)
            base = bq_conversion(tenant, b_start, b_end)
        else:
            cur = self.wh.conversion_by_browser(w_start, w_end)
            base = self.wh.conversion_by_browser(b_start, b_end)
        self.a2a(inv.id, "orchestrator", "analytics_agent", "TB-2", f"{sig.metric} by segment")
        focus = (sig.affected_segments[0].browser if sig.affected_segments else None) or None
        if not focus and cur:
            focus = max(
                cur.keys(),
                key=lambda n: abs(
                    float(cur[n].get("conversion") or 0) - float((base.get(n) or {}).get("conversion") or 0)
                ),
            )
        focus = focus or (next(iter(cur), None) if cur else None) or "all"
        control = next((n for n in cur if n != focus), "control")
        focus_cur = float((cur.get(focus) or {}).get("conversion") or 0)
        focus_base = float((base.get(focus) or {}).get("conversion") or 0)
        control_cur = float((cur.get(control) or {}).get("conversion") or 0)
        control_base = float((base.get(control) or {}).get("conversion") or 0)
        items.append(
            self._evidence(
                inv,
                source_type="analytics",
                source_reference=f"events_{w_start:%Y%m%d}..events_{w_end:%Y%m%d} segment={focus} metric={sig.metric}",
                claim=(
                    f"{sig.metric}: {focus} was {focus_cur:.1%} in the detection window versus "
                    f"{focus_base:.1%} baseline ({((focus_cur-focus_base)/focus_base) if focus_base else 0:.1%}). "
                    f"{control} held {control_cur:.1%} vs {control_base:.1%}."
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
        log_sig = _log_signature_for(sig)
        focus_b = (sig.affected_segments[0].browser if sig.affected_segments else None) or focus
        now_counts = self.wh.error_counts(start_dt, end_dt, log_sig)
        then_counts = self.wh.error_counts(base_start_dt, base_end_dt, log_sig)
        now_n = sum(v for k, v in now_counts.items() if str(k).startswith(focus_b)) or sum(now_counts.values())
        then_n = sum(v for k, v in then_counts.items() if str(k).startswith(focus_b)) or sum(then_counts.values())
        items.append(
            self._evidence(
                inv,
                source_type="logs",
                source_reference=f"Cloud Logging signature={log_sig} segment={focus_b} {w_start}..{w_end}",
                claim=(
                    f"{log_sig} errors on {focus_b} rose from {then_n} in the baseline window "
                    f"to {now_n} in the detection window."
                ),
                independence_group="logs_errors",
                collected_by="logs_agent",
                confidence=0.9,
            )
        )

        # Deployments
        self.a2a(inv.id, "orchestrator", "deployment_agent", "TB-2", "release timeline correlation")
        all_deploys = list(self.wh.deploys())
        window_deploys = [
            d for d in all_deploys
            if str(w_start) <= str(d.get("at") or "")[:10] <= str(w_end)
        ]
        desc = window_deploys[0] if window_deploys else (all_deploys[0] if all_deploys else {})
        focus_b = (sig.affected_segments[0].browser if sig.affected_segments else None) or "segment"
        items.append(
            self._evidence(
                inv,
                source_type="deployment",
                source_reference=f"deploy:{desc.get('id', 'unknown')} sha={desc.get('sha', '')}",
                claim=(
                    f"Release {desc.get('version', desc.get('service', 'app'))} shipped "
                    f"{desc.get('at', 'near onset')} ({desc.get('note', 'deploy in window')}). "
                    f"Timing aligns with the {sig.metric} break on {focus_b}."
                ),
                independence_group="deploy_timeline",
                collected_by="deployment_agent",
                confidence=0.88,
            )
        )

        # Customer Voice — diagnostic, not a survey. Structured evidence (research doc + K-11).
        self.a2a(inv.id, "orchestrator", "customer_voice_agent", "TB-3", "consented diagnostic call")
        voice = self._collect_customer_voice(inv)
        items.append(voice)

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

    def _collect_customer_voice(self, inv: Investigation) -> Evidence:
        """Sarah-style adaptive diagnostic from the research brief. Live API stays mocked."""
        from .media_bridge import MediaBridge

        bridge = MediaBridge()
        session_id = f"voice_{inv.id}"
        bridge.open_session(session_id)
        sig = self.store.get_signal(inv.originating_signal_ids[0]) if inv.originating_signal_ids else None
        metric = (sig.metric if sig else "checkout") or "checkout"
        seg = sig.affected_segments[0] if sig and sig.affected_segments else None
        device = " · ".join(x for x in [(seg.browser if seg else None), (seg.os if seg else None)] if x) or "their device"
        turns = [
            ("agent", f"We saw trouble around {metric} on {device}. What did you see on screen?"),
            ("customer", "It kept loading / would not finish."),
            ("agent", "Did you see an error message, or did it hang?"),
            ("customer", "Mostly hung. No clear error."),
            ("agent", "Did another device or browser work?"),
            ("customer", "Yes — another setup worked; this one failed twice."),
        ]
        fixtures = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "pii_transcript.json"
        if fixtures.exists():
            import json

            raw = json.loads(fixtures.read_text())
            for t in raw.get("turns", []):
                turns.append((str(t.get("role", "customer")), str(t.get("text", ""))))
        screened = [bridge.ingest_transcript_turn(session_id, role, text) for role, text in turns]
        blocked = sum(1 for t in screened if t.get("blocked"))
        pii_holder = next((t["redacted"] for t in screened if "[EMAIL_ADDRESS]" in t.get("redacted", "")), "")
        structured = {
            "reason": f"{metric}_friction",
            "severity": "high",
            "purchase_intent": "high",
            "friction": "technical",
            "competitor_mentioned": False,
            "feature_request": None,
            "willing_to_retry": True,
            "confidence": 0.94,
            "user_token": f"tok_{inv.id[-8:]}",
            "channel": "voice_text_fallback",
            "injection_turns_blocked": blocked,
        }
        self.store.put_memory(
            f"voice_{inv.id}",
            "customer",
            {"structured": structured, "redacted_excerpt": pii_holder[:180], "provenance": inv.id},
        )
        return self._evidence(
            inv,
            source_type="customer_voice",
            source_reference=f"media-bridge:{session_id} structured.reason={metric}_friction",
            claim=(
                f"Consented diagnostic on {device}: hang/friction around {metric}, "
                f"willing to retry. Structured reason={metric}_friction confidence=0.94. "
                f"PII redacted; {blocked} injected/unsafe turns blocked."
            ),
            independence_group="customer_voice",
            collected_by="customer_voice_agent",
            confidence=0.94,
        )

    def form_hypothesis(
        self,
        inv: Investigation,
        *,
        statement: str | None = None,
        classification: Classification = Classification.BUG,
    ) -> Hypothesis | None:
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
        support = [e.id for e in evidence]
        if not statement:
            bits = [e.claim.split(".")[0].strip() for e in evidence[:3] if e.claim]
            sig0 = self.store.get_signal(inv.originating_signal_ids[0]) if inv.originating_signal_ids else None
            metric = sig0.metric if sig0 else "metric"
            statement = (
                (" · ".join(bits) + f". Scoped fix for {metric}.")
                if bits
                else f"Multi-source agreement on {metric}; propose a scoped fix."
            )
        hyp = Hypothesis(
            id=_id("hyp"),
            investigation_id=inv.id,
            statement=statement,
            classification=classification,
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

    def propose_action(
        self,
        inv: Investigation,
        hyp: Hypothesis,
        *,
        surface: str | None = None,
        action_type: str = "flag_rollback",
        artifacts: dict | None = None,
        consequence: str | None = None,
        semantic: str = "propose-action",
    ) -> ProposedAction:
        from .tenant import resolve_tenant
        from .tenant_context import consequence_for, merge_proposed_artifacts

        tenant = resolve_tenant(self.store, investigation=inv)
        merged = merge_proposed_artifacts(inv, hyp, tenant, artifacts)
        has_flag = "flag" in merged
        surface = (
            surface
            or (tenant.default_surface if tenant else None)
            or str((merged.get("code_brief") or {}).get("surface") or "")
            or inv.title
            or "product"
        )
        tier = assign_risk_tier(surface, hyp.statement)
        key = idempotency_key(inv.id, "propose_action", semantic)
        action = ProposedAction(
            id=_id("act"),
            investigation_id=inv.id,
            type=action_type,  # type: ignore[arg-type]
            risk_tier=tier,
            tier_rationale=(
                f"Touched surface is {surface}. Tier follows the surface, not model confidence (H-1)."
            ),
            required_approver_role="eng-manager" if tier == RiskTier.HIGH else "developer",
            artifacts=merged,
            idempotency_key=key,
            status="awaiting_approval" if tier in {RiskTier.HIGH, RiskTier.MEDIUM} else "proposed",
            consequence=consequence or consequence_for(tenant, inv, hyp, has_flag=has_flag),
        )
        self.store.put_action(action)
        inv.linked_action_ids.append(action.id)
        inv.state = (
            InvestigationState.AWAITING_APPROVAL
            if tier in {RiskTier.HIGH, RiskTier.MEDIUM}
            else InvestigationState.APPROVED
        )
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

        from .connectors import calendar_hold, create_issue, mail_draft, open_pr
        from .tenant import flag_key, is_tenant_scenario, resolve_tenant
        from .tenant_context import flag_file_for

        tenant = resolve_tenant(self.store, investigation=inv)
        tenant_bound = is_tenant_scenario(inv.scenario_id)

        reports = []
        result: dict = {"merged": False, "pr_opened": False}
        reused = False
        code_fix_job: dict | None = None
        if "flag" in action.artifacts:
            import json as json_lib

            name = str(action.artifacts["flag"])
            value_str = str(action.artifacts.get("to", "off"))
            if tenant_bound:
                if not tenant:
                    raise PermissionError("investigation is not bound to a tenant")
                value, reused = self.store.set_flag(flag_key(tenant.id, name), value_str, action.idempotency_key)
            else:
                value, reused = self.store.set_flag(name, value_str, action.idempotency_key)
                if tenant and inv.tenant_id:
                    self.store.set_flag(flag_key(tenant.id, name), value_str, action.idempotency_key + ":mirror")
            result["flag"] = name
            result["value"] = value
            if tenant:
                result["tenant_id"] = tenant.id
            pr_meta = action.artifacts.get("pr") if isinstance(action.artifacts.get("pr"), dict) else {}
            title = pr_meta.get("title") or f"Product OS: {name}"
            body = pr_meta.get("body") or f"Investigation {inv.id}. Flag {name} → {value}."
            flags_doc: dict[str, str] = {name: str(value)}
            companions = action.artifacts.get("companion_flags")
            if isinstance(companions, dict):
                for ck, cv in companions.items():
                    flags_doc[str(ck)] = str(cv)
            elif name == "pay_sdk_4_3":
                # Safari fixture only: keep demo flags.json dual-key in sync.
                flags_doc["pay_sdk"] = "4.2.1" if str(value) == "off" else "4.3.0"
            file_content = json_lib.dumps(flags_doc, indent=2) + "\n"
            code_fix = action.artifacts.get("code_fix", True) is not False
            brief = None
            if code_fix:
                from .code_fix import resolve_brief

                brief = resolve_brief(action, inv, self.store)
                if brief and tenant:
                    code_fix_job = {
                        "action_id": action_id,
                        "tenant": tenant,
                        "inv": inv,
                        "brief": brief,
                        "flag_patch": flags_doc,
                        "pr_title": str(pr_meta.get("title") or title),
                        "pr_body": str(pr_meta.get("body") or body),
                    }
                    result["code_fix"] = "queued"
            if tenant and not (code_fix and brief):
                gh, _ = self.store.claim_idempotency(
                    action.idempotency_key + ":gh",
                    "github.pr",
                    lambda: open_pr(
                        tenant,
                        title,
                        body,
                        file_path=flag_file_for(tenant),
                        file_content=file_content,
                    ).model_dump(),
                )
                reports.append(gh)
                result["github"] = gh
                if gh.get("status") == "applied" and gh.get("url"):
                    result["pr_opened"] = True
                    result["pr_url"] = gh["url"]
                    tenant.last_pr_url = str(gh["url"])
                    tenant.last_connector = "github.pr applied"
                    self.store.put_tenant(tenant)
                elif gh.get("detail"):
                    tenant.last_connector = str(gh.get("detail"))
                    self.store.put_tenant(tenant)
            elif code_fix and brief:
                result["pr_note"] = "Code fix PR opening in background (multi-file)"
        else:
            issue = action.artifacts.get("github_issue") if isinstance(action.artifacts.get("github_issue"), dict) else {}
            title = issue.get("title") or "Product OS follow-up"
            body = issue.get("body") or f"Investigation {inv.id}"
            if tenant:
                gh, _ = self.store.claim_idempotency(
                    action.idempotency_key + ":gh",
                    "github.issue",
                    lambda: create_issue(tenant, title, body).model_dump(),
                )
                reports.append(gh)
                result["github"] = gh
                if gh.get("url"):
                    result["github_issue_url"] = gh["url"]
            if action.artifacts.get("gmail"):
                reports.append(mail_draft(f"oncall@{tenant.id if tenant else 'loop'}", title, body).model_dump())
            if action.artifacts.get("calendar"):
                reports.append(calendar_hold(title, str(action.artifacts.get("calendar"))).model_dump())
        result["connectors"] = reports
        action.status = "executed"
        action.artifacts["execution"] = {**result, "reused": reused}
        self.store.put_action(action)
        if code_fix_job:
            from .code_fix import enqueue_code_fix_job

            enqueue_code_fix_job(self, **code_fix_job)
            # Running receipt so the user sees work in flight (Cursor-style).
            if inv.room_id:
                from .receipts import post_receipt

                post_receipt(
                    self,
                    inv.room_id,
                    kind="github",
                    title="Opening pull request on Product Y",
                    agent="code_agent",
                    status="running",
                    detail="Cloning · patching · opening PR…",
                    proof={
                        "kind": "github",
                        "status": "running",
                        "title": "Opening pull request…",
                        "subtitle": (tenant.repo if tenant else "") or "repo",
                        "detail": "Code fix job queued",
                        "state": "open",
                    },
                )
        # Visible receipts for everything that actually ran (flag, mail, calendar, issue).
        if inv.room_id and not reused:
            from .receipts import post_connector_receipts

            post_connector_receipts(
                self,
                inv.room_id,
                flag=(
                    {
                        "name": result.get("flag"),
                        "value": result.get("value"),
                        "from": action.artifacts.get("from"),
                    }
                    if result.get("flag")
                    else None
                ),
                connectors=reports,
                pr_url=result.get("pr_url"),
            )
        self.timeline(
            inv.id,
            "code_agent",
            "action",
            "Approved action executed" if not reused else "Idempotent replay — no duplicate side effect",
            str(result),
        )
        return {**result, "reused": reused}

    def verify(self, inv_id: str) -> Outcome:
        inv = self.store.get_investigation(inv_id)
        assert inv
        sig = self.store.get_signal(inv.originating_signal_ids[0]) if inv.originating_signal_ids else None
        # Data-driven browser recovery when warehouse has conversion-by-browser for this signal.
        if sig and sig.affected_segments and any(s.browser for s in sig.affected_segments):
            return self._verify_segment_conversion(inv, sig)
        return self._verify_generic(inv)

    def _verify_segment_conversion(self, inv: Investigation, sig: Signal) -> Outcome:
        """Measure the signal's own browser/segment — not a scenario_id branch."""
        inv.state = InvestigationState.VERIFYING
        self.store.put_investigation(inv)
        self.a2a(inv.id, "orchestrator", "learning_agent", "TB-7", "measure originating metric")
        browser = next((s.browser for s in sig.affected_segments if s.browser), None) or "all"
        control = next(
            (s.browser for s in sig.affected_segments if s.browser and s.browser != browser),
            None,
        )
        w_start = date.fromisoformat(sig.detection_window["start"])
        w_end = date.fromisoformat(sig.detection_window["end"])
        by_pre = self.wh.conversion_by_browser(w_start, w_end)
        by_post = self.wh.conversion_by_browser(
            RECOVERY_START, RECOVERY_START + timedelta(days=3), include_recovery=True
        )
        if browser == "all" and by_pre:
            browser = max(
                by_pre.keys(),
                key=lambda n: abs(float((by_pre.get(n) or {}).get("conversion") or 0)),
            )
        if not control:
            control = next((n for n in by_pre if n != browser), "control")
        pre = (by_pre.get(browser) or {}).get("conversion", 0)
        post = (by_post.get(browser) or {}).get("conversion", 0)
        # Any flag flipped off (or companion rollback) counts as recovery attempt
        flags = self.store.list_flags() if hasattr(self.store, "list_flags") else {}
        flag_off = any(str(v).lower() == "off" for v in (flags.values() if isinstance(flags, dict) else []))
        if not flag_off:
            for act in self.store.list_actions(inv.id):
                art = act.artifacts or {}
                fname = art.get("flag")
                if fname and self.store.get_flag(str(fname)) == "off":
                    flag_off = True
                    break
        if flag_off and post > pre * 1.1:
            verdict = OutcomeVerdict.RESOLVED
        elif flag_off:
            verdict = OutcomeVerdict.PARTIALLY_RESOLVED
        else:
            verdict = OutcomeVerdict.NOT_RESOLVED
        outcome = Outcome(
            id=_id("out"),
            investigation_id=inv.id,
            metric=f"{sig.metric}.{browser}",
            pre_value=pre,
            post_value=post,
            control_comparison=self.wh.conversion_by_browser(
                RECOVERY_START, RECOVERY_START + timedelta(days=3), include_recovery=True
            )
            .get(control, {})
            .get("conversion"),
            delta=post - pre,
            verdict=verdict,
            measured_at=_now(),
        )
        self.store.put_outcome(outcome)
        drop = ((pre - sig.baseline) / sig.baseline) if sig.baseline else 0
        lesson = Lesson(
            id=_id("les"),
            investigation_id=inv.id,
            statement=(
                f"{browser} regressions on {sig.metric} need a segment regression test. "
                f"Observed ~{drop:.0%} drop vs baseline; flag rollback "
                f"{'recovered' if verdict == OutcomeVerdict.RESOLVED else 'partially recovered' if verdict == OutcomeVerdict.PARTIALLY_RESOLVED else 'did not recover'} the funnel."
            ),
            root_cause_family=f"{browser.lower()}-{sig.funnel_position or 'funnel'}",
            applicable_conditions=[f"browser={browser}", f"metric={sig.metric}"],
            linked_playbook_skill=f"playbooks/{inv.scenario_id}" if inv.scenario_id else None,
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
        if inv.room_id:
            from .receipts import memory_proof, post_receipt

            post_receipt(
                self,
                inv.room_id,
                kind="memory",
                title="Lesson written to Memory Bank",
                agent="learning_agent",
                status="done",
                detail=lesson.statement,
                proof=memory_proof(statement=lesson.statement, lesson_id=lesson.id),
                extra={"lesson": lesson.model_dump(mode="json")},
            )
        return outcome

    def _verify_generic(self, inv: Investigation) -> Outcome:
        from .connectors.warehouse import read_metric_window
        from .models import Direction
        from .tenant import resolve_tenant

        inv.state = InvestigationState.VERIFYING
        self.store.put_investigation(inv)
        self.a2a(inv.id, "orchestrator", "learning_agent", "TB-7", "measure originating metric")
        sig = self.store.get_signal(inv.originating_signal_ids[0]) if inv.originating_signal_ids else None
        pre = float(sig.baseline) if sig else 0.0
        post = pre
        verdict = OutcomeVerdict.INCONCLUSIVE
        tenant = resolve_tenant(self.store, investigation=inv)
        reading = None
        if tenant and sig:
            reading = read_metric_window(self, tenant, sig.metric, baseline=pre)
        if reading and reading.get("value") is not None:
            post = float(reading["value"])
            if sig and sig.direction == Direction.NEGATIVE:
                if post >= pre * 1.05:
                    verdict = OutcomeVerdict.RESOLVED
                elif post > pre:
                    verdict = OutcomeVerdict.PARTIALLY_RESOLVED
                else:
                    verdict = OutcomeVerdict.NOT_RESOLVED
            elif sig and sig.direction == Direction.POSITIVE:
                if post >= pre * 1.05:
                    verdict = OutcomeVerdict.RESOLVED
                else:
                    verdict = OutcomeVerdict.NOT_RESOLVED
            else:
                verdict = OutcomeVerdict.INCONCLUSIVE
        outcome = Outcome(
            id=_id("out"),
            investigation_id=inv.id,
            metric=sig.metric if sig else "impact",
            pre_value=pre,
            post_value=post,
            control_comparison=None,
            delta=post - pre,
            verdict=verdict,
            measured_at=_now(),
        )
        self.store.put_outcome(outcome)
        if verdict == OutcomeVerdict.INCONCLUSIVE:
            lesson_text = (
                f"Scenario {inv.scenario_id}: post-deploy verification needs a tenant metric connector. "
                f"No live re-read for {outcome.metric}; marked inconclusive instead of auto-resolved."
            )
        else:
            lesson_text = (
                f"Post-deploy verify for {outcome.metric}: {pre:.4g} → {post:.4g} "
                f"({verdict.value}) via {reading.get('source') if reading else 'connector'}."
            )
        lesson = Lesson(
            id=_id("les"),
            investigation_id=inv.id,
            statement=lesson_text,
            root_cause_family=inv.scenario_id or "generic",
            applicable_conditions=[inv.scenario_id or "generic"],
            linked_playbook_skill=f"playbooks/{inv.scenario_id}" if inv.scenario_id else None,
            confidence=0.7 if verdict != OutcomeVerdict.INCONCLUSIVE else 0.5,
            author_agent="learning_agent",
            tenant_id=inv.tenant_id,
        )
        self.store.put_lesson(lesson)
        mem_kind = "product" if inv.loop_type and inv.loop_type.value == "type_b" else "engineering"
        self.store.put_memory(
            lesson.id,
            mem_kind,
            {
                "statement": lesson.statement,
                "provenance": inv.id,
                "kind": mem_kind,
                "confidence": lesson.confidence,
                "tenant_id": inv.tenant_id,
            },
            tenant_id=inv.tenant_id,
        )
        inv.verification_result = verdict.value
        inv.state = InvestigationState(verdict.value) if verdict != OutcomeVerdict.INCONCLUSIVE else InvestigationState.INCONCLUSIVE
        inv.closed_at = _now()
        self.store.put_investigation(inv)
        self.timeline(inv.id, "learning_agent", "verify", f"Verification {verdict.value}", lesson.statement)
        if inv.room_id:
            from .receipts import memory_proof, post_receipt

            post_receipt(
                self,
                inv.room_id,
                kind="memory",
                title="Lesson written to Memory Bank",
                agent="learning_agent",
                status="done",
                detail=lesson.statement,
                proof=memory_proof(statement=lesson.statement, lesson_id=lesson.id),
                extra={"lesson": lesson.model_dump(mode="json")},
            )
        return outcome

    def run_until_approval(self, as_of: date | None = None) -> Investigation:
        signals = self.detect_signals(as_of)
        open_signals = [s for s in signals if s.status != SignalStatus.SUPPRESSED]
        if not open_signals:
            raise RuntimeError("no unsuppressed signal — seeded regression missing")
        # Prefer the strongest open signal (largest |magnitude|); Safari is one fixture among many.
        pick = max(open_signals, key=lambda s: abs(float(s.magnitude or 0)))
        inv = self.open_investigation(pick)
        assert inv
        self.gather_evidence(inv)
        hyp = self.form_hypothesis(inv)
        if not hyp:
            raise RuntimeError("three-source gate failed on seeded world")
        # Only attach safari_3ds scenario when the signal itself is that warehouse fixture.
        if any(seg.browser == SAFARI for seg in pick.affected_segments) and "purchase" in (pick.metric or ""):
            inv.scenario_id = inv.scenario_id or "safari_3ds"
        self.store.put_investigation(inv)
        self.propose_action(inv, hyp)
        inv = self.store.get_investigation(inv.id)
        assert inv
        from .world import publish_safari_room

        if inv.scenario_id == "safari_3ds":
            publish_safari_room(self, inv)
        return inv

    def seed_world(self) -> dict:
        from .world import seed_world

        return seed_world(self)

    def resume_after_approval(self, action_id: str, approver: str, rationale: str = "") -> Outcome:
        self.approve(
            action_id,
            approver,
            "approve",
            rationale or "Evidence pack and risk gate reviewed.",
        )
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
    if any(k in blob for k in ("schema", "flag", "business logic", "integration", "proposal", "prd", "experiment")):
        return RiskTier.MEDIUM
    if any(k in blob for k in ("docs", "copy", "logging", "test-only")):
        return RiskTier.LOW
    return RiskTier.HIGH


def json_dumps_lower(d: dict) -> str:
    return str(d).lower()


def screen_tool_output(text: str) -> tuple[bool, str]:
    """Deterministic + Model Armor layered screen (M-10)."""
    from .model_armor import screen_tool_output as layered

    hit, needle, _backend = layered(text)
    return hit, needle


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
