"""Cloud Tasks dispatch for durable background jobs."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request

from loop import gcs_state
from loop.tenant import ConnectorReport


def queue_name() -> str:
    return (os.environ.get("LOOP_TASKS_QUEUE") or "loop-jobs").strip()


def worker_url(job_id: str) -> str:
    base = (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/api/internal/worker/run/{job_id}"


def use_cloud_tasks() -> bool:
    """Cloud Tasks races with LOOP_INLINE_WORKER claim/process — use one path."""
    if os.environ.get("LOOP_TASKS_DISABLE") == "1":
        return False
    if os.environ.get("LOOP_INLINE_WORKER") == "1":
        return False
    return True


def dispatch_job(job_id: str) -> ConnectorReport:
    """Enqueue HTTP task to process one job. Falls back to in-process tick."""
    url = worker_url(job_id)
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not url or not project or not use_cloud_tasks():
        detail = "inline worker — no Cloud Tasks"
        if os.environ.get("LOOP_INLINE_WORKER") == "1":
            detail = "inline worker active — Cloud Tasks skipped"
        return ConnectorReport(
            status="skipped",
            connector="cloud_tasks",
            detail=detail,
        )
    token = gcs_state.metadata_access_token()
    if not token:
        return ConnectorReport(status="skipped", connector="cloud_tasks", detail="no metadata token")
    location = (os.environ.get("GOOGLE_CLOUD_REGION") or "us-central1").strip()
    parent = f"projects/{project}/locations/{location}/queues/{queue_name()}"
    admin = (os.environ.get("LOOP_ADMIN_TOKEN") or "").strip()
    base = (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")
    body = json.dumps(
        {
            "httpRequest": {
                "httpMethod": "POST",
                "url": url,
                "headers": {
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {admin}"} if admin else {}),
                    **({"X-Loop-Worker": admin} if admin else {}),
                },
                "oidcToken": {
                    "serviceAccountEmail": (
                        os.environ.get("LOOP_TASKS_SA")
                        or f"loop-runtime@{project}.iam.gserviceaccount.com"
                    ),
                    "audience": base or url,
                },
            }
        }
    ).encode()
    api = f"https://cloudtasks.googleapis.com/v2/{parent}/tasks"
    req = urllib.request.Request(
        api,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode() or "{}")
        return ConnectorReport(
            status="applied",
            connector="cloud_tasks",
            detail=f"task queued for {job_id}",
            url=raw.get("name"),
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:240]
        return ConnectorReport(
            status="skipped",
            connector="cloud_tasks",
            detail=f"tasks {exc.code}: {detail}",
        )
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return ConnectorReport(status="skipped", connector="cloud_tasks", detail=str(exc)[:200])


def kick_job(job_id: str) -> None:
    """Cloud Tasks when available; otherwise background thread with retry bookkeeping."""

    def worker() -> None:
        from loop.engine import default_engine
        from loop.jobs import fail, process_job

        eng = default_engine()
        try:
            process_job(eng.store, eng, job_id)
        except Exception as exc:
            fail(eng.store, job_id, str(exc))

    report = dispatch_job(job_id)
    if report.status == "applied":
        return

    threading.Thread(target=worker, name=f"job-{job_id[:8]}", daemon=True).start()
