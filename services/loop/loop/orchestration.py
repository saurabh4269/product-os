"""Progressive orchestration — agents appear when invoked, not as a fixed homepage spine.

Signal agent watches in the background. When something moves, the flow reveals one
step at a time. Each handoff carries a plain-English *why* derived from rules + facts.
"""

from __future__ import annotations

from typing import Any

from .models import InvestigationState, SignalStatus
from .workflow import (
    NODE_DETAIL,
    NODE_LABEL,
    NODE_SHORT,
    infer_needs,
    kind_label,
    workflow_from_store,
)

# Primary owner per workflow node (for handoff narration).
NODE_AGENT: dict[str, str] = {
    "signal": "signal_agent",
    "investigate": "investigator_agent",
    "evidence": "evidence_agent",
    "customer_mail": "customer_voice_agent",
    "customer_call": "customer_voice_agent",
    "customer": "customer_voice_agent",
    "root_cause": "root_cause_agent",
    "product": "product_agent",
    "code": "code_agent",
    "experiment": "product_agent",
    "risk": "risk_agent",
    "approve": "risk_agent",
    "coordinate": "coordination_agent",
    "verify": "learning_agent",
    "learn": "learning_agent",
}

# Rule templates: why this node enters the flow (capability + observation).
NODE_WHY: dict[str, str] = {
    "signal": "Warehouse or product telemetry moved outside baseline.",
    "investigate": "Need independent specialists — analytics, logs, deploys — in parallel.",
    "evidence": "Merge sources; refuse hypothesis until ≥3 independence groups agree.",
    "customer_mail": "Similar users hit the same friction — mail first, not cold-call.",
    "customer_call": "Non-responders to mail still need a diagnostic voice pass.",
    "root_cause": "Bug path — converge on a scoped fix from correlated evidence.",
    "product": "Feature path — shape the change before shipping.",
    "code": "Patch or flag rollback on Product Y.",
    "experiment": "Measure treatment before a full rollout.",
    "risk": "Tier the change; HIGH needs a human gate.",
    "approve": "Human OK required before side effects run.",
    "coordinate": "Owners, calendar, and mail drafts for the review.",
    "verify": "Re-read the metric window after the change.",
    "learn": "Write the lesson to Memory Bank for the next case.",
}


def handoff_why(
    from_node: str,
    to_node: str,
    *,
    needs: Any | None = None,
    tags: list[str] | None = None,
    metric: str | None = None,
    stored_summary: str | None = None,
) -> str:
    """Plain English: why agent/node A handed to B."""
    if stored_summary:
        return stored_summary
    to_agent = NODE_AGENT.get(to_node, to_node)
    from_agent = NODE_AGENT.get(from_node, from_node)
    tags = tags or []
    metric = metric or "the metric"

    if from_node == "signal" and to_node == "investigate":
        if "analytics" in tags or "warehouse" in tags:
            return f"{from_agent} saw {metric} move in analytics — dispatching specialists."
        if "dependency" in tags:
            return f"{from_agent} flagged a dependency/version shift — specialists will confirm."
        return f"{from_agent} opened a case on {metric} — fan-out to independent arms."

    if to_node == "evidence":
        return f"{from_agent} collected specialist claims — {to_agent} merges independence groups."

    if to_node in {"customer_mail", "customer_call", "customer"}:
        if to_node == "customer_mail":
            return f"{from_agent} has evidence — {to_agent} emails similar-pattern users first."
        return f"{from_agent} mail window elapsed — {to_agent} calls non-responders only."

    if to_node == "root_cause":
        return f"{from_agent} packed evidence — {to_agent} forms a bug hypothesis."

    if to_node == "product":
        return f"{from_agent} packed evidence — {to_agent} shapes a product change."

    if to_node == "code":
        return f"{from_agent} hypothesis approved — {to_agent} prepares patch / PR."

    if to_node == "experiment":
        return f"{from_agent} proposal ready — {to_agent} designs a measured experiment."

    if to_node == "risk":
        return f"{from_agent} proposed a change — {to_agent} tiers risk."

    if to_node == "approve":
        return f"{to_agent} needs your OK before connectors run."

    if to_node == "coordinate":
        return f"{from_agent} approved — {to_agent} schedules owners and drafts mail."

    if to_node == "verify":
        return f"{from_agent} executed — {to_agent} re-reads {metric}."

    if to_node == "learn":
        return f"{from_agent} verified outcome — {to_agent} writes the lesson."

    return NODE_WHY.get(to_node, f"{from_agent} → {to_agent}: {NODE_WHY.get(to_node, 'next step')}.")


def _pick_focus_room(store: Any) -> tuple[Any | None, Any | None]:
    """Highest-priority open room + investigation."""
    rooms = [r for r in store.list_rooms() if getattr(r, "status", "open") == "open"]
    if not rooms:
        return None, None

    def score(room: Any) -> tuple[int, float]:
        inv = store.get_investigation(room.investigation_id) if room.investigation_id else None
        awaiting = 0
        if inv and hasattr(store, "list_actions"):
            for act in store.list_actions(inv.id):
                if act.status in {"proposed", "awaiting_approval"}:
                    awaiting = 2
                    break
        active = 1 if inv and getattr(inv, "state", None) not in {
            InvestigationState.RESOLVED,
            InvestigationState.NOT_RESOLVED,
            InvestigationState.INCONCLUSIVE,
            InvestigationState.PARTIALLY_RESOLVED,
        } else 0
        return (awaiting, active)

    room = max(rooms, key=score)
    inv = store.get_investigation(room.investigation_id) if room.investigation_id else None
    return room, inv


