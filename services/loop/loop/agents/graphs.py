"""Deterministic Type A / Type B graph runner — product-os-v2 + ADK 2 energy.

ADK 2 prefers Workflow + JoinNode + RequestInput. Hosted LOOP keeps this
deterministic runner as the always-on path (no Gemini required). When
google-adk is present, workflow_catalog() / build_*_workflow() attach.
"""

from __future__ import annotations

from typing import Any, Callable

from .workflows import build_hitl_gate_spec, workflow_catalog

# Fan-out investigators (JoinNode barrier equivalent in the deterministic path).
INVESTIGATORS = (
    "analytics_agent",
    "logs_agent",
    "deployment_agent",
    "database_agent",
    "customer_agent",
    "research_agent",
)

PIPELINE_BUG = (
    "commander_agent",
    "signal_agent",
    "investigator_agent",
    *INVESTIGATORS,
    "evidence_agent",
    "root_cause_agent",
    "code_agent",
    "risk_agent",
    "coordinator_agent",
    "learning_agent",
)

PIPELINE_FEATURE = (
    "commander_agent",
    "signal_agent",
    "investigator_agent",
    *INVESTIGATORS,
    "evidence_agent",
    "product_agent",
    "experiment_agent",
    "risk_agent",
    "coordinator_agent",
    "learning_agent",
)


def graph_for(fork: str = "BUG") -> tuple[str, ...]:
    return PIPELINE_FEATURE if fork.upper() == "FEATURE" else PIPELINE_BUG


def run_presence_sweep(
    room_id: str,
    fork: str,
    set_presence: Callable[[str, str, str], None],
    publish: Callable[[str, dict[str, Any]], None] | None = None,
) -> list[str]:
    """Walk the pipeline once, flashing presence (thinking → idle) per agent.

    Used by scenario run / agent_callback demos so the console HandoffRail
    lights up without requiring Gemini.
    """
    order = graph_for(fork)
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
    return list(order)


def adk2_alignment() -> dict[str, Any]:
    """How this repo maps SalesShortcut 1.x patterns onto ADK 2.0."""
    cat = workflow_catalog()
    hitl = build_hitl_gate_spec()
    return {
        "adk": "2.x",
        "adk_version": "2.x",
        "deprecated_1x": ["SequentialAgent", "ParallelAgent", "LoopAgent"],
        "preferred_2x": ["Workflow", "JoinNode", "RequestInput", "Workflow-as-Tool≥2.4"],
        "hosted_source_of_truth": "LoopEngine (deterministic)",
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
        },
    }
