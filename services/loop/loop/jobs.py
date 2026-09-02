"""Durable background jobs — code fix, verify, and future workers."""

from __future__ import annotations

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


def claim_next(store: Any, kinds: list[JobKind] | None = None) -> Job | None:
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
    job = store.get_job(job_id)
    if not job:
        return None
    job.attempts += 1
    job.error = error[:500]
    job.updated_at = _iso()
    if job.attempts >= job.max_attempts:
        job.status = "dead"
    else:
        job.status = "queued"
        job.run_after = _iso(_now() + timedelta(seconds=retry_delay_s))
    store.put_job(job)
    _schedule_persist(store)
    return job


def mark_running(store: Any, job: Job) -> Job:
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


def process_job(store: Any, engine: Any, job_id: str) -> dict[str, Any] | None:
    job = store.get_job(job_id)
    if not job or job.status not in {"queued", "running"}:
        return None
    mark_running(store, job)
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
    return process_job(store, engine, job.id)


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
