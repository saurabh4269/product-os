"""Room UI card/status mapping — GitHub receipts and pending approvals."""

from __future__ import annotations

from datetime import UTC, datetime

from loop.code_fix import run_code_fix_job
from loop.jobs import enqueue_code_fix
from loop.models import (
    Investigation,
    InvestigationState,
    ProposedAction,
    RiskTier,
    Room,
    RoomKind,
)
from loop.room_ui import (
    github_card_lifecycle,
    investigation_pr_url,
    receipt_proof_status,
    suppress_pending_action,
    visible_pending_actions,
    visible_pending_approvals,
)
from loop.tenant import ConnectorReport


def test_github_card_lifecycle_prefers_open_pr():
    assert github_card_lifecycle(pr_url="https://github.com/acme/y/pull/12", connector_status="failed") == "done"
    assert github_card_lifecycle(pr_url=None, connector_status="failed") == "failed"
    assert github_card_lifecycle(pr_url=None, connector_status="applied") == "done"
    assert github_card_lifecycle(pr_url=None, connector_status="running") == "running"


def test_receipt_proof_status_never_failed_when_pr_open():
    assert receipt_proof_status(kind="github", receipt_status="failed", pr_url="https://github.com/acme/y/pull/3") == "done"
    assert receipt_proof_status(kind="github", receipt_status="failed", pr_url=None) == "failed"
    assert receipt_proof_status(kind="code_fix", receipt_status="failed", pr_url="https://github.com/acme/y/pull/3") == "failed"


def _room_bundle(engine):
    tenant = __import__("loop.tenant", fromlist=["Tenant"]).Tenant(
        id="brandx",
        name="Brand X",
        product="Brand X",
        repo="org/shop",
        connected=True,
        stack="nextjs",
        flag_names=["checkout_v2"],
        code_paths=["src/checkout.ts"],
    )
    engine.store.put_tenant(tenant)
    inv = Investigation(
        id="inv_room_ui",
        originating_signal_ids=[],
        state=InvestigationState.AWAITING_APPROVAL,
        opened_at=datetime.now(UTC),
        invocation_id="x",
        scenario_id="t:brandx:checkout_drop",
        tenant_id="brandx",
        title="Brand X: checkout_drop",
        room_id="room_room_ui",
    )
    engine.store.put_investigation(inv)
    engine.store.put_room(
        Room(
            id="room_room_ui",
            title="Checkout",
            topic="checkout",
            kind=RoomKind.INCIDENT,
            created_at=datetime.now(UTC),
            investigation_id=inv.id,
            members=["you", "code_agent"],
        )
    )
    return tenant, inv


def test_visible_pending_actions_hides_duplicate_code_change(engine):
    tenant, inv = _room_bundle(engine)
    shipped = ProposedAction(
        id="act_shipped",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={
            "flag": "checkout_v2",
            "execution": {
                "pr_opened": True,
                "pr_url": "https://github.com/org/shop/pull/7",
            },
        },
        idempotency_key="idem_shipped",
        status="executed",
        consequence="Opened PR on org/shop",
    )
    duplicate = ProposedAction(
        id="act_dup",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"flag": "checkout_v2", "code_fix": True},
        idempotency_key="idem_dup",
        status="awaiting_approval",
        consequence="Duplicate rollback",
    )
    engine.store.put_action(shipped)
    engine.store.put_action(duplicate)
    assert investigation_pr_url(engine.store, inv.id).endswith("/pull/7")
    assert suppress_pending_action(engine.store, duplicate) is True
    assert [a.id for a in visible_pending_actions(engine.store, inv.id)] == []


def test_code_fix_failure_skips_github_failed_receipt_when_flag_pr_open(engine, monkeypatch):
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: ConnectorReport(
            status="failed",
            connector="code_fix",
            detail="tests failed",
        ),
    )
    tenant, inv = _room_bundle(engine)
    action = ProposedAction(
        id="act_cf",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={
            "flag": "checkout_v2",
            "code_fix": True,
            "execution": {
                "pr_opened": True,
                "pr_url": "https://github.com/org/shop/pull/7",
            },
        },
        idempotency_key="idem_cf",
        status="executed",
        consequence="Open PR on org/shop",
    )
    engine.store.put_action(action)
    posted: list[dict] = []

    def capture(engine, room_id, **kwargs):
        posted.append(kwargs)

    monkeypatch.setattr("loop.receipts.post_receipt", capture)

    job = enqueue_code_fix(
        engine.store,
        action_id=action.id,
        investigation_id=inv.id,
        tenant_id=tenant.id,
        brief={"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
        flag_patch={"checkout_v2": "off"},
        pr_title="Fix checkout",
        pr_body="body",
        flag_pr_opened=True,
    )
    run_code_fix_job(engine, job)
    assert len(posted) == 1
    assert posted[0]["kind"] == "code_fix"
    assert posted[0].get("open_url") is None
    assert posted[0]["proof"]["kind"] == "code_fix"


def test_bundle_pending_actions_filtered(engine):
    from loop.api import _bundle

    tenant, inv = _room_bundle(engine)
    shipped = ProposedAction(
        id="act_shipped2",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"execution": {"pr_url": "https://github.com/org/shop/pull/9"}},
        idempotency_key="idem_shipped2",
        status="executed",
        consequence="Opened PR",
    )
    duplicate = ProposedAction(
        id="act_dup2",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"flag": "checkout_v2"},
        idempotency_key="idem_dup2",
        status="awaiting_approval",
        consequence="Duplicate rollback",
    )
    engine.store.put_action(shipped)
    engine.store.put_action(duplicate)
    bundle = _bundle(engine, inv.id)
    assert len(bundle["actions"]) == 2
    assert bundle["pending_actions"] == []


