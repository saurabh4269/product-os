"""ADK 2.0 Workflow graphs — supersede pre-2.0 Sequential/Parallel/Loop agents.

Typical pre–ADK-2 stacks used:
  SequentialAgent, ParallelAgent, LoopAgent + before_tool_callback skip-if-done.

ADK 2.0 prefers:
  Workflow + START + JoinNode (fan-out/join)
  RequestInput / ResumeOrRequestInput (HITL pause)
  Workflow-as-Tool on LlmAgent (ADK ≥2.4; needs input_schema)
  App resumability_config

Hosted LOOP still runs the deterministic engine (no Gemini required).
These graphs attach when google-adk is present.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InvestigationIn(BaseModel):
    """Input for investigation_fanout when used as Workflow-as-Tool."""

    room_id: str = Field(default="", description="Room to attach evidence into")
    fork: str = Field(default="BUG", description="BUG or FEATURE pipeline")


class CritiqueIn(BaseModel):
    draft: str = Field(default="", description="Proposal draft to critique")


def build_investigation_workflow() -> Any | None:
    """Parallel fan-out of analytics/logs/deploy/db/customer/code → JoinNode (ADK 2)."""
    try:
        from google.adk import Workflow
        from google.adk.workflow import START, JoinNode
    except ImportError:
        try:
            from google.adk.workflows import Workflow  # type: ignore

            START = "START"  # type: ignore
            JoinNode = None  # type: ignore
        except ImportError:
            return None

    async def analytics_node(_inp=None):
        return {"source": "analytics", "independence_group": "ga4"}

    async def logs_node(_inp=None):
        return {"source": "logs", "independence_group": "error_budget"}

    async def deploy_node(_inp=None):
        return {"source": "deploy", "independence_group": "release"}

    async def database_node(_inp=None):
        return {"source": "database", "independence_group": "database"}

    async def customer_node(_inp=None):
        return {"source": "customer", "independence_group": "customer_voice"}

    async def code_node(_inp=None):
        return {"source": "code", "independence_group": "code"}

    def join_evidence(node_input=None, **_k):
        if isinstance(node_input, dict) and any(
            k.startswith("fetch") or k.endswith("_node") for k in node_input
        ):
            parts = [v for v in node_input.values() if isinstance(v, dict) and "source" in v]
        else:
            parts = [p for p in (node_input if isinstance(node_input, list) else []) if p]
            if not parts and isinstance(node_input, dict) and "source" in node_input:
                parts = [node_input]
        groups = sorted({p["independence_group"] for p in parts if "independence_group" in p})
        return {
            "evidence": parts,
            "groups": groups,
            "confidence": round(min(0.97, 0.5 + 0.08 * len(groups)), 3),
        }

    fanout = [
        analytics_node,
        logs_node,
        deploy_node,
        database_node,
        customer_node,
        code_node,
    ]

    try:
        if JoinNode is not None:
            joiner = JoinNode(name="evidence_join")
            return Workflow(
                name="investigation_fanout",
                description=(
                    "Fan-out analytics/logs/deploy/db/customer/code evidence, then join. "
                    "Replaces ParallelAgent from ADK 1.x."
                ),
                input_schema=InvestigationIn,
                edges=[(START, node, joiner) for node in fanout] + [(joiner, join_evidence)],
            )
        return Workflow(
            name="investigation_fanout",
            description="Fan-out six investigators, then join.",
            input_schema=InvestigationIn,
            edges=[("START", n) for n in fanout] + [(n, join_evidence) for n in fanout],
        )
    except TypeError:
        return None


def build_proposal_critique_workflow() -> Any | None:
    """Draft → critique (Review pattern) as an ADK 2 Workflow."""
    try:
        from google.adk import Workflow
        from google.adk.workflow import START
    except ImportError:
        try:
            from google.adk.workflows import Workflow  # type: ignore

            START = "START"  # type: ignore
        except ImportError:
            return None

    def draft(_inp=None):
        return {"draft": "proposal skeleton", "status": "draft"}

    def critique(node_input=None, **_k):
        body = node_input if isinstance(node_input, dict) else {}
        return {**body, "status": "reviewed", "ok": True}

    try:
        return Workflow(
            name="proposal_critique",
            description="Draft then critique a proposal. Replaces LoopAgent review cycles.",
            input_schema=CritiqueIn,
            edges=[(START, draft, critique)],
        )
    except TypeError:
        return None


def build_hitl_gate_spec() -> dict[str, Any]:
    """Document RequestInput HITL — mirrored by skip-if-done approve in api.py."""
    return {
        "pattern": "RequestInput",
        "hosted": "POST /api/approvals/{id} with skip-if-done when already executed",
        "adk": "node yields RequestInput → runner pauses → human reply resumes checkpoint",
    }


def workflow_catalog() -> dict[str, str]:
    inv = build_investigation_workflow()
    prop = build_proposal_critique_workflow()
    hitl = build_hitl_gate_spec()
    return {
        "adk_version": "2.x",
        "investigation_fanout": "available" if inv else "unavailable",
        "proposal_critique": "available" if prop else "unavailable",
        "hitl": hitl["pattern"],
        "note": (
            "ADK 2 Workflow + JoinNode + RequestInput replace SequentialAgent/"
            "ParallelAgent/LoopAgent from the pre-2.0 ADK era. "
            "Workflow-as-Tool (≥2.4) needs Pydantic input_schema on the Workflow. "
            "Hosted LOOP uses the deterministic engine; graphs attach when ADK is present."
        ),
    }


def workflow_tools() -> list[Any]:
    """Workflow-as-Tool list for LlmAgent(tools=[...]) when ADK ≥2.4 is installed.

    NodeTool requires an explicit Pydantic input_schema on the wrapped node.
    """
    out: list[Any] = []
    for wf in (build_investigation_workflow(), build_proposal_critique_workflow()):
        if wf is None:
            continue
        if not getattr(wf, "input_schema", None):
            continue
        if not getattr(wf, "description", None):
            try:
                wf.description = getattr(wf, "name", "workflow")
            except Exception:
                pass
        out.append(wf)
    return out