def _metric_from_room(store: Any, room: Any, inv: Any | None) -> str:
    for msg in store.list_messages(room.id):
        if msg.artifact_type == "signal" and isinstance(msg.artifact, dict):
            m = msg.artifact.get("metric")
            if m:
                return str(m)
    if inv and inv.originating_signal_ids:
        sig = store.get_signal(inv.originating_signal_ids[0])
        if sig:
            return sig.metric
    return getattr(room, "title", "") or "metric"


def _handoffs_from_store(store: Any, inv_id: str) -> list[dict[str, str]]:
    if not hasattr(store, "list_agent_calls"):
        return []
    out: list[dict[str, str]] = []
    for call in store.list_agent_calls(inv_id):
        out.append(
            {
                "from": call.from_agent,
                "to": call.to_agent,
                "why": call.summary or "",
                "at": call.started_at.isoformat() if hasattr(call.started_at, "isoformat") else str(call.started_at),
            }
        )
    return out


def _node_status(idx: int, current_idx: int) -> str:
    if idx < current_idx:
        return "done"
    if idx == current_idx:
        return "active"
    if idx == current_idx + 1:
        return "next"
    return "hidden"


def progressive_flow(store: Any, *, room: Any | None = None, inv: Any | None = None) -> dict[str, Any]:
    """Build homepage flow — only reveal steps reached so far (+ one peek ahead)."""
    if room is None:
        room, inv = _pick_focus_room(store)
    if not room:
        return {"mode": "watching", "steps": [], "handoffs": [], "current": None, "kind": None}

    wf = workflow_from_store(store, room, inv)
    nodes: list[str] = list(wf.get("nodes") or [])
    if not nodes:
        return {"mode": "watching", "steps": [], "handoffs": [], "current": None, "kind": None}

    current = str(wf.get("current") or nodes[0])
    try:
        cur_idx = nodes.index(current)
    except ValueError:
        cur_idx = 0
        current = nodes[0]

    needs = infer_needs(
        loop_type=getattr(room, "loop_type", None),
        path=getattr(room, "path", None),
        room_kind=getattr(room, "kind", None),
        scenario_id=getattr(room, "scenario_id", None),
        artifact_types=[m.artifact_type for m in store.list_messages(room.id) if m.artifact_type],
    )
    tags = list(wf.get("tags") or needs.tags)
    metric = _metric_from_room(store, room, inv)
    stored_handoffs = _handoffs_from_store(store, inv.id) if inv else []

    steps: list[dict[str, Any]] = []
    handoffs: list[dict[str, Any]] = []

    for i, node in enumerate(nodes):
        status = _node_status(i, cur_idx)
        if status == "hidden":
            continue
        agent = NODE_AGENT.get(node, "orchestrator")
        step = {
            "n": len(steps) + 1,
            "id": node,
            "stage": node,
            "short": NODE_SHORT.get(node, NODE_LABEL.get(node, node)),
            "label": NODE_LABEL.get(node, node.replace("_", " ").title()),
            "detail": NODE_WHY.get(node, NODE_DETAIL.get(node, "")),
            "agent": agent,
            "status": status,
            "on": status in {"done", "active"},
        }
        if status == "next":
            step["on"] = False
            step["detail"] = NODE_WHY.get(node, step["detail"])
        steps.append(step)

        if i > 0 and status in {"done", "active", "next"}:
            prev = nodes[i - 1]
            why = None
            from_a = NODE_AGENT.get(prev, prev)
            to_a = agent
            for h in stored_handoffs:
                if h["from"] == from_a and h["to"] == to_a and h.get("why"):
                    why = h["why"]
                    break
            if not why:
                why = handoff_why(prev, node, needs=needs, tags=tags, metric=metric)
            handoffs.append({"from": from_a, "to": to_a, "from_node": prev, "to_node": node, "why": why})

    return {
        "mode": "active",
        "room_id": room.id,
        "room_title": getattr(room, "title", ""),
        "investigation_id": getattr(inv, "id", None) if inv else room.investigation_id,
        "kind": wf.get("kind") or kind_label(needs),
        "tags": tags,
        "needs": wf.get("needs") or {},
        "nodes": nodes,
        "current": current,
        "steps": steps,
        "handoffs": handoffs,
        "stored_handoffs": stored_handoffs,
    }


def home_orchestration(store: Any, engine: Any | None = None) -> dict[str, Any]:
    """Homepage orchestration payload — watching or progressive active flow."""
    open_signals = []
    if engine and hasattr(engine, "store"):
        open_signals = [
            s
            for s in (engine.store.list_signals() if hasattr(engine.store, "list_signals") else [])
            if getattr(s, "status", None) in {SignalStatus.OPEN, SignalStatus.INVESTIGATING}
        ]

    flow = progressive_flow(store)
    if flow.get("mode") == "active":
        return {
            "mode": "active",
            "watch_line": None,
            "signal_agent": {"status": "active", "detail": flow.get("room_title") or "Case open"},
            **flow,
        }

    # Quiet — signal agent watches; no fake seven-step spine.
    watch_detail = "Polling warehouse and product telemetry."
    if open_signals:
        sig = open_signals[0]
        watch_detail = f"Watching — {sig.metric} flagged, opening work…"
    return {
        "mode": "watching",
        "watch_line": "Signal agent watching",
        "signal_agent": {"status": "watching", "detail": watch_detail},
        "steps": [],
        "handoffs": [],
        "current": None,
        "kind": None,
        "room_id": None,
        "tags": [],
        "needs": {},
    }


def focus_steps_progressive(orchestration: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Shape for SevenStepLoop / homepage — progressive only."""
    if not orchestration:
        return []
    if orchestration.get("mode") == "watching":
        return []
    return list(orchestration.get("steps") or [])
