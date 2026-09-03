"""Job dispatcher — inline worker, Cloud Tasks fallback, and zombie reclaim."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from loop.jobs import (
    _iso,
    begin_attempt,
    enqueue,
    job_is_stale,
    process_job,
    process_one,
    reclaim_stale_running_jobs,
)
from loop.tasks import dispatch_job, kick_job, use_cloud_tasks


def test_inline_worker_mode_disables_cloud_tasks(monkeypatch):
    monkeypatch.setenv("LOOP_INLINE_WORKER", "1")
    monkeypatch.delenv("LOOP_TASKS_DISABLE", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://example.test")
    assert use_cloud_tasks() is False
    report = dispatch_job("job_test123")
    assert report.status == "skipped"
    assert "inline worker" in report.detail.lower()


def test_cloud_tasks_used_without_inline_worker(monkeypatch):
    monkeypatch.delenv("LOOP_INLINE_WORKER", raising=False)
    monkeypatch.delenv("LOOP_TASKS_DISABLE", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://example.test")
    assert use_cloud_tasks() is True


def test_kick_job_runs_code_fix_body_when_inline_worker(monkeypatch, engine):
    monkeypatch.setenv("LOOP_INLINE_WORKER", "1")
    ran: dict[str, bool] = {}

    def fake_process_job(store, eng, job_id):
        ran["job_id"] = job_id
        job = store.get_job(job_id)
        begin_attempt(store, job)
        return {"job_id": job_id, "status": "skipped", "detail": "test"}

    monkeypatch.setattr("loop.tasks.dispatch_job", lambda _jid: type("R", (), {"status": "skipped"})())
    monkeypatch.setattr("loop.jobs.process_job", fake_process_job)

    job = enqueue(engine.store, "code_fix", {"action_id": "act_x"})
    kick_job(job.id)
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if ran.get("job_id") == job.id:
            break
        time.sleep(0.05)
    assert ran.get("job_id") == job.id


def test_zombie_running_with_zero_attempts_is_reclaimed(engine, monkeypatch):
    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "1")
    job = enqueue(engine.store, "code_fix", {"action_id": "act_z"})
    stale_at = _iso(datetime.now(timezone.utc) - timedelta(seconds=5))
    job.status = "running"
    job.attempts = 0
    job.updated_at = stale_at
    engine.store.put_job(job)
    job = engine.store.get_job(job.id)

    assert job_is_stale(job)
    reclaimed = reclaim_stale_running_jobs(engine.store)
    assert job.id in reclaimed
    got = engine.store.get_job(job.id)
    assert got.status == "queued"


def test_process_one_reclaims_and_runs_stale_code_fix(engine, monkeypatch):
    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "1")
    calls: list[str] = []

    def fake_run(eng, job):
        calls.append(job.id)
        return {"status": "skipped", "detail": "honest skip"}

    monkeypatch.setattr("loop.code_fix.run_code_fix_job", fake_run)

    job = enqueue(engine.store, "code_fix", {"tenant_id": "acme", "action_id": "act_a"})
    job.status = "running"
    job.attempts = 0
    job.updated_at = _iso(datetime.now(timezone.utc) - timedelta(seconds=5))
    engine.store.put_job(job)

    result = process_one(engine.store, engine)
    assert result
    assert result["status"] == "skipped"
    assert calls == [job.id]
    done = engine.store.get_job(job.id)
    assert done.status == "succeeded"
    assert done.attempts >= 1


def test_process_one_reclaims_stale_code_fix_after_first_attempt(engine, monkeypatch):
    """Regression: reclaimed jobs with attempts>=1 must run, not zombie-loop."""
    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "1")
    calls: list[str] = []

    def fake_run(eng, job):
        calls.append(job.id)
        return {"status": "skipped", "detail": "honest skip"}

    monkeypatch.setattr("loop.code_fix.run_code_fix_job", fake_run)

    job = enqueue(engine.store, "code_fix", {"tenant_id": "acme", "action_id": "act_retry"})
    job.status = "running"
    job.attempts = 1
    job.error = "worker died mid-run"
    job.updated_at = _iso(datetime.now(timezone.utc) - timedelta(seconds=5))
    engine.store.put_job(job)

    result = process_one(engine.store, engine)
    assert result
    assert result["status"] == "skipped"
    assert calls == [job.id]
    done = engine.store.get_job(job.id)
    assert done.status == "succeeded"
    assert done.attempts == 2
    assert "reclaimed stale running job" not in done.error


def test_process_one_finishes_flag_pr_job_with_honest_code_fix(engine, monkeypatch):
    """When flag PR already opened, reclaimed code_fix must complete execution.code_fix."""
    from tests.test_code_fix import _action_bundle

    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "1")
    from loop.code_fix import enqueue_code_fix_job
    from loop.tenant import ConnectorReport

    tenant, inv, action = _action_bundle(engine)
    action.artifacts["execution"] = {
        "pr_opened": True,
        "pr_url": "https://github.com/org/shop/pull/7",
    }
    engine.store.put_action(action)

    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: ConnectorReport(
            status="skipped",
            connector="code_fix",
            detail="flag PR already open — code PR deferred",
        ),
    )

    job_id = enqueue_code_fix_job(
        engine,
        action_id=action.id,
        tenant=tenant,
        inv=inv,
        brief={"issue": "checkout timeout", "likely_files": ["src/checkout.ts"]},
        flag_patch={"checkout_v2": "off"},
        pr_title="Fix checkout",
        pr_body="body",
        flag_pr_opened=True,
    )
    assert job_id
    job = engine.store.get_job(job_id)
    job.status = "running"
    job.attempts = 1
    job.updated_at = _iso(datetime.now(timezone.utc) - timedelta(seconds=5))
    engine.store.put_job(job)

    result = process_one(engine.store, engine)
    assert result
    assert result["status"] == "skipped"
    done = engine.store.get_job(job_id)
    assert done.status == "succeeded"
    exe = engine.store.get_action(action.id).artifacts["execution"]
    assert exe["pr_opened"] is True
    assert exe["pr_url"].endswith("/pull/7")
    assert exe["code_fix"]["status"] == "skipped"


def test_process_job_increments_attempts_before_body(engine, monkeypatch):
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix_job",
        lambda eng, job: {"status": "skipped", "detail": "no tenant"},
    )
    job = enqueue(engine.store, "code_fix", {"action_id": "act_b"})
    process_job(engine.store, engine, job.id)
    got = engine.store.get_job(job.id)
    assert got.status == "succeeded"
    assert got.attempts == 1


def test_duplicate_running_worker_skips_active_job(engine, monkeypatch):
    job = enqueue(engine.store, "code_fix", {"action_id": "act_dup"})
    begin_attempt(engine.store, job)
    second = process_job(engine.store, engine, job.id)
    assert second is None


def test_claimed_running_zero_attempts_eventually_executes(engine, monkeypatch):
    """Simulate claim_job reservation without begin_attempt — must not zombie."""
    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "60")
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix_job",
        lambda eng, job: {"status": "skipped", "detail": "test"},
    )
    job = enqueue(engine.store, "code_fix", {"action_id": "act_claim"})
    job.status = "running"
    job.attempts = 0
    job.updated_at = _iso()
    engine.store.put_job(job)

    result = process_job(engine.store, engine, job.id)
    assert result
    got = engine.store.get_job(job.id)
    assert got.status == "succeeded"
    assert got.attempts == 1


def test_atomic_claim_excludes_fresh_running(engine):
    job = enqueue(engine.store, "verify", {"investigation_id": "inv_x"})
    begin_attempt(engine.store, job)
    claimed = engine.store.claim_job(["verify"])
    assert claimed is None


def test_atomic_claim_allows_stale_running(engine, monkeypatch):
    monkeypatch.setenv("LOOP_JOB_STALE_SECONDS", "1")
    job = enqueue(engine.store, "verify", {"investigation_id": "inv_y"})
    job.status = "running"
    job.attempts = 1
    job.updated_at = _iso(datetime.now(timezone.utc) - timedelta(seconds=5))
    engine.store.put_job(job)

    claimed = engine.store.claim_job(["verify"])
    assert claimed is not None
    assert claimed.id == job.id


def test_process_job_respects_run_after(engine, monkeypatch):
    monkeypatch.setattr(
        "loop.jobs.run_verify_job",
        lambda eng, job: {"status": "succeeded", "verdict": "RESOLVED"},
    )
    job = enqueue(engine.store, "verify", {"investigation_id": "inv_future"})
    job.run_after = _iso(datetime.now(timezone.utc) + timedelta(hours=1))
    engine.store.put_job(job)

    assert process_job(engine.store, engine, job.id) is None
    still = engine.store.get_job(job.id)
    assert still.status == "queued"
    assert still.attempts == 0
