"""Production-grade E2E — ambient loop, auth, jobs, gateway, pubsub, status."""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.auth import require_admin_or_internal, verify_internal_oidc
from loop.jobs import enqueue_verify, process_job
from loop.models import InvestigationState, RiskTier
from loop.pubsub_consumer import decode_push, handle_signal_push
from loop.signal_watch import tick_signal_watch
from loop.tenant import Tenant, hash_token
from loop.worker_heartbeat import last_tick, record_tick


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as c:
        yield c


def test_worker_tick_detects_and_records_heartbeat(client, engine, monkeypatch):
    monkeypatch.setenv("LOOP_AUTO_INVESTIGATE", "1")
    res = client.post("/api/internal/worker/tick")
    assert res.status_code == 200
    body = res.json()
    assert body["detected"] >= 0
    hb = last_tick()
    assert hb.get("count") is not None
    assert client.get("/api/status").json()["worker"].get("last_worker_tick")


def test_worker_auth_with_secret_header(engine, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "prod-secret")
    monkeypatch.setenv("LOOP_DEV_OPEN", "0")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        denied = client.post("/api/internal/worker/tick")
        assert denied.status_code == 401
        ok = client.post("/api/internal/worker/tick", headers={"X-Loop-Worker": "prod-secret"})
        assert ok.status_code == 200


def test_require_admin_or_internal_local_open(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("LOOP_ADMIN_TOKEN", raising=False)
    assert require_admin_or_internal(None) == "worker"


def test_verify_internal_oidc_rejects_garbage(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://example.test")
    assert verify_internal_oidc("not-a-jwt") is False


def test_pubsub_push_ingest(client, engine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Y", token_hash=hash_token("tok"), repo="acme/y")
    )
    payload = {
        "tenant_id": "acme",
        "metric": "signup_rate",
        "magnitude": -0.15,
        "baseline": 0.2,
        "note": "pubsub test",
    }
    raw = base64.b64encode(json.dumps(payload).encode()).decode()
    res = client.post(
        "/api/internal/pubsub/signals",
        json={"message": {"data": raw}},
    )
    assert res.status_code == 200
    assert res.json()["result"]["status"] == "applied"
    assert res.json()["result"].get("room_id")


def test_pubsub_consumer_decode():
    payload = {"tenant_id": "x", "metric": "m"}
    raw = base64.b64encode(json.dumps(payload).encode()).decode()
    assert decode_push({"message": {"data": raw}}) == payload


def test_handle_signal_push_with_signal_id(engine, monkeypatch):
    monkeypatch.setenv("LOOP_AUTO_INVESTIGATE", "0")
    signals = engine.detect_signals()
    assert signals
    sig = signals[0]
    from loop.models import SignalStatus

    sig.status = SignalStatus.OPEN
    engine.store.put_signal(sig)
    engine.store.put_tenant(Tenant(id="acme", name="A", product="Y", token_hash="x", repo=""))
    out = handle_signal_push(engine, {"tenant_id": "acme", "signal_id": sig.id})
    assert out.get("status") in {"applied", "skipped", "failed"}


def _awaiting_investigation(engine):
    for inv in engine.store.list_investigations():
        if inv.state == InvestigationState.AWAITING_APPROVAL:
            return inv
    return engine.run_until_approval()


def test_deferred_verify_api_flow(client, engine, monkeypatch):
    monkeypatch.setenv("LOOP_VERIFY_DEFER", "1")
    monkeypatch.setenv("LOOP_EVAL", "1")
    inv = _awaiting_investigation(engine)
    action = engine.store.list_actions(inv.id)[0]
    res = client.post(
        f"/api/approvals/{action.id}",
        json={"decision": "approve", "approver": "oncall@test", "rationale": "ship it"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("deferred_verify") is True
    assert body.get("verify_job_id")
    job = engine.store.get_job(str(body["verify_job_id"]))
    assert job and job.kind == "verify"


def test_immediate_verify_api_flow(client, engine, monkeypatch):
    monkeypatch.setenv("LOOP_VERIFY_DEFER", "0")
    monkeypatch.setenv("LOOP_EVAL", "1")
    inv = _awaiting_investigation(engine)
    action = engine.store.list_actions(inv.id)[0]
    res = client.post(
        f"/api/approvals/{action.id}",
        json={"decision": "approve", "approver": "oncall@test", "rationale": "ship it"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("deferred_verify") is not True
    assert body.get("outcome")


def test_admin_verify_endpoint(client, monkeypatch):
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "admin-tok")
    bad = client.post("/api/admin/verify", headers={"Authorization": "Bearer wrong"})
    assert bad.status_code == 401
    ok = client.post("/api/admin/verify", headers={"Authorization": "Bearer admin-tok"})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True


def test_tenant_list_requires_admin_when_hosted(client, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("LOOP_DEV_OPEN", "0")
    denied = client.get("/api/tenants")
    assert denied.status_code == 401
    ok = client.get("/api/tenants", headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


def test_status_includes_production_fields(client):
    st = client.get("/api/status").json()
    assert "worker" in st
    assert "memory" in st
    assert "auth" in st
    assert "gcs" in st


def test_full_ambient_pipeline_to_approval(engine, monkeypatch):
    """Detect → auto-investigate → awaiting approval without human ingest."""
    from loop.signal_watch import reset_watch_state

    monkeypatch.setenv("LOOP_AUTO_INVESTIGATE", "1")
    reset_watch_state(None)
    from loop.models import SignalStatus

    signals = list(engine.detect_signals())
    assert signals, "warehouse fixtures must emit detectable signals"
    for sig in signals:
        sig.status = SignalStatus.OPEN
        engine.store.put_signal(sig)
    reset_watch_state(None)
    summary = tick_signal_watch(engine)
    assert summary is not None
    invs = engine.store.list_investigations()
    if not invs:
        applied = int(summary.get("auto_investigated") or 0)
        assert applied > 0 or summary.get("new_signal_ids"), summary
        invs = engine.store.list_investigations()
    assert invs
    inv = invs[-1]
    assert inv.state in {InvestigationState.AWAITING_APPROVAL, InvestigationState.APPROVED}
    actions = engine.store.list_actions(inv.id)
    if actions:
        assert actions[0].risk_tier in {RiskTier.HIGH, RiskTier.MEDIUM, RiskTier.LOW}


def test_verify_job_closes_loop(engine):
    inv = engine.run_until_approval()
    action = engine.store.list_actions(inv.id)[0]
    engine.approve(action.id, "oncall", "approve", "test")
    engine.execute_approved(action.id)
    job = enqueue_verify(engine.store, inv.id, delay_hours=0)
    result = process_job(engine.store, engine, job.id)
    assert result
    assert result.get("verdict")
    inv_after = engine.store.get_investigation(inv.id)
    assert inv_after.state.value.lower() in {"resolved", "partially_resolved", "not_resolved", "inconclusive"}


def test_worker_heartbeat_record():
    record_tick({"count": 2, "detected": 5})
    assert last_tick()["count"] == 2
