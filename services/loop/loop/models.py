"""PRD §23 entities. Field lists are the required minimum."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SignalFamily(str, Enum):
    TECHNICAL = "technical"
    BUSINESS = "business"
    CUSTOMER = "customer"


class Direction(str, Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


class SignalStatus(str, Enum):
    OPEN = "open"
    SUPPRESSED = "suppressed"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class InvestigationState(str, Enum):
    OPEN = "OPEN"
    GATHERING = "GATHERING"
    HYPOTHESIS = "HYPOTHESIS"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    ACTING = "ACTING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    INCONCLUSIVE = "INCONCLUSIVE"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TrustLevel(str, Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class OutcomeVerdict(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    INCONCLUSIVE = "INCONCLUSIVE"


class Classification(str, Enum):
    BUG = "BUG"
    OPPORTUNITY = "OPPORTUNITY"


class RoomKind(str, Enum):
    INCIDENT = "incident"
    OPPORTUNITY = "opportunity"
    REVIEW = "review"
    RESEARCH = "research"
    OPS = "ops"


class LoopType(str, Enum):
    TYPE_A = "type_a"
    TYPE_B = "type_b"


class PathKind(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    SECURITY = "security"


class Segment(BaseModel):
    platform: str | None = None
    os: str | None = None
    browser: str | None = None
    app_version: str | None = None
    geo: str | None = None
    channel: str | None = None


class Signal(BaseModel):
    id: str
    family: SignalFamily
    direction: Direction
    funnel_position: str
    metric: str
    magnitude: float
    baseline: float
    affected_segments: list[Segment]
    detection_window: dict[str, str]
    confidence: float
    source: str
    status: SignalStatus = SignalStatus.OPEN
    suppression_reason: str | None = None
    detected_at: datetime


class Investigation(BaseModel):
    id: str
    originating_signal_ids: list[str]
    state: InvestigationState
    opened_at: datetime
    closed_at: datetime | None = None
    invocation_id: str
    assigned_agents: list[str] = Field(default_factory=list)
    token_budget: int = 200_000
    tokens_consumed: int = 0
    linked_hypothesis_ids: list[str] = Field(default_factory=list)
    linked_action_ids: list[str] = Field(default_factory=list)
    verification_result: str | None = None
    recalled_lessons: list[str] = Field(default_factory=list)
    scenario_id: str | None = None
    room_id: str | None = None
    tenant_id: str | None = None
    loop_type: LoopType | None = None
    title: str | None = None


class Evidence(BaseModel):
    id: str
    investigation_id: str
    source_type: str
    source_reference: str
    claim: str
    confidence: float
    trust_level: TrustLevel
    collected_by: str
    collected_at: datetime
    weight: float
    independence_group: str


class Hypothesis(BaseModel):
    id: str
    investigation_id: str
    statement: str
    classification: Classification
    confidence: float
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    cited_memory: list[str] = Field(default_factory=list)
    rank: int
    independence_groups: list[str]


class ProposedAction(BaseModel):
    id: str
    investigation_id: str
    type: Literal["code_change", "product_proposal", "experiment", "flag_rollback"]
    risk_tier: RiskTier
    tier_rationale: str
    required_approver_role: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    status: str = "proposed"
    consequence: str


class Approval(BaseModel):
    id: str
    action_id: str
    approver_identity: str
    decision: Literal["approve", "deny"]
    rationale: str
    timestamp: datetime
    tier_at_decision: RiskTier


class Outcome(BaseModel):
    id: str
    investigation_id: str
    metric: str
    pre_value: float
    post_value: float
    control_comparison: float | None = None
    delta: float
    verdict: OutcomeVerdict
    measured_at: datetime


class Lesson(BaseModel):
    id: str
    investigation_id: str
    statement: str
    root_cause_family: str
    applicable_conditions: list[str]
    linked_playbook_skill: str | None = None
    confidence: float
    author_agent: str
    human_reviewer: str | None = None
    tenant_id: str | None = None


class PolicyVerdict(BaseModel):
    id: str
    agent_identity: str
    tool: str
    arguments_digest: str
    verdict: Literal["ALLOW", "DENY", "BLOCK"]
    rationale: str
    enforcement_mode: str
    token_usage: int = 0
    timestamp: datetime
    finding_type: str | None = None


class TimelineEvent(BaseModel):
    id: str
    investigation_id: str
    at: datetime
    actor: str
    kind: str
    title: str
    detail: str
    denial: bool = False


class AgentCall(BaseModel):
    id: str
    investigation_id: str
    from_agent: str
    to_agent: str
    trust_boundary: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    summary: str = ""


class Room(BaseModel):
    id: str
    kind: RoomKind
    title: str
    topic: str
    status: str = "open"
    created_at: datetime
    members: list[str] = Field(default_factory=list)
    investigation_id: str | None = None
    scenario_id: str | None = None
    tenant_id: str | None = None
    loop_type: LoopType | None = None
    path: PathKind | None = None
    last_message_at: datetime | None = None


class RoomMessage(BaseModel):
    id: str
    room_id: str
    author: str
    author_kind: Literal["agent", "human", "system"]
    kind: Literal["chat", "artifact", "approval", "system"]
    text: str
    artifact_type: str | None = None
    artifact: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RegistryEntry(BaseModel):
    id: str
    display_name: str
    owner: str
    capabilities: list[str]
    permissions_allow: list[str]
    permissions_deny: list[str]
    version: str
    environment: str
    risk_level: str
    status: str
    identity: str
    room: str
    role: str
    trust_boundary: str
