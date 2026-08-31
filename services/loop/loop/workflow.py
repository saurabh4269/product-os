"""Capability-composed workflows — no fixed homepage pipeline.

Each open room gets a node graph composed from what *this case* needs:
customer call vs analytics-only, code fix vs experiment, security deny, etc.
Unseen cases work because we compose from observed facts, not named recipes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .models import InvestigationState, LoopType, PathKind, RoomKind

# Stable labels for every node the composer can emit.
NODE_LABEL: dict[str, str] = {
    "signal": "Signal",
    "investigate": "Investigate",
    "evidence": "Evidence",
    "customer": "Customer",
    "customer_mail": "Email",
    "customer_call": "Call",
    "root_cause": "Root cause",
    "product": "Product",
    "code": "Code",
    "experiment": "Experiment",
    "risk": "Risk",
    "approve": "Approve",
    "coordinate": "Coordinate",
    "verify": "Verify",
    "learn": "Learn",
}

NODE_SHORT: dict[str, str] = {
    "signal": "Signal",
    "investigate": "Investigate",
    "evidence": "Diagnose",
    "customer": "Ask",
    "customer_mail": "Email",
    "customer_call": "Call",
    "root_cause": "Decide",
    "product": "Shape",
    "code": "Ship",
    "experiment": "Experiment",
    "risk": "Risk",
    "approve": "Approve",
    "coordinate": "Coordinate",
    "verify": "Verify",
    "learn": "Learn",
}

NODE_DETAIL: dict[str, str] = {
    "signal": "Something moved in the product",
    "investigate": "Specialists fan out in parallel",
    "evidence": "Independent sources merged",
    "customer": "Mail first, call only non-responders",
    "customer_mail": "Friendly feedback email to similar-pattern users",
    "customer_call": "Call only if they didn't reply to mail",
    "root_cause": "Bug path — find and fix",
    "product": "Feature path — shape the change",
    "code": "Patch / PR on Product Y",
    "experiment": "Treatment + measure window",
    "risk": "Tier the change",
    "approve": "Human gate when required",
    "coordinate": "Owners · calendar · mail",
    "verify": "Metric window after the change",
    "learn": "Write the lesson to memory",
}

# Preferred left→right order when unioning boards across rooms.
CANONICAL_ORDER = [
    "signal",
    "investigate",
    "evidence",
    "customer_mail",
    "customer_call",
    "customer",
    "root_cause",
    "product",
    "code",
    "experiment",
    "risk",
    "approve",
    "coordinate",
    "verify",
    "learn",
]

# Homepage live receipts: keep fewer columns; map fine nodes into these.
LIVE_ORDER = ["signal", "evidence", "customer", "code", "experiment", "approve", "verify"]

LIVE_LABEL: dict[str, str] = {
    "signal": "Signal",
    "evidence": "Evidence",
    "customer": "Customer",
    "code": "Code",
    "experiment": "Experiment",
    "approve": "Approve",
    "verify": "Verify",
}

_STATE_HINT: dict[InvestigationState, str] = {
    InvestigationState.OPEN: "signal",
    InvestigationState.GATHERING: "investigate",
    InvestigationState.HYPOTHESIS: "evidence",
    InvestigationState.ACTION_PROPOSED: "risk",
    InvestigationState.AWAITING_APPROVAL: "approve",
    InvestigationState.APPROVED: "approve",
    InvestigationState.ACTING: "code",
    InvestigationState.VERIFYING: "verify",
    InvestigationState.RESOLVED: "learn",
    InvestigationState.PARTIALLY_RESOLVED: "learn",
    InvestigationState.NOT_RESOLVED: "learn",
    InvestigationState.INCONCLUSIVE: "learn",
}

_CUSTOMER_ARTIFACTS = frozenset(
    {
        "voice",
        "contact",
        "contact_lookup",
        "call",
        "call_feedback",
        "call_transcript",
        "call_evidence",
        "mail_outreach",
        "mail_reply",
        "user_cluster",
    }
)
_CODE_ARTIFACTS = frozenset({"code", "code_brief", "pr", "patch"})
_EXPERIMENT_ARTIFACTS = frozenset({"experiment", "prd", "product"})
_COORD_ARTIFACTS = frozenset({"coordination", "mail", "gmail"})
_EVIDENCE_ARTIFACTS = frozenset(
    {
        "evidence",
        "evidence_pack",
        "analytics",
        "warehouse",
        "bq",
        "metric",
        "hypothesis",
        "classification",
        "voice_context",
    }
)


@dataclass
class Needs:
    """What this case actually requires. Composed into an ordered node list."""

    signal: bool = True
    investigate: bool = True
    evidence: bool = True
    customer: bool = False  # mail-first ladder (email → wait → call non-responders)
    feature: bool = False  # product node vs root_cause
    code: bool = False
    experiment: bool = False
    risk: bool = False
    approve: bool = False
    coordinate: bool = False
    verify: bool = False
    learn: bool = True
    security: bool = False
    # Free-form tags for UI (source of signal, etc.) — not used for branching.
    tags: list[str] = field(default_factory=list)


def _truthy(v: Any) -> bool:
    if v is None or v is False:
        return False
    if isinstance(v, (dict, list, str)) and not v:
        return False
    return True


def _as_state(state: InvestigationState | str | None) -> InvestigationState | None:
    if state is None:
        return None
    if isinstance(state, InvestigationState):
        return state
    try:
        return InvestigationState(str(state))
    except ValueError:
        return None


def _loop_is_feature(loop_type: LoopType | str | None, path: PathKind | str | None = None) -> bool:
    raw = loop_type.value if isinstance(loop_type, LoopType) else str(loop_type or "")
    if raw.lower() in {"type_b", "b", "feature"}:
        return True
    praw = path.value if isinstance(path, PathKind) else str(path or "")
    return praw.lower() == "feature"


def _is_security(
    *,
    path: PathKind | str | None = None,
    room_kind: RoomKind | str | None = None,
    scenario_id: str | None = None,
) -> bool:
    praw = path.value if isinstance(path, PathKind) else str(path or "")
    if praw.lower() == "security":
        return True
    kind = room_kind.value if isinstance(room_kind, RoomKind) else str(room_kind or "")
    if kind.lower() == "review":
        return True
    # Last resort: known security fixture id — prefer path/kind when present.
    if scenario_id == "security_exfil":
        return True
    return False


def infer_needs(
    *,
    loop_type: LoopType | str | None = None,
    path: PathKind | str | None = None,
    room_kind: RoomKind | str | None = None,
    scenario_id: str | None = None,
    dimensions: dict[str, Any] | None = None,
    artifact_types: Iterable[str] | None = None,
    action_types: Iterable[str] | None = None,
    action_statuses: Iterable[str] | None = None,
    propose_action: bool | None = None,
    signal_family: str | None = None,
    signal_source: str | None = None,
    members: Iterable[str] | None = None,
) -> Needs:
    """Derive capabilities from event/room facts — works for cases never seen before."""
    dims = dimensions if isinstance(dimensions, dict) else {}
    arts = {str(a) for a in (artifact_types or []) if a}
    acts = {str(a) for a in (action_types or []) if a}
    statuses = {str(s) for s in (action_statuses or []) if s}
    feature = _loop_is_feature(loop_type, path)
    security = _is_security(path=path, room_kind=room_kind, scenario_id=scenario_id)
    kind = room_kind.value if isinstance(room_kind, RoomKind) else str(room_kind or "")

    tags: list[str] = []
    if feature:
        tags.append("feature")
    else:
        tags.append("bug")
    if security:
        tags.append("security")

    # --- customer contact (call / voice feedback) ---
    voice = dims.get("voice_subject")
    wants_call = dims.get("customer_contact") or dims.get("needs_call") or dims.get("call")
    customer = bool(
        _truthy(voice)
        or _truthy(wants_call)
        or bool(arts & _CUSTOMER_ARTIFACTS)
        or (str(signal_family or "").lower() == "customer")
        or kind.lower() == "research"
    )
    # Explicit opt-out for analytics / dependency / agent-search upgrades with no user.
    if dims.get("skip_customer") or dims.get("no_customer_contact") is True:
        customer = False
    if customer:
        tags.append("customer_contact")

    # --- code / experiment / product shape ---
    code_dim = dims.get("code") if isinstance(dims.get("code"), dict) else dims.get("code")
    has_code = bool(
        _truthy(code_dim)
        or bool(arts & _CODE_ARTIFACTS)
        or "code_change" in acts
        or "flag_rollback" in acts
    )
    has_experiment = bool(
        _truthy(dims.get("experiment"))
        or bool(arts & {"experiment"})
        or "experiment" in acts
    )
    # Source tags (informational)
    src = str(signal_source or dims.get("source") or "").lower()
    if "ga4" in src or "analytics" in src or "bigquery" in src or "bq" in src:
        tags.append("analytics")
    if "depend" in src or dims.get("dependency") or (isinstance(code_dim, dict) and code_dim.get("dependency")):
        tags.append("dependency")
    if arts & {"warehouse", "bq", "analytics", "metric"}:
        tags.append("warehouse")

    # Propose / risk / approve — explicit flag wins; else infer from actions / room kind.
    if propose_action is not None:
        will_propose = bool(propose_action)
    else:
        will_propose = bool(acts) or any(
            s in {"proposed", "awaiting_approval", "approved", "executed"} for s in statuses
        )
        if not will_propose and not security:
            if kind.lower() in {"research", "ops"}:
                will_propose = False
            elif kind.lower() in {"incident", "opportunity", ""}:
                # Typical product loop opens with an eventual proposed change.
                will_propose = True
            else:
                will_propose = bool(arts & (_CODE_ARTIFACTS | _EXPERIMENT_ARTIFACTS))

    awaiting = any(s in {"proposed", "awaiting_approval"} for s in statuses)
    risk = bool(will_propose or awaiting or security or "risk_decision" in arts)
    approve = bool(awaiting or will_propose or security)
    coordinate = bool(arts & _COORD_ARTIFACTS or _truthy(dims.get("coordination")) or _truthy(dims.get("owners")))
    verify = bool(
        will_propose
        or has_code
        or has_experiment
        or any(s in {"approved", "executed"} for s in statuses)
        or "verify" in arts
        or "outcome" in arts
    )

    # Security review: observe → evidence → risk → human → learn (no ship/verify).
    if security:
        return Needs(
            signal=True,
            investigate=True,
            evidence=True,
            customer=False,
            feature=False,
            code=False,
            experiment=False,
            risk=True,
            approve=True,
            coordinate=False,
            verify=False,
            learn=True,
            security=True,
            tags=tags,
        )

    # Research / ops without a proposed change: lighter loop.
    if kind.lower() in {"research", "ops"} and not will_propose and not has_code and not has_experiment:
        return Needs(
            signal=True,
            investigate=True,
            evidence=True,
            customer=customer,
            feature=feature,
            code=False,
            experiment=False,
            risk=False,
            approve=False,
            coordinate=coordinate,
            verify=False,
            learn=True,
            security=False,
            tags=tags,
        )

    # Feature path: product + experiment unless a code_change already exists.
    if feature:
        code = has_code or "code_change" in acts
        # Type B without an existing code change → experiment path.
        experiment = has_experiment or not code
        return Needs(
            signal=True,
            investigate=True,
            evidence=True,
            customer=customer,
            feature=True,
            code=code,
            experiment=bool(experiment),
            risk=risk,
            approve=approve,
            coordinate=coordinate,
            verify=verify or bool(experiment) or code,
            learn=True,
            security=False,
            tags=tags,
        )

    # Bug / incident — code fix by default; experiment only when explicitly chosen.
    if dims.get("action_type") == "experiment" or "experiment" in acts:
        code = has_code
        has_experiment = True
    else:
        code = True
    return Needs(
        signal=True,
        investigate=True,
        evidence=True,
        customer=customer,
        feature=False,
        code=bool(code),
        experiment=bool(has_experiment),
        risk=risk,
        approve=approve,
        coordinate=coordinate,
        verify=verify or bool(code) or has_experiment,
        learn=True,
        security=False,
        tags=tags,
    )


def compose_nodes(needs: Needs) -> list[str]:
    """Ordered workflow nodes for this case."""
    nodes: list[str] = []
    if needs.signal:
        nodes.append("signal")
    if needs.investigate:
        nodes.append("investigate")
    if needs.evidence:
        nodes.append("evidence")
    if needs.customer:
        # Mail first, then call only non-responders — never spam-dial.
        nodes.append("customer_mail")
        nodes.append("customer_call")
    if needs.security:
        nodes.extend(["risk", "approve", "learn"] if needs.learn else ["risk", "approve"])
        # Dedup while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for n in nodes:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out
    if needs.feature:
        nodes.append("product")
    else:
        nodes.append("root_cause")
    if needs.code:
        nodes.append("code")
    if needs.experiment:
        nodes.append("experiment")
    if needs.risk:
        nodes.append("risk")
    if needs.approve:
        nodes.append("approve")
    if needs.coordinate:
        nodes.append("coordinate")
    if needs.verify:
        nodes.append("verify")
    if needs.learn:
        nodes.append("learn")
    seen2: set[str] = set()
    out2: list[str] = []
    for n in nodes:
        if n not in seen2:
            seen2.add(n)
            out2.append(n)
    return out2


def current_node(
    nodes: list[str],
    state: InvestigationState | str | None,
    *,
    awaiting: bool = False,
    artifact_types: Iterable[str] | None = None,
    needs: Needs | None = None,
) -> str:
    """Map investigation progress onto this instance's node list."""
    if not nodes:
        return "signal"
    arts = {str(a) for a in (artifact_types or []) if a}
    st = _as_state(state)

    if awaiting and "approve" in nodes:
        return "approve"

    # Artifact-led progress (more precise than state alone for mixed workflows).
    if arts & {"outcome", "learning", "verify"} and "verify" in nodes:
        if st and st in {
            InvestigationState.RESOLVED,
            InvestigationState.PARTIALLY_RESOLVED,
            InvestigationState.NOT_RESOLVED,
            InvestigationState.INCONCLUSIVE,
        }:
            return "learn" if "learn" in nodes else "verify"
        return "verify" if "verify" in nodes else nodes[-1]
    if arts & _COORD_ARTIFACTS and "coordinate" in nodes and st in {
        InvestigationState.APPROVED,
        InvestigationState.ACTING,
        None,
    }:
        if st in {InvestigationState.APPROVED, InvestigationState.ACTING}:
            return "coordinate"
    if arts & _CUSTOMER_ARTIFACTS and ("customer_mail" in nodes or "customer_call" in nodes or "customer" in nodes):
        # Still early if we only have voice context but not past hypothesis.
        if st in {None, InvestigationState.OPEN, InvestigationState.GATHERING, InvestigationState.HYPOTHESIS}:
            if not (arts & (_CODE_ARTIFACTS | {"risk_decision", "approval", "pr"})):
                if arts & {"call", "call_feedback", "call_transcript", "call_evidence"}:
                    if "customer_call" in nodes:
                        return "customer_call"
                    if "customer" in nodes:
                        return "customer"
                if arts & {"mail_outreach", "mail_reply", "user_cluster", "contact", "contact_lookup", "voice_context"}:
                    if "customer_mail" in nodes:
                        return "customer_mail"
                    if "customer" in nodes:
                        return "customer"

    hint = _STATE_HINT.get(st, "signal") if st else "signal"
    if st == InvestigationState.HYPOTHESIS:
        if needs and needs.feature and "product" in nodes:
            hint = "product"
        elif "root_cause" in nodes:
            hint = "root_cause"
        elif "product" in nodes:
            hint = "product"
        else:
            hint = "evidence"
    if st == InvestigationState.ACTION_PROPOSED and not awaiting:
        if "risk" in nodes:
            hint = "risk"
        elif "code" in nodes and arts & _CODE_ARTIFACTS:
            hint = "code"
        elif "experiment" in nodes:
            hint = "experiment"
    if st == InvestigationState.ACTING:
        if "coordinate" in nodes and arts & _COORD_ARTIFACTS:
            hint = "coordinate"
        elif "code" in nodes:
            hint = "code"
        elif "experiment" in nodes:
            hint = "experiment"
        elif "approve" in nodes:
            hint = "approve"

    if hint in nodes:
        return hint
    # Snap to nearest earlier node that exists.
    try:
        idx = CANONICAL_ORDER.index(hint)
    except ValueError:
        return nodes[0]
    for cand in reversed(CANONICAL_ORDER[: idx + 1]):
        if cand in nodes:
            return cand
    return nodes[0]


