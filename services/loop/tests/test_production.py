"""Auth, jobs, state persist, code worker."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.auth import admin_required, require_admin
from loop.jobs import Job, enqueue, fail, complete, process_one
from loop.state_persist import hydrate_db, persist_db, schedule_snapshot
from loop.code_worker import apply_patches, detect_test_command, run_tests


def test_admin_open_locally_without_token():
    os.environ.pop("K_SERVICE", None)
    os.environ.pop("LOOP_ADMIN_TOKEN", None)
    assert admin_required() is False
    assert require_admin(None, actor="dev") == "dev"


def test_admin_required_on_hosted(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    assert admin_required() is True
    with pytest.raises(HTTPException):
        require_admin("wrong", actor="x")


def test_jobs_enqueue_and_complete(engine):
    job = enqueue(engine.store, "code_fix", {"action_id": "act_x"})
    assert job.status == "queued"
    got = engine.store.get_job(job.id)
    assert got and got.payload["action_id"] == "act_x"
    complete(engine.store, job.id, {"status": "applied"})
    done = engine.store.get_job(job.id)
    assert done.status == "succeeded"


def test_jobs_fail_and_retry(engine):
    job = enqueue(engine.store, "code_fix", {"x": 1}, max_attempts=2)
    fail(engine.store, job.id, "boom")
    j1 = engine.store.get_job(job.id)
    assert j1.status == "queued"
    assert j1.attempts == 1
    fail(engine.store, job.id, "boom again")
    j2 = engine.store.get_job(job.id)
    assert j2.status == "dead"


def test_state_persist_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "loop.db"
    from loop.store import Store

    store = Store(db)
    store.set_flag("pay_sdk_4_3", "off", "k1")
    uri = f"gs://test-bucket/{tmp_path.name}/loop_state.db"
    monkeypatch.setattr("loop.state_persist.state_gcs_uri", lambda: uri)
    uploaded: dict[str, bytes] = {}

    def fake_write(u, payload, **kw):
        uploaded["blob"] = payload
        return True

    def fake_read(u):
        return uploaded.get("blob", b"")

    monkeypatch.setattr("loop.gcs_state.write_bytes", fake_write)
    monkeypatch.setattr("loop.gcs_state.read_bytes", fake_read)
    assert persist_db(db) is True
    db.unlink()
    assert hydrate_db(db) is True
    store2 = Store(db)
    assert store2.get_flag("pay_sdk_4_3") == "off"


def test_code_worker_apply_and_test_skip(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"test":"echo ok"}}')
    touched = apply_patches(repo, {"src/a.ts": "export const x = 1;\n"})
    assert "src/a.ts" in touched
    ok, msg = run_tests(repo)
    assert ok or "skipped" in msg or "npm" in msg


def test_worker_tick_requires_admin_on_hosted(engine, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "tok")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        denied = client.post("/api/internal/worker/tick")
        assert denied.status_code == 401
        ok = client.post("/api/internal/worker/tick", headers={"Authorization": "Bearer tok"})
        assert ok.status_code == 200
        assert "count" in ok.json()


def test_worker_run_processes_job(engine, monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "tok")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    job = enqueue(engine.store, "verify", {"probe": True})
    monkeypatch.setattr(
        "loop.jobs.process_job",
        lambda store, eng, jid: {"job_id": jid, "status": "succeeded"},
    )
    with TestClient(api_mod.app) as client:
        denied = client.post(f"/api/internal/worker/run/{job.id}")
        assert denied.status_code == 401
        ok = client.post(
            f"/api/internal/worker/run/{job.id}",
            headers={"Authorization": "Bearer tok"},
        )
        assert ok.status_code == 200
        assert ok.json()["result"]["job_id"] == job.id


def test_approval_status_public(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    action = next(a for a in engine.store.pending_approvals())
    job = enqueue(engine.store, "code_fix", {"action_id": action.id})
    execution = {"job_id": job.id, "code_fix": "queued"}
    action.artifacts["execution"] = execution
    action.status = "executed"
    engine.store.put_action(action)
    with TestClient(api_mod.app) as client:
        res = client.get(f"/api/approvals/{action.id}/status")
        assert res.status_code == 200
        body = res.json()
        assert body["job"]["id"] == job.id
        assert body["execution"]["job_id"] == job.id
