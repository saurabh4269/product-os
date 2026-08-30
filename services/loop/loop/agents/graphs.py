"""Live Type A / Type B graph — product-os-v2 + SalesShortcut patterns.

SalesShortcut (pre-ADK-2 winners) taught us:
  - Parallel fan-out then merger (ParallelAgent → JoinNode energy)
  - Review/Critique loop with output_key state (draft → fact-check)
  - after_agent_callback → UI push with funnel status
  - skip-if-done before_tool HITL

ADK 2 maps Sequential/Parallel/Loop → Workflow + JoinNode + RequestInput.
Hosted path stays deterministic (no Gemini).
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from ..a2a_protocol import A2AEnvelope
from ..gateway import authorize
from ..live import HUB, PIPELINE_LABEL
from ..world import post as world_post
from .callbacks import after_agent_push, skip_if_done
from .workflows import build_hitl_gate_spec, workflow_catalog

INVESTIGATORS = (
    "analytics_agent",
    "logs_agent",
    "deployment_agent",
    "database_agent",
    "customer_voice_agent",
    "code_agent",
)

# Agent → SalesShortcut-style funnel stage (for UI counters / chips).
AGENT_STAGE = {
    "orchestrator": "signal",
    "signal_agent": "signal",
    "investigator_agent": "investigate",
    "analytics_agent": "evidence",
    "logs_agent": "evidence",
    "deployment_agent": "evidence",
    "database_agent": "evidence",
    "customer_voice_agent": "evidence",
    "evidence_agent": "evidence",
    "root_cause_agent": "root_cause",
    "product_agent": "product",
    "feedback_agent": "product",  # critique / fact-check
    "code_agent": "code",
    "experiment_agent": "experiment",
    "risk_agent": "approve",
    "learning_agent": "learn",
    "security_policy_agent": "risk",
}

PIPELINE_BUG = (
    "orchestrator",
    "signal_agent",
    "investigator_agent",
    "customer_voice_agent",
    "evidence_agent",
    "root_cause_agent",
    "code_agent",
    "risk_agent",
    "learning_agent",
)

PIPELINE_FEATURE = (
    "orchestrator",
    "signal_agent",
    "investigator_agent",
    "customer_voice_agent",
    "evidence_agent",
    "product_agent",
    "feedback_agent",  # SalesShortcut FactChecker / Review-Critique
    "experiment_agent",
    "risk_agent",
    "learning_agent",
)


def graph_for(fork: str = "BUG") -> tuple[str, ...]:
    return PIPELINE_FEATURE if fork.upper() == "FEATURE" else PIPELINE_BUG


class RunContext:
    """v2 RunContext + SalesShortcut output_key / after_agent energy."""

    def __init__(self, engine: Any, room_id: str, signal: dict[str, Any], fork: str = "BUG") -> None:
        self.engine = engine
        self.room_id = room_id
        self.signal = signal
        self.fork = fork.upper() if fork else "BUG"
        self.trace_id = str(uuid4())
        self.steps: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {"fork": self.fork, "groups": set()}
        self.funnel_stage = "signal"

    def set_output(self, key: str, value: Any) -> None:
        """SalesShortcut output_key — pass structured state between agents."""
        self.state[key] = value

    def get_output(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def stage(self, stage: str, agent_id: str = "") -> None:
        self.funnel_stage = stage
        HUB.publish(
            self.room_id,
            {
                "type": "funnel_stage",
                "stage": stage,
                "label": PIPELINE_LABEL.get(stage, stage),
                "agentId": agent_id,
                "traceId": self.trace_id,
            },
        )

    def presence(self, agent_id: str, status: str) -> None:
        HUB.set_presence(
            self.room_id,
            agent_id,
            status,
            {"label": agent_id, "hue": abs(hash(agent_id)) % 360},
        )
        self.trace(agent_id, "presence", status)

    def trace(self, agent_id: str, kind: str, summary: str, payload: dict | None = None) -> None:
        step = {"agentId": agent_id, "kind": kind, "summary": summary, "payload": payload or {}}
        self.steps.append(step)
        HUB.publish(self.room_id, {"type": "trace", "traceId": self.trace_id, "step": step})

    def say(self, agent_id: str, text: str) -> None:
        from ..engine import log_verdict
        from ..model_armor import screen_chat

        blocked, needle, backend = screen_chat(text)
        if blocked:
            deny = {
                "tool": "room.chat",
                "reason": f"chat blocked: {needle}",
                "agentId": agent_id,
                "backend": backend,
            }
            log_verdict(
                self.engine.store,
                agent=agent_id,
                tool="room.chat",
                args="{}",
                verdict="BLOCK",
                rationale=f"Model Armor chat screen: {needle}",
                finding="prompt_injection" if needle != "screening_failure" else "screening_failure",
            )
            self.artifact(agent_id, "deny", deny, text=f"DENY · chat · {needle[:40]}")
            self.emit_a2a("security_policy_agent", agent_id, "deny", deny)
            return
        self.presence(agent_id, "speaking")
        world_post(
            self.engine,
            self.room_id,
            author=agent_id,
            author_kind="agent",
            kind="chat",
            text=text,
        )
        self.emit_a2a(agent_id, "broadcast", "task", {"text": text, "summary": text[:120]})

    def artifact(self, agent_id: str, kind: str, payload: dict[str, Any], text: str | None = None) -> None:
        body = {**payload, "agentId": agent_id}
        world_post(
            self.engine,
            self.room_id,
            author=agent_id,
            author_kind="agent",
            kind="artifact",
            text=text or kind,
            artifact_type=kind,
            artifact=body,
        )
        a2a_kind = (
            kind if kind in {"evidence", "hypothesis", "risk", "pr", "deny", "memory", "experiment"} else "evidence"
        )
        self.emit_a2a(agent_id, "broadcast", a2a_kind, body)

    def emit_a2a(self, frm: str, to: str, kind: str, payload: dict[str, Any]) -> None:
        env = A2AEnvelope(
            from_agent=frm,
            to_agent=to,
            kind=kind,  # type: ignore[arg-type]
            trace_id=self.trace_id,
            room_id=self.room_id,
            payload=payload,
        )
        HUB.publish(self.room_id, env.as_event())
        if to and to != "broadcast":
            self.presence(to, "thinking")

    def tool(self, agent_id: str, tool: str, fn: Callable[[], Any], *, output_key: str | None = None) -> Any:
        if output_key:
            cached = skip_if_done(self.state, output_key, {"done", "completed", "applied"})
            if cached is not None:
                self.trace(agent_id, "reused", f"skip-if-done {tool}", {"key": output_key})
                return cached
        self.presence(agent_id, "tool")
        gate = authorize(agent_id, tool)
        self.trace(agent_id, "gateway", gate.decision, gate.as_dict())
        self.emit_a2a(
            agent_id,
            "security_policy_agent",
            "tool_request",
            {"tool": tool, "gate": gate.as_dict()},
        )
        if gate.decision == "deny":
            deny = {"tool": tool, "reason": gate.reason, "agentId": agent_id}
            self.artifact(agent_id, "deny", deny, text=f"DENY · {tool}")
            self.emit_a2a("security_policy_agent", agent_id, "deny", deny)
            raise PermissionError(gate.reason)
        if gate.decision == "approval":
            raise PermissionError(gate.reason + " (pending approval)")
        result = fn()
        text = str(result) if not isinstance(result, dict) else " ".join(str(v) for v in result.values())
        if text.strip():
            from ..engine import log_verdict, screen_tool_output

            hit, needle = screen_tool_output(text)
            if hit:
                deny = {"tool": tool, "reason": f"tool output blocked: {needle}", "agentId": agent_id}
                log_verdict(
                    self.engine.store,
                    agent=agent_id,
                    tool=tool,
                    args=str({}),
                    verdict="BLOCK",
                    rationale=f"Model Armor / injection screen: {needle}",
                    finding="prompt_injection",
                )
                self.artifact(agent_id, "deny", deny, text=f"DENY · tool output · {tool}")
                self.emit_a2a("security_policy_agent", agent_id, "deny", deny)
                raise PermissionError(deny["reason"])
        if output_key:
            self.set_output(output_key, result if isinstance(result, dict) else {"result": result, "status": "done"})
        self.emit_a2a(agent_id, "broadcast", "tool_result", {"tool": tool, "ok": True})
        return result


def _metric(sig: dict[str, Any]) -> str:
    return str(sig.get("metric") or sig.get("scenario") or "signal")


def _dims(sig: dict[str, Any]) -> dict[str, Any]:
    d = sig.get("dimensions")
    return d if isinstance(d, dict) else {}


def _run_agent(ctx: RunContext, agent_id: str) -> None:
    stage = AGENT_STAGE.get(agent_id)
    if stage:
        ctx.stage(stage, agent_id)
    ctx.presence(agent_id, "thinking")
    try:
        _dispatch(ctx, agent_id)
        after_agent_push(
            lambda payload: HUB.publish(
                ctx.room_id,
                {
                    "type": "agent_callback",
                    "agent_type": agent_id.split("_")[0],
                    "agentId": agent_id,
                    "status": ctx.funnel_stage,
                    "message": payload.get("message") or f"{agent_id} done",
                    "data": {"stage": ctx.funnel_stage, "fork": ctx.fork},
                },
            ),
            room_id=ctx.room_id,
            agent_id=agent_id,
            status=ctx.funnel_stage,
            message=f"{agent_id} completed",
            data={"stage": ctx.funnel_stage},
        )
    except PermissionError as e:
        ctx.trace(agent_id, "denied", str(e))
        ctx.say(agent_id, f"Gateway blocked a tool: {e}")
    finally:
        ctx.presence(agent_id, "idle")


def _run_parallel_investigators(ctx: RunContext) -> None:
    """SalesShortcut ParallelAgent fan-out → JoinNode gather."""
    ctx.stage("evidence", "investigator_agent")
    ctx.say("investigator_agent", "Fan-out: analytics, logs, deploy, warehouse (parallel).")
    for aid in INVESTIGATORS:
        ctx.emit_a2a("investigator_agent", aid, "task", {"summary": f"parallel → {aid}"})
        _run_agent(ctx, aid)
    parts = [ctx.get_output(f"evidence_{aid}") for aid in INVESTIGATORS]
    ctx.set_output(
        "final_merged_evidence",
        {"parts": [p for p in parts if p], "status": "done"},
    )


def _critique_loop(ctx: RunContext, metric: str, dims: dict[str, Any], max_iterations: int = 2) -> None:
    """SalesShortcut LoopAgent review/critique — draft → fact-check (max N)."""
    draft = ctx.get_output("draft_proposal") or {
        "draft": dims.get("hypothesis") or f"Proposal for {metric}",
        "metric": metric,
        "status": "draft",
        "iteration": 0,
    }
    ctx.set_output("draft_proposal", draft)

    for i in range(max_iterations):
        prev = ctx.get_output("draft_proposal") or draft
        if isinstance(prev, dict) and prev.get("status") == "reviewed" and prev.get("ok"):
            break
        critique = {
            **(prev if isinstance(prev, dict) else {"draft": str(prev)}),
            "status": "reviewed",
            "ok": True,
            "iteration": i + 1,
            "notes": "Claims grounded in evidence pack; tone tightened.",
        }
        ctx.set_output("proposal", critique)
        ctx.set_output("draft_proposal", critique)
        ctx.artifact(
            "feedback_agent",
            "evidence",
            critique,
            text=f"Critique · pass {i + 1}",
        )
        ctx.say("feedback_agent", f"Fact-check pass {i + 1}: proposal looks solid.")
        if critique.get("ok"):
            break


def _dispatch(ctx: RunContext, agent_id: str) -> None:
    sig = ctx.signal
    metric = _metric(sig)
    dims = _dims(sig)
    delta = sig.get("delta")

    if agent_id == "orchestrator":
        ctx.say(agent_id, f"Opening work on {metric}. Fleet is assembling.")
        return
    if agent_id == "signal_agent":
        polarity = sig.get("polarity") or ("negative" if ctx.fork == "BUG" else "positive")
        ctx.artifact(
            agent_id,
            "signal",
            {
                "metric": metric,
                "delta": delta,
                "polarity": polarity,
                "source": sig.get("source"),
                "dimensions": dims,
            },
            text=f"Signal · {metric}" + (f" ({delta})" if delta is not None else ""),
        )
        ctx.set_output("signal_result", {"metric": metric, "status": "done"})
        ctx.say(agent_id, f"Classified as {'Type A / BUG' if ctx.fork == 'BUG' else 'Type B / FEATURE'}.")
        return
    if agent_id == "investigator_agent":
        ctx.say(agent_id, "Dispatching specialists in parallel.")
        return
    if agent_id == "analytics_agent":
        fact = ctx.tool(
            agent_id,
            "ga4.read",
            lambda: {
                "metric": metric,
                "baseline": 0.82 if ctx.fork == "BUG" else 0.11,
                "delta": delta,
                "note": "warehouse fact, not memory",
                "status": "done",
            },
            output_key=f"evidence_{agent_id}",
        )
        ctx.artifact(agent_id, "evidence", fact, text=f"Analytics · {metric}")
        ctx.state.setdefault("groups", set()).add("ga4")
        return
    if agent_id == "logs_agent":
        cluster = ctx.tool(
            agent_id,
            "logs.read",
            lambda: {
                "cluster": f"{dims.get('error') or metric}-cluster",
                "count": 140 + abs(int(float(delta or 0) * 800)),
                "example": dims.get("error") or "timeout_or_drop",
                "status": "done",
            },
            output_key=f"evidence_{agent_id}",
        )
        ctx.artifact(agent_id, "evidence", cluster, text=f"Logs · {cluster['cluster']}")
        ctx.state.setdefault("groups", set()).add("logs")
        return
    if agent_id == "deployment_agent":
        deploy = ctx.tool(
            agent_id,
            "deploys.read",
            lambda: {
                "service": dims.get("sdk") or dims.get("service") or "app-web",
                "version": dims.get("version") or "4.2.0",
                "minutes_ago": dims.get("deploy_minutes_ago", 42),
                "status": "done",
            },
            output_key=f"evidence_{agent_id}",
        )
        ctx.artifact(agent_id, "evidence", deploy, text=f"Deploy · {deploy['service']} {deploy['version']}")
        ctx.state.setdefault("groups", set()).add("deploys")
        return
    if agent_id == "database_agent":
        row = ctx.tool(
            agent_id,
            "warehouse.read",
            lambda: {"aggregate": metric, "segments": dims or {"segment": "all"}, "ok": True, "status": "done"},
            output_key=f"evidence_{agent_id}",
        )
        ctx.artifact(agent_id, "evidence", row, text="Warehouse aggregate")
        ctx.state.setdefault("groups", set()).add("warehouse")
        return
    if agent_id == "customer_voice_agent":
        persona = "confused" if ctx.fork == "BUG" else "technical"
        voice = {
            "persona": persona,
            "reason": dims.get("error") or f"{metric}_friction",
            "severity": "high" if ctx.fork == "BUG" else "medium",
            "willing_to_retry": True,
            "status": "done",
        }
        ctx.set_output("voice_result", voice)
        ctx.artifact(agent_id, "evidence", voice, text=f"Voice · {persona}")
        ctx.state.setdefault("groups", set()).add("voice")
        return
    if agent_id == "evidence_agent":
        groups = sorted(ctx.state.get("groups") or [])
        merged = ctx.get_output("final_merged_evidence") or {}
        parts = merged.get("parts") or []
        # Scored pack — agreement across independence groups (not a bare count).
        confidence = round(min(0.97, 0.5 + 0.08 * len(groups) + 0.02 * len(parts)), 3)
        correlation = dims.get("correlation") or (
            f"{metric} anomaly with {len(groups)} independent sources"
            + (f" · Δ {delta}" if delta is not None else "")
        )
        pack = {
            "independence_groups": groups,
            "count": len(groups),
            "merged_parts": len(parts),
            "confidence": confidence,
            "correlation_summary": correlation,
            "checklist": {
                "analytics": "analytics_agent" in str(groups) or "ga4" in groups,
                "logs": "logs" in groups or "error_budget" in str(groups),
                "deploys": "deploys" in groups or "release" in str(groups),
                "customer": "voice" in groups or "customer" in str(groups),
            },
            "status": "done",
        }
        ctx.artifact(
            agent_id,
            "evidence_pack",
            pack,
            text=f"Evidence pack · {len(groups)} groups · confidence {confidence}",
        )
        ctx.set_output("evidence_pack", pack)
        return
    if agent_id == "root_cause_agent":
        hyp = dims.get("hypothesis") or f"Root cause tied to {metric}"
        ctx.set_output("hypothesis", {"statement": hyp, "fork": "BUG", "status": "done"})
        ctx.artifact(agent_id, "hypothesis", {"statement": hyp, "fork": "BUG"}, text=hyp)
        ctx.say(agent_id, "Hypothesis ready. Handing to code.")
        return
    if agent_id == "product_agent":
        draft = {
            "draft": dims.get("hypothesis") or f"Opportunity around {metric}",
            "metric": metric,
            "status": "draft",
        }
        ctx.set_output("draft_proposal", draft)
        ctx.artifact(agent_id, "hypothesis", {**draft, "fork": "FEATURE"}, text=draft["draft"])
        ctx.say(agent_id, "Draft proposal ready. Fact-check next.")
        return
    if agent_id == "feedback_agent":
        _critique_loop(ctx, metric, dims, max_iterations=2)
        return
    if agent_id == "code_agent":
        ctx.artifact(
            agent_id,
            "pr",
            {"title": f"Fix {metric}", "status": "proposed", "merged": False},
            text=f"PR brief · Fix {metric}",
        )
        ctx.set_output("pr_brief", {"title": f"Fix {metric}", "status": "done"})
        return
    if agent_id == "experiment_agent":
        proposal = ctx.get_output("proposal") or ctx.get_output("draft_proposal") or {}
        ctx.artifact(
            agent_id,
            "experiment",
            {
                "metric": metric,
                "mde": 0.05,
                "guardrail": "crash_free_sessions",
                "from_proposal": bool(proposal),
            },
            text=f"Experiment · {metric}",
        )
        ctx.set_output("experiment", {"metric": metric, "status": "done"})
        return
    if agent_id == "risk_agent":
        tier = "HIGH" if ctx.fork == "BUG" and abs(float(delta or 0.2)) >= 0.1 else "MEDIUM"
        ctx.artifact(
            agent_id,
            "risk",
            {"tier": tier, "needs_approval": True},
            text=f"Risk · {tier} — waiting on a human",
        )
        ctx.stage("approve", agent_id)
        HUB.publish(
            ctx.room_id,
            {
                "type": "approval_required",
                "approval": {"agent_id": agent_id, "risk_level": tier, "status": "pending"},
            },
        )
        return
    if agent_id == "learning_agent":
        lesson = dims.get("hypothesis") or f"Lesson from {metric}"
        ctx.artifact(
            agent_id,
            "memory",
            {"type": "engineering" if ctx.fork == "BUG" else "product", "title": lesson},
            text=lesson,
        )
        ctx.set_output("lesson", {"title": lesson, "status": "done"})
        ctx.say(agent_id, "Remembered. Investigation can close after verify.")
        return
    if agent_id == "security_policy_agent":
        try:
            ctx.tool(agent_id, "customer_records.dump", lambda: {"records": []})
        except PermissionError:
            pass
        return


def run_live_graph(
    engine: Any,
    room_id: str,
    signal: dict[str, Any],
    *,
    fork: str | None = None,
    probe_exfil: bool = False,
) -> dict[str, Any]:
    """Walk the fleet with live presence, parallel fan-out, review/critique, gateway."""
    forced = fork or signal.get("fork") or ("FEATURE" if signal.get("polarity") == "positive" else "BUG")
    ctx = RunContext(engine, room_id, signal, fork=str(forced))
    HUB.publish(room_id, {"type": "signal", "signal": {**signal, "roomId": room_id}})
    ctx.stage("signal", "orchestrator")

    if probe_exfil or signal.get("scenario") in {"security_exfil", "pii-exfil-deny"}:
        _run_agent(ctx, "orchestrator")
        _run_agent(ctx, "security_policy_agent")
        try:
            ctx.tool("code_agent", "customer_records.dump", lambda: {"records": []})
        except PermissionError:
            pass
        _run_agent(ctx, "learning_agent")
        return {
            "trace_id": ctx.trace_id,
            "steps": len(ctx.steps),
            "fork": "DENY",
            "pipeline": ["security_policy_agent", "code_agent", "learning_agent"],
            "funnel_stage": ctx.funnel_stage,
        }

    walked: list[str] = []
    _run_agent(ctx, "orchestrator")
    walked.append("orchestrator")
    _run_agent(ctx, "signal_agent")
    walked.append("signal_agent")
    _run_agent(ctx, "investigator_agent")
    walked.append("investigator_agent")
    _run_parallel_investigators(ctx)
    walked.extend(INVESTIGATORS)

    rest = [
        a
        for a in graph_for(ctx.fork)
        if a not in {"orchestrator", "signal_agent", "investigator_agent", *INVESTIGATORS}
    ]
    for agent_id in rest:
        _run_agent(ctx, agent_id)
        walked.append(agent_id)

    return {
        "trace_id": ctx.trace_id,
        "steps": len(ctx.steps),
        "fork": ctx.fork,
        "pipeline": walked,
        "groups": sorted(ctx.state.get("groups") or []),
        "funnel_stage": ctx.funnel_stage,
        "outputs": {
            k: v for k, v in ctx.state.items() if k not in {"groups", "fork"} and not isinstance(v, set)
        },
    }


def run_presence_sweep(
    room_id: str,
    fork: str,
    set_presence: Callable[[str, str, str], None],
    publish: Callable[[str, dict[str, Any]], None] | None = None,
) -> list[str]:
    """Lightweight presence-only walk. Prefer run_live_graph."""
    order = list(graph_for(fork))
    if "investigator_agent" in order:
        idx = order.index("investigator_agent") + 1
        for aid in reversed(INVESTIGATORS):
            if aid not in order:
                order.insert(idx, aid)
    for agent_id in order:
        set_presence(room_id, agent_id, "thinking")
        if publish:
            publish(
                room_id,
                {
                    "type": "a2a",
                    "from": "orchestrator",
                    "to": agent_id,
                    "kind": "task",
                    "summary": f"handoff → {agent_id}",
                },
            )
        set_presence(room_id, agent_id, "idle")
    return order


def adk2_alignment() -> dict[str, Any]:
    cat = workflow_catalog()
    hitl = build_hitl_gate_spec()
    return {
        "adk": "2.x",
        "adk_version": "2.x",
        "deprecated_1x": ["SequentialAgent", "ParallelAgent", "LoopAgent"],
        "preferred_2x": ["Workflow", "JoinNode", "RequestInput", "Workflow-as-Tool≥2.4"],
        "salesshortcut_patterns": [
            "parallel_fanout_merge",
            "review_critique_output_key",
            "after_agent_callback_push",
            "skip_if_done_before_tool",
            "funnel_stage_bus",
        ],
        "hosted_source_of_truth": "LoopEngine + live RunContext",
        "workflows": cat,
        "investigation_fanout": cat.get("investigation_fanout"),
        "proposal_critique": cat.get("proposal_critique"),
        "hitl": hitl,
        "investigators_fanout": list(INVESTIGATORS),
        "enterprise": {
            "workspace_oauth": "browser consent + offline refresh (no SA for Gmail/Calendar)",
            "mail_send": "denied until explicit product decision",
            "gateway_identity": "exfil DENY — fail_open=false",
            "agent_gateway": "plan-only",
            "pstn": "not at launch — text fallback only",
        },
    }
