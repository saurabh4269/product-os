"""Durable background jobs — code fix, verify, and future workers."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "succeeded", "failed", "dead"]
JobKind = Literal["code_fix", "verify"]


class Job(BaseModel):
    id: str
    kind: JobKind
    status: JobStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 3
    error: str = ""
    created_at: str
    updated_at: str
    run_after: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _id(prefix: str = "job") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def stale_job_seconds() -> int:
    raw = (os.environ.get("LOOP_JOB_STALE_SECONDS") or "120").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 120


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def job_age_seconds(job: Job, *, now: datetime | str | None = None) -> float:
    stamp = _parse_iso(job.updated_at) or _parse_iso(job.created_at)
    if not stamp:
        return 0.0
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    if now is None:
        ref = _now()
    elif isinstance(now, str):
        ref = _parse_iso(now) or _now()
    else:
        ref = now
    return max(0.0, (ref - stamp).total_seconds())


def job_is_stale(job: Job, *, now: datetime | None = None) -> bool:
    if job.status != "running":
        return False
    return job_age_seconds(job, now=now) >= stale_job_seconds()


def reclaim_stale_running_jobs(store: Any) -> list[str]:
    """Return queued zombies that were stuck in running without making progress."""
    now = _now()
    reclaimed: list[str] = []
    for job in store.list_jobs(status="running", limit=200):
        if not job_is_stale(job, now=now):
            continue
        job.status = "queued"
        note = "reclaimed stale running job"
        job.error = f"{job.error[:420]}; {note}".strip("; ") if job.error else note
        job.updated_at = _iso(now)
        store.put_job(job)
        reclaimed.append(job.id)
    if reclaimed:
        _schedule_persist(store)
    return reclaimed


def enqueue(store: Any, kind: JobKind, payload: dict[str, Any], *, max_attempts: int = 3, run_after: datetime | None = None) -> Job:
    now = _iso()
    job = Job(
        id=_id(),
        kind=kind,
        status="queued",
        payload=payload,
        attempts=0,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
        run_after=_iso(run_after) if run_after else now,
    )
    store.put_job(job)
    _schedule_persist(store)
    dispatch(job, store)
    return job


def enqueue_verify(store: Any, investigation_id: str, *, delay_hours: int = 24) -> Job:
    run_after = _now() if delay_hours <= 0 else _now() + timedelta(hours=delay_hours)
    return enqueue(
        store,
        "verify",
        {"investigation_id": investigation_id},
        run_after=run_after,
    )


_SWEEP_DEAD_INTERVAL_S = 60.0
_last_dead_sweep_mono = 0.0


def sweep_dead_jobs(store: Any, *, force: bool = False, limit: int = 25) -> list[str]:
    """Clear zombie dead jobs and queue verify when flags PR already shipped."""
    global _last_dead_sweep_mono
    now_mono = time.monotonic()
    if not force and now_mono - _last_dead_sweep_mono < _SWEEP_DEAD_INTERVAL_S:
        return []
    _last_dead_sweep_mono = now_mono
    swept: list[str] = []
    for job in store.list_jobs(status="dead", limit=limit):
        inv_id = str(job.payload.get("investigation_id") or "")
        if job.kind == "code_fix" and (
            job.payload.get("flag_pr_opened") or job.result.get("flag_pr_opened")
        ):
            job.status = "succeeded"
            job.result = {
                **(job.result or {}),
                "status": "skipped",
                "detail": "flags.json PR path — code_fix not required on lean worker",
            }
            job.error = ""
            job.updated_at = _iso()
            store.put_job(job)
            swept.append(job.id)
            if inv_id and not _investigation_has_verify_job(store, inv_id):
                enqueue_verify(store, inv_id, delay_hours=0)
            continue
        if job.kind == "verify" and inv_id:
            # One retry for verify jobs that died before posting room outcome.
            job.status = "queued"
            job.attempts = 0
            job.max_attempts = max(job.max_attempts, 2)
            job.run_after = _iso()
            job.error = ""
            job.updated_at = _iso()
            store.put_job(job)
            swept.append(job.id)
    if swept:
        _schedule_persist(store)
    return swept


def _investigation_has_verify_job(store: Any, inv_id: str) -> bool:
    for job in store.list_jobs(kind="verify", limit=200):
        if str(job.payload.get("investigation_id") or "") == inv_id and job.status in {
            "queued",
            "running",
            "succeeded",
        }:
            return True
    return False


def claim_next(store: Any, kinds: list[JobKind] | None = None) -> Job | None:
    reclaim_stale_running_jobs(store)
    sweep_dead_jobs(store)
    return store.claim_job(kinds or ["code_fix", "verify"])


def complete(store: Any, job_id: str, result: dict[str, Any]) -> Job | None:
    job = store.get_job(job_id)
    if not job:
        return None
    job.status = "succeeded"
    job.result = result
    job.error = ""
    job.updated_at = _iso()
    store.put_job(job)
    _schedule_persist(store)
    return job


def fail(store: Any, job_id: str, error: str, *, retry_delay_s: int = 30) -> Job | None:
    from loop.code_worker import NON_RETRYABLE_TEST_ERRORS

    job = store.get_job(job_id)
    if not job:
        return None
    job.error = error[:500]
    job.updated_at = _iso()
    permanent = any(marker in error for marker in NON_RETRYABLE_TEST_ERRORS)
    if permanent or job.attempts >= job.max_attempts:
        job.status = "dead"
    else:
        job.status = "queued"
        job.run_after = _iso(_now() + timedelta(seconds=retry_delay_s))
    store.put_job(job)
    _schedule_persist(store)
    return job


def begin_attempt(store: Any, job: Job) -> Job:
    """Mark execution start — attempts must advance before work runs."""
    job.attempts += 1
    job.status = "running"
    job.updated_at = _iso()
    store.put_job(job)
    return job


def enqueue_code_fix(
    store: Any,
    *,
    action_id: str,
    investigation_id: str,
    tenant_id: str,
    brief: dict[str, Any],
    flag_patch: dict[str, str] | None,
    pr_title: str,
    pr_body: str,
    flag_pr_opened: bool = False,
) -> Job:
    return enqueue(
        store,
        "code_fix",
        {
            "action_id": action_id,
            "investigation_id": investigation_id,
            "tenant_id": tenant_id,
            "brief": brief,
            "flag_patch": flag_patch or {},
            "pr_title": pr_title,
            "pr_body": pr_body,
            "flag_pr_opened": flag_pr_opened,
        },
    )


def run_verify_job(engine: Any, job: Job) -> dict[str, Any]:
    inv_id = str(job.payload.get("investigation_id") or "")
    if not inv_id:
        return {"status": "failed", "detail": "missing investigation_id"}
    outcome = engine.verify(inv_id)
    verdict = outcome.verdict.value
    # Job ran; investigation outcome is separate from queue status.
    status = "inconclusive" if verdict == "INCONCLUSIVE" else "succeeded"
    return {
        "status": status,
        "investigation_id": inv_id,
        "verdict": verdict,
    }


def process_job(
    store: Any,
    engine: Any,
    job_id: str,
    *,
    from_claim: bool = False,
) -> dict[str, Any] | None:
    job = store.get_job(job_id)
    if not job:
        return None
    if job.status not in {"queued", "running"}:
        return None
    if job.run_after:
        run_after = _parse_iso(job.run_after)
        if run_after and run_after > _now():
            return None
    if job.status == "running":
        if job_is_stale(job):
            job.status = "queued"
            job.updated_at = _iso()
            store.put_job(job)
            begin_attempt(store, job)
        elif from_claim:
            # claim_job already incremented attempts and set running.
            pass
        elif job.attempts > 0:
            return None
        else:
            # Legacy reservation: running without begin_attempt (attempts still 0).
            begin_attempt(store, job)
    else:
        begin_attempt(store, job)
    try:
        if job.kind == "code_fix":
            from loop.code_fix import run_code_fix_job

            result = run_code_fix_job(engine, job)
            if result.get("status") in {"applied", "succeeded", "skipped"}:
                delay = int(__import__("os").environ.get("LOOP_VERIFY_DELAY_HOURS", "24"))
                verify_job = enqueue_verify(store, str(job.payload.get("investigation_id") or ""), delay_hours=delay)
                result["verify_job_id"] = verify_job.id
        elif job.kind == "verify":
            result = run_verify_job(engine, job)
        else:
            result = {"status": "skipped", "detail": f"unknown kind {job.kind}"}
        if result.get("status") in {"applied", "succeeded", "skipped", "inconclusive"}:
            complete(store, job.id, result)
        else:
            fail(store, job.id, str(result.get("detail") or result.get("error") or "job failed"))
        return {"job_id": job.id, **result}
    except Exception as exc:
        fail(store, job.id, str(exc))
        return {"job_id": job.id, "status": "failed", "error": str(exc)}


def process_one(store: Any, engine: Any) -> dict[str, Any] | None:
    job = claim_next(store)
    if not job:
        return None
    try:
        return process_job(store, engine, job.id, from_claim=True)
    except Exception as exc:
        fail(store, job.id, str(exc))
        return {"job_id": job.id, "status": "failed", "error": str(exc)}


def dispatch(job: Job, store: Any) -> None:
    from loop.tasks import kick_job

    kick_job(job.id)


def _schedule_persist(store: Any) -> None:
    try:
        from loop.state_persist import schedule_snapshot

        ok = schedule_snapshot(store.path)
        if ok is False:
            from loop.audit import record

            record(
                store,
                actor="jobs",
                action="persist.failed",
                resource="state_persist",
                detail={"path": str(store.path)},
            )
    except Exception as exc:
        try:
            from loop.audit import record

            record(
                store,
                actor="jobs",
                action="persist.error",
                resource="state_persist",
                detail={"error": str(exc)[:200]},
            )
        except Exception:
            pass
