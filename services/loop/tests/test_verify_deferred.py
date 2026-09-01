"""Deferred verify job and atomic job claims."""

from __future__ import annotations

import threading

from loop.jobs import enqueue_verify, process_job


def test_deferred_verify_job(engine, monkeypatch):
    monkeypatch.setenv("LOOP_VERIFY_DEFER", "1")
    inv = engine.run_until_approval()
    action = engine.store.list_actions(inv.id)[0]
    out = engine.resume_after_approval(action.id, "oncall@test")
    assert out.get("deferred") is True
    job_id = out.get("verify_job_id")
    assert job_id
    job = engine.store.get_job(str(job_id))
    assert job.kind == "verify"


def test_verify_job_runs(engine):
    inv = engine.run_until_approval()
    action = engine.store.list_actions(inv.id)[0]
    engine.approve(action.id, "oncall", "approve", "test")
    engine.execute_approved(action.id)
    job = enqueue_verify(engine.store, inv.id, delay_hours=0)
    result = process_job(engine.store, engine, job.id)
    assert result
    assert result.get("verdict") in {"RESOLVED", "PARTIALLY_RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE"}


def test_atomic_job_claim(engine):
    enqueue_verify(engine.store, "inv_test_a", delay_hours=0)
    enqueue_verify(engine.store, "inv_test_b", delay_hours=0)

    results: list = []

    def claim():
        j = engine.store.claim_job(["verify"])
        results.append(j.id if j else None)

    t1 = threading.Thread(target=claim)
    t2 = threading.Thread(target=claim)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    claimed = [r for r in results if r]
    assert len(claimed) >= 1
    assert len(set(claimed)) == len(claimed)
