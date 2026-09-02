"""Pass 1 — production control-plane auth (LOOP_EVAL=0 / hosted)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.auth import cors_allowlist
from loop.tenant import Tenant, hash_token

PROTECTED_GETS = (
    "/api/rooms",
    "/api/approvals",
    "/api/pipeline",
    "/api/traces",
    "/api/registry",
    "/api/office",
    "/api/signals",
    "/api/memory",
    "/api/oauth/google",
)

PROTECTED_POSTS = (
    ("/api/tenants", {"id": "x", "name": "X", "product": "Y"}),
    ("/api/memory", {"type": "engineering", "title": "t", "body": "b"}),
    ("/api/agent_callback", {"room_id": "room_x", "agent_id": "a", "message": "hi"}),
    ("/api/investigate", {"kind": "anomaly", "metric": "conversion"}),
    ("/api/improve", {"kind": "signal", "metric": "conversion"}),
    ("/api/research", {"kind": "checkout", "user_id": "u1"}),
)


@pytest.fixture()
def prod_client(engine, monkeypatch):
    monkeypatch.setenv("LOOP_EVAL", "0")
    monkeypatch.setenv("LOOP_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://productos.heisenbug.in")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        yield client


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_requires_admin(prod_client, path):
    denied = prod_client.get(path)
    assert denied.status_code == 401
    ok = prod_client.get(path, headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


@pytest.mark.parametrize("path,payload", PROTECTED_POSTS)
def test_protected_post_requires_admin_before_body(prod_client, path, payload):
    denied = prod_client.post(path, json=payload)
    assert denied.status_code == 401
    ok = prod_client.post(path, headers={"Authorization": "Bearer secret"}, json=payload)
    assert ok.status_code != 401


def test_coordinate_requires_admin(prod_client):
    denied = prod_client.post("/api/coordinate", json={"title": "sync"})
    assert denied.status_code == 401


def test_post_tenants_401_before_invalid_body(prod_client):
    """Auth dependency must run before Pydantic body validation."""
    denied = prod_client.post("/api/tenants", json={"name": "missing id"})
    assert denied.status_code == 401


def test_post_memory_401_unauth_no_write(prod_client, engine):
    before = len(engine.store.list_memory())
    denied = prod_client.post(
        "/api/memory",
        json={"type": "engineering", "title": "secret", "body": "nope"},
    )
    assert denied.status_code == 401
    assert len(engine.store.list_memory()) == before


def test_room_messages_require_admin(prod_client, engine):
    engine.seed_world()
    room_id = engine.store.list_rooms()[0].id
    denied = prod_client.post(f"/api/rooms/{room_id}/messages", json={"text": "hello"})
    assert denied.status_code == 401


def test_room_detail_requires_admin(prod_client, engine):
    engine.seed_world()
    room_id = engine.store.list_rooms()[0].id
    assert prod_client.get(f"/api/rooms/{room_id}").status_code == 401
    assert (
        prod_client.get(f"/api/rooms/{room_id}", headers={"Authorization": "Bearer secret"}).status_code
        == 200
    )


def test_cors_never_wildcard_on_hosted(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CONSOLE_ORIGIN", "*")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://productos.heisenbug.in")
    origins, credentials = cors_allowlist()
    assert "*" not in origins
    assert "https://productos.heisenbug.in" in origins
    assert credentials is True


def test_cors_allowlist_includes_console_origin(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "loop")
    monkeypatch.setenv("LOOP_CONSOLE_ORIGIN", "https://productos.heisenbug.in")
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://productos.heisenbug.in")
    origins, credentials = cors_allowlist()
    assert "https://productos.heisenbug.in" in origins
    assert credentials is True


def test_connect_hides_duplicate_tenant_repo(prod_client, engine):
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Cove", repo="saurabh4269/cove", token_hash=hash_token("a"))
    )
    engine.store.put_tenant(
        Tenant(id="cove", name="Cove", product="Cove", repo="saurabh4269/cove", token_hash=hash_token("b"))
    )
    listed = prod_client.get("/api/tenants", headers={"Authorization": "Bearer secret"}).json()["tenants"]
    ids = {t["id"] for t in listed}
    assert "acme" in ids
    assert "cove" not in ids


def test_tenant_scoped_routes_still_use_tenant_token(prod_client, engine):
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Y", repo="r", token_hash=hash_token("tenant-secret"))
    )
    assert prod_client.get("/api/t/acme/flags").status_code == 401
    ok = prod_client.get("/api/t/acme/flags", headers={"Authorization": "Bearer tenant-secret"})
    assert ok.status_code == 200