def test_room_message_summary_without_loading_all(engine):
    from loop.models import RoomMessage, Room, RoomKind
    from datetime import UTC, datetime

    room = Room(
        id="room_summary",
        title="Summary",
        topic="t",
        kind=RoomKind.INCIDENT,
        created_at=datetime.now(UTC),
        members=["you"],
    )
    engine.store.put_room(room)
    for i in range(5):
        engine.store.put_message(
            RoomMessage(
                id=f"msg_{i}",
                room_id=room.id,
                author="a",
                author_kind="agent",
                kind="chat",
                text=f"line {i}",
                created_at=datetime.now(UTC),
            )
        )
    count, preview = engine.store.room_message_summary(room.id)
    assert count == 5
    assert preview == "line 4"


def test_slim_room_bundle_caps_payload(engine):
    from loop.api import _bundle

    tenant, inv = _room_bundle(engine)
    full = _bundle(engine, inv.id, slim=False)
    slim = _bundle(engine, inv.id, slim=True)
    assert len(full["approvals"]) >= 0
    assert slim["approvals"] == []
    assert len(slim["timeline"]) <= len(full["timeline"])


def test_visible_pending_approvals_hides_duplicate_globally(engine):
    tenant, inv = _room_bundle(engine)
    shipped = ProposedAction(
        id="act_shipped_global",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"execution": {"pr_url": "https://github.com/org/shop/pull/11"}},
        idempotency_key="idem_shipped_global",
        status="executed",
        consequence="Opened PR",
    )
    duplicate = ProposedAction(
        id="act_dup_global",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"flag": "checkout_v2"},
        idempotency_key="idem_dup_global",
        status="awaiting_approval",
        consequence="Duplicate rollback",
    )
    engine.store.put_action(shipped)
    engine.store.put_action(duplicate)
    assert len(engine.store.pending_approvals()) == 1
    assert visible_pending_approvals(engine.store) == []


def test_approvals_api_hides_duplicate_pending(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from loop import api as api_mod

    tenant, inv = _room_bundle(engine)
    shipped = ProposedAction(
        id="act_shipped_api",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"execution": {"pr_url": "https://github.com/org/shop/pull/12"}},
        idempotency_key="idem_shipped_api",
        status="executed",
        consequence="Opened PR",
    )
    duplicate = ProposedAction(
        id="act_dup_api",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"flag": "checkout_v2"},
        idempotency_key="idem_dup_api",
        status="awaiting_approval",
        consequence="Duplicate rollback",
    )
    engine.store.put_action(shipped)
    engine.store.put_action(duplicate)
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        body = client.get("/api/approvals").json()
    assert body["pending"] == []


def test_decide_blocks_duplicate_high_when_pr_open(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from loop import api as api_mod

    tenant, inv = _room_bundle(engine)
    shipped = ProposedAction(
        id="act_shipped_gate",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"execution": {"pr_url": "https://github.com/org/shop/pull/17"}},
        idempotency_key="idem_shipped_gate",
        status="executed",
        consequence="Opened PR",
    )
    duplicate = ProposedAction(
        id="act_4754e1ae24f5",
        investigation_id=inv.id,
        type="code_change",
        risk_tier=RiskTier.HIGH,
        tier_rationale="checkout surface",
        required_approver_role="eng-manager",
        artifacts={"flag": "checkout_v2"},
        idempotency_key="idem_dup_gate",
        status="awaiting_approval",
        consequence="Duplicate rollback",
    )
    engine.store.put_action(shipped)
    engine.store.put_action(duplicate)
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        blocked = client.post(
            f"/api/approvals/{duplicate.id}",
            json={"decision": "approve", "approver": "oncall@brandx", "rationale": "retry"},
        )
    assert blocked.status_code == 409
    assert "duplicate" in blocked.json()["detail"].lower()
    """Leftover HIGH is hidden after a flags PR — same-metric ingest must still join, not open a new room."""
    from loop.tenant import Tenant, hash_token
    from loop.world import ingest_tenant_signal, tenant_ingest_should_join_room

    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    tenant = Tenant(
        id="brandx",
        name="Brand X",
        product="Brand X",
        repo="org/shop",
        token_hash=hash_token("tok"),
        connected=True,
        flag_names=["checkout_v2"],
    )
    engine.store.put_tenant(tenant)
    first = ingest_tenant_signal(
        engine,
        tenant,
        metric="otp_verify_hang_0904",
        magnitude=-0.2,
        baseline=0.1,
        note="OTP hang",
        async_finish=False,
    )
    inv = engine.store.get_investigation(first["investigation_id"])
    assert inv
    shipped = False
    for act in engine.store.list_actions(inv.id):
        if not shipped:
            act.status = "executed"
            art = dict(act.artifacts or {})
            art["execution"] = {"pr_opened": True, "pr_url": "https://github.com/org/shop/pull/17"}
            act.artifacts = art
            engine.store.put_action(act)
            shipped = True
    inv.state = InvestigationState.AWAITING_APPROVAL
    inv.closed_at = None
    engine.store.put_investigation(inv)
    assert tenant_ingest_should_join_room(engine, inv) is True
    inv.state = InvestigationState.ACTING
    engine.store.put_investigation(inv)
    assert tenant_ingest_should_join_room(engine, inv) is True
    again = ingest_tenant_signal(
        engine,
        tenant,
        metric="otp_verify_hang_0904",
        magnitude=-0.18,
        baseline=0.1,
        note="OTP hang again",
        async_finish=False,
    )
    assert again.get("joined") is True
    assert again["room_id"] == first["room_id"]