def steps_payload(nodes: list[str], current: str) -> list[dict[str, Any]]:
    idx = nodes.index(current) if current in nodes else 0
    return [
        {
            "id": n,
            "label": NODE_LABEL.get(n, n.replace("_", " ").title()),
            "short": NODE_SHORT.get(n, NODE_LABEL.get(n, n)),
            "detail": NODE_DETAIL.get(n, ""),
            "on": i <= idx,
        }
        for i, n in enumerate(nodes)
    ]


def kind_label(needs: Needs) -> str:
    if needs.security:
        return "security"
    if needs.feature:
        return "feature"
    return "bug"


def workflow_for(
    *,
    loop_type: LoopType | str | None = None,
    path: PathKind | str | None = None,
    room_kind: RoomKind | str | None = None,
    scenario_id: str | None = None,
    state: InvestigationState | str | None = None,
    awaiting: bool = False,
    dimensions: dict[str, Any] | None = None,
    artifact_types: Iterable[str] | None = None,
    action_types: Iterable[str] | None = None,
    action_statuses: Iterable[str] | None = None,
    propose_action: bool | None = None,
    signal_family: str | None = None,
    signal_source: str | None = None,
    members: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Full workflow instance for one room/investigation."""
    needs = infer_needs(
        loop_type=loop_type,
        path=path,
        room_kind=room_kind,
        scenario_id=scenario_id,
        dimensions=dimensions,
        artifact_types=artifact_types,
        action_types=action_types,
        action_statuses=action_statuses,
        propose_action=propose_action,
        signal_family=signal_family,
        signal_source=signal_source,
        members=members,
    )
    nodes = compose_nodes(needs)
    current = current_node(
        nodes,
        state,
        awaiting=awaiting,
        artifact_types=artifact_types,
        needs=needs,
    )
    return {
        "steps": steps_payload(nodes, current),
        "nodes": nodes,
        "current": current,
        "kind": kind_label(needs),
        "needs": {
            "customer": needs.customer,
            "code": needs.code,
            "experiment": needs.experiment,
            "approve": needs.approve,
            "coordinate": needs.coordinate,
            "verify": needs.verify,
            "security": needs.security,
            "feature": needs.feature,
        },
        "tags": list(needs.tags),
    }


def workflow_from_store(store: Any, room: Any, inv: Any | None = None) -> dict[str, Any]:
    """Build workflow for a room using messages + actions already on the store."""
    if inv is None and getattr(room, "investigation_id", None):
        inv = store.get_investigation(room.investigation_id)

    messages = store.list_messages(room.id) if hasattr(store, "list_messages") else []
    arts = [m.artifact_type for m in messages if getattr(m, "artifact_type", None)]

    actions = store.list_actions(inv.id) if inv and hasattr(store, "list_actions") else []
    action_types = [getattr(a, "type", None) for a in actions]
    action_statuses = [getattr(a, "status", None) for a in actions]
    awaiting = any(s in {"proposed", "awaiting_approval"} for s in action_statuses)

    dimensions: dict[str, Any] = {}
    signal_family = None
    signal_source = None
    stored_nodes: list[str] | None = None
    stored_needs: dict[str, Any] | None = None
    # Recover dimensions from the opening signal artifact when present.
    for m in messages:
        art = m.artifact if isinstance(getattr(m, "artifact", None), dict) else {}
        if m.artifact_type == "workflow" and isinstance(art.get("nodes"), list):
            stored_nodes = [str(n) for n in art["nodes"]]
            if isinstance(art.get("needs"), dict):
                stored_needs = art["needs"]
        if m.artifact_type == "signal":
            dimensions.setdefault("metric", art.get("metric"))
            if art.get("family"):
                signal_family = str(art.get("family"))
            if art.get("kind"):
                dimensions.setdefault("kind", art.get("kind"))
            if art.get("source"):
                signal_source = str(art.get("source"))
        if m.artifact_type in {
            "voice_context",
            "voice",
            "contact",
            "call",
            "call_feedback",
            "call_transcript",
            "call_evidence",
        }:
            raw = art.get("raw") if isinstance(art.get("raw"), dict) else {}
            sub = art.get("voice_subject") or art.get("subject") or art.get("customer") or raw
            # Empty generic voice_context (no subject) must not force a call step.
            if isinstance(sub, dict) and sub:
                dimensions["voice_subject"] = sub
                dimensions["needs_call"] = True
            elif m.artifact_type in {
                "contact",
                "call",
                "call_feedback",
                "call_transcript",
                "call_evidence",
            }:
                dimensions["needs_call"] = True
            elif art.get("phone") or art.get("to_number"):
                dimensions["needs_call"] = True
        if isinstance(art.get("voice_subject"), dict) and art["voice_subject"]:
            dimensions["voice_subject"] = art["voice_subject"]
            dimensions["needs_call"] = True

    # Seed dimensions from topic/title for voice without hardcoding scenario ids.
    topic = f"{getattr(room, 'title', '')} {getattr(room, 'topic', '')}".lower()
    if any(w in topic for w in ("call ", " called", "customer said", "feedback call", "callback")):
        dimensions.setdefault("needs_call", True)

    # Analytics / dependency-only: explicit skip when no voice artifacts and source is telemetry.
    if not dimensions.get("voice_subject") and not dimensions.get("needs_call"):
        src_blob = f"{signal_source or ''} {dimensions.get('kind') or ''}".lower()
        if any(k in src_blob for k in ("ga4", "analytics", "bigquery", "dependency", "npm", "cargo", "upgrade")):
            dimensions["skip_customer"] = True

    if stored_needs:
        if stored_needs.get("customer"):
            dimensions["needs_call"] = True
        if stored_needs.get("customer") is False:
            dimensions["skip_customer"] = True

    wf = workflow_for(
        loop_type=getattr(room, "loop_type", None) or (getattr(inv, "loop_type", None) if inv else None),
        path=getattr(room, "path", None),
        room_kind=getattr(room, "kind", None),
        scenario_id=getattr(room, "scenario_id", None),
        state=getattr(inv, "state", None) if inv else None,
        awaiting=awaiting,
        dimensions=dimensions,
        artifact_types=arts,
        action_types=action_types,
        action_statuses=action_statuses,
        signal_family=signal_family,
        signal_source=signal_source,
        members=getattr(room, "members", None),
    )
    if stored_nodes:
        nodes = order_nodes(stored_nodes)
        for extra in wf.get("nodes") or []:
            if extra not in nodes:
                nodes = order_nodes([*nodes, extra])
        current = current_node(
            nodes,
            getattr(inv, "state", None) if inv else None,
            awaiting=awaiting,
            artifact_types=arts,
        )
        wf = {
            **wf,
            "nodes": nodes,
            "current": current,
            "steps": steps_payload(nodes, current),
        }
    return wf


def order_nodes(nodes: Iterable[str]) -> list[str]:
    present = {str(n) for n in nodes if n}
    return [n for n in CANONICAL_ORDER if n in present] + sorted(present - set(CANONICAL_ORDER))


def union_columns(workflows: Iterable[dict[str, Any]]) -> list[str]:
    """Homepage / pipeline columns = union of active instance nodes (canonical order)."""
    present: set[str] = set()
    for wf in workflows:
        for n in wf.get("nodes") or []:
            present.add(str(n))
        cur = wf.get("current")
        if cur:
            present.add(str(cur))
    if not present:
        return []
    return order_nodes(present)


def to_live_column(node_or_artifact_col: str) -> str | None:
    """Collapse fine funnel nodes into homepage live-work columns."""
    n = str(node_or_artifact_col or "")
    if n in LIVE_ORDER:
        return n
    if n in {"investigate", "root_cause", "product", "evidence"}:
        return "evidence"
    if n in {"risk", "approve", "coordinate"}:
        return "approve"
    if n in {"learn", "verify"}:
        return "verify"
    if n in {"customer", "customer_mail", "customer_call"}:
        return "customer"
    if n in {"code", "patch", "pr"}:
        return "code"
    if n == "experiment":
        return "experiment"
    if n == "signal":
        return "signal"
    return None


def live_columns_from_workflows(
    workflows: Iterable[dict[str, Any]],
    *,
    card_columns: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    present: set[str] = set()
    for wf in workflows:
        for n in wf.get("nodes") or []:
            live = to_live_column(str(n))
            if live:
                present.add(live)
    for c in card_columns or []:
        live = to_live_column(str(c))
        if live:
            present.add(live)
    if not present:
        present = {"signal", "evidence", "code", "approve", "verify"}
    ordered = [c for c in LIVE_ORDER if c in present]
    return [{"id": c, "label": LIVE_LABEL.get(c, c.title()), "count": 0} for c in ordered]


def focus_steps(workflow: dict[str, Any] | None = None, orchestration: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Homepage narrator steps — progressive reveal only (no fixed spine)."""
    from .orchestration import focus_steps_progressive

    if orchestration:
        return focus_steps_progressive(orchestration)
    if orchestration is None and workflow is None:
        return []
    if workflow and workflow.get("steps"):
        # Legacy: collapse to progressive slice (done + active + next only).
        steps = workflow["steps"]
        cur = workflow.get("current")
        cur_idx = next((i for i, s in enumerate(steps) if s.get("id") == cur), len(steps) - 1)
        visible = [s for i, s in enumerate(steps) if i <= cur_idx + 1]
        return [
            {
                "n": i + 1,
                "id": s["id"],
                "short": s.get("short") or s.get("label") or s["id"],
                "label": s.get("label") or s["id"],
                "detail": s.get("detail") or "",
                "stage": s["id"],
                "on": s.get("on", False),
                "status": "done" if i < cur_idx else ("active" if i == cur_idx else "next"),
                "agent": s.get("agent"),
            }
            for i, s in enumerate(visible)
        ]
    return []


# Back-compat aliases used by older call sites.
PIPELINE_BUG = [
    "signal",
    "investigate",
    "evidence",
    "root_cause",
    "code",
    "risk",
    "approve",
    "verify",
    "learn",
]
PIPELINE_FEATURE = [
    "signal",
    "investigate",
    "evidence",
    "product",
    "experiment",
    "risk",
    "approve",
    "verify",
    "learn",
]
PIPELINE_LABEL = NODE_LABEL
