"""Capability-composed workflows — different cases get different node graphs."""

from __future__ import annotations

from loop.models import InvestigationState, LoopType, PathKind, RoomKind
from loop.workflow import compose_nodes, infer_needs, workflow_for


def test_customer_call_path_includes_customer_node():
    wf = workflow_for(
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.INCIDENT,
        state=InvestigationState.HYPOTHESIS,
        dimensions={"voice_subject": {"name": "Alex", "failure": "timeout"}},
        propose_action=True,
    )
    assert "customer_mail" in wf["nodes"]
    assert "customer_call" in wf["nodes"]
    assert wf["needs"]["customer"] is True
    assert "code" in wf["nodes"]
    assert wf["kind"] == "bug"


def test_analytics_dependency_upgrade_skips_customer():
    wf = workflow_for(
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.INCIDENT,
        state=InvestigationState.HYPOTHESIS,
        dimensions={
            "skip_customer": True,
            "code": {"dependency": "payments-sdk", "version": "3.2.1"},
        },
        signal_source="ga4",
        propose_action=True,
    )
    assert "customer" not in wf["nodes"]
    assert "code" in wf["nodes"]
    assert wf["needs"]["customer"] is False


def test_feature_path_uses_product_and_experiment():
    wf = workflow_for(
        loop_type=LoopType.TYPE_B,
        path=PathKind.FEATURE,
        room_kind=RoomKind.OPPORTUNITY,
        state=InvestigationState.HYPOTHESIS,
        propose_action=True,
    )
    assert "product" in wf["nodes"]
    assert "experiment" in wf["nodes"]
    assert "root_cause" not in wf["nodes"]
    assert wf["current"] == "product"
    assert wf["kind"] == "feature"


def test_security_review_has_no_ship_verify():
    wf = workflow_for(
        loop_type=LoopType.TYPE_A,
        path=PathKind.SECURITY,
        room_kind=RoomKind.REVIEW,
        state=InvestigationState.ACTION_PROPOSED,
        awaiting=True,
    )
    assert wf["kind"] == "security"
    assert "code" not in wf["nodes"]
    assert "verify" not in wf["nodes"]
    assert "approve" in wf["nodes"]
    assert wf["current"] == "approve"


def test_research_without_propose_is_light():
    needs = infer_needs(
        loop_type=LoopType.TYPE_B,
        room_kind=RoomKind.RESEARCH,
        propose_action=False,
        dimensions={"voice_subject": {"name": "Sam"}},
    )
    nodes = compose_nodes(needs)
    assert "customer_mail" in nodes
    assert "customer_call" in nodes
    assert "approve" not in nodes
    assert "code" not in nodes
    assert nodes[-1] == "learn"


def test_unseen_coordination_case_adds_coordinate():
    wf = workflow_for(
        loop_type=LoopType.TYPE_A,
        room_kind=RoomKind.INCIDENT,
        state=InvestigationState.ACTING,
        artifact_types=["signal", "evidence", "coordination"],
        action_types=["code_change"],
        action_statuses=["approved"],
        propose_action=True,
    )
    assert "coordinate" in wf["nodes"]


def test_funnel_compat_type_a_hypothesis():
    from loop.live import funnel_for

    bug = funnel_for(LoopType.TYPE_A, InvestigationState.HYPOTHESIS)
    feat = funnel_for(LoopType.TYPE_B, InvestigationState.HYPOTHESIS)
    assert bug["kind"] == "bug"
    assert feat["kind"] == "feature"
    assert bug["current"] == "root_cause"
    assert feat["current"] == "product"
