"""GCP Cloud Run onboard + verify (production wire path)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.onboard import onboard_tenant, verify_tenant
from loop.tenant import Tenant, hash_token, token_ok


def test_onboard_mints_token_without_cloudrun(engine, monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    out = onboard_tenant(
        engine.store,
        cloud_run_service="",
        repo="acme/product-y",
        deploy_url="https://y.example",
        tenant_id="acme",
        name="Acme",
        product="Product Y",
        wire=True,
    )
    assert out["tenant_id"] == "acme"
    assert out["token"]
    assert out["token_once"] is True
    t = engine.store.get_tenant("acme")
    assert t is not None
    assert t.repo == "acme/product-y"
    assert t.deploy_url == "https://y.example"
    assert token_ok(t, out["token"])
    assert "token_hash" not in out["tenant"]
    assert out["wire"]["status"] == "skipped"


def test_onboard_wires_cloudrun_env(engine, monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")

    current = {
        "name": "projects/demo-proj/locations/us-central1/services/cove",
        "uri": "https://cove.example",
        "template": {
            "containers": [
                {
                    "name": "app",
                    "image": "gcr.io/demo/cove",
                    "env": [{"name": "NODE_ENV", "value": "production"}],
                }
            ]
        },
    }
    calls: list[tuple[str, str]] = []

    def fake_run(method, path, body=None):
        calls.append((method, path.split("?")[0]))
        if method == "GET":
            return 200, current
        if method == "PATCH":
            assert body is not None
            env = body["template"]["containers"][0]["env"]
            names = {e["name"]: e.get("value") for e in env}
            assert names["LOOP_OS_URL"] == "https://loop.example"
            assert names["LOOP_TENANT_ID"] == "cove"
            assert names["LOOP_TENANT_TOKEN"]
            assert names["NODE_ENV"] == "production"
            return 200, {**current, "uri": "https://cove.example"}
        return 500, {"error": "unexpected"}

    monkeypatch.setattr("loop.onboard._run_api", fake_run)

    out = onboard_tenant(
        engine.store,
        cloud_run_service="cove",
        repo="acme/cove",
        tenant_id="cove",
        name="Cove",
        product="Cove",
        wire=True,
    )
    assert out["status"] == "applied"
    assert out["wire"]["status"] == "applied"
    assert any(m == "PATCH" for m, _ in calls)
    t = engine.store.get_tenant("cove")
    assert t is not None
    assert token_ok(t, out["token"])
    assert t.deploy_url == "https://cove.example"


def test_wire_reuses_matching_env(engine, monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
    token = "already-set-token-value-32chars!!"

    current = {
        "name": "projects/demo-proj/locations/us-central1/services/cove",
        "uri": "https://cove.example",
        "template": {
            "containers": [
                {
                    "env": [
                        {"name": "LOOP_OS_URL", "value": "https://loop.example"},
                        {"name": "LOOP_TENANT_ID", "value": "cove"},
                        {"name": "LOOP_TENANT_TOKEN", "value": token},
                    ]
                }
            ]
        },
    }

    def fake_run(method, path, body=None):
        if method == "GET":
            return 200, current
        return 500, {"error": "should not patch"}

    monkeypatch.setattr("loop.onboard._run_api", fake_run)
    # Force minted token to match so reuse path can trigger after mint — reuse checks
    # against newly minted token, so first wire always PATCHes. Test reuse via wire_cloud_run_env.
    from loop.onboard import wire_cloud_run_env

    report = wire_cloud_run_env(
        "cove",
        env_updates={
            "LOOP_OS_URL": "https://loop.example",
            "LOOP_TENANT_ID": "cove",
            "LOOP_TENANT_TOKEN": token,
        },
    )
    assert report["status"] == "reused"


def test_verify_ingest_and_checklist(engine, monkeypatch):
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Acme",
            product="Y",
            repo="acme/y",
            deploy_url="https://y.example",
            token_hash=hash_token("secret"),
            connected=True,
        )
    )
    monkeypatch.setenv("LOOP_GITHUB_TOKEN", "gh")

    class FakeResp:
        status = 200

        def read(self):
            return b'{"flags":{}}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResp())
    out = verify_tenant(engine, "acme")
    assert out["ready"] is True
    ids = {c["id"]: c["ok"] for c in out["checks"]}
    assert ids["tenant_record"]
    assert ids["token"]
    assert ids["ingest"]
    assert ids["flags_product"]
    assert ids["github"]
    assert out["room_id"]


def test_onboard_http_endpoints(engine, monkeypatch):
    monkeypatch.setenv("LOOP_PUBLIC_URL", "https://loop.example")
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)

    def fake_list(**kwargs):
        return {
            "status": "applied",
            "project": "p",
            "region": "us-central1",
            "services": [{"id": "cove", "name": "cove", "url": "https://cove.example", "repo_hint": ""}],
            "detail": "1 services",
        }

    monkeypatch.setattr("loop.onboard.list_cloud_run_services", fake_list)
    monkeypatch.setattr(
        "loop.onboard.onboard_tenant",
        lambda store, **kw: {
            "status": "applied",
            "tenant_id": kw.get("tenant_id") or "cove",
            "tenant": {"id": "cove", "name": "Cove", "product": "Cove", "repo": kw["repo"], "has_token": True},
            "token": "once-token",
            "token_once": True,
            "wire": {"status": "applied", "detail": "ok"},
        },
    )

    with TestClient(api_mod.app) as client:
        listed = client.get("/api/onboard/services")
        assert listed.status_code == 200
        assert listed.json()["services"][0]["id"] == "cove"

        engine.store.put_tenant(
            Tenant(id="cove", name="Cove", product="Cove", repo="a/b", token_hash=hash_token("x"), connected=True)
        )
        monkeypatch.setattr(
            "loop.onboard.verify_tenant",
            lambda eng, tid: {
                "status": "applied",
                "tenant_id": tid,
                "checks": [{"id": "ingest", "ok": True, "label": "ok"}],
                "ok": 1,
                "total": 1,
                "ready": True,
                "room_id": "room_1",
            },
        )
        wired = client.post(
            "/api/tenants/onboard",
            json={"cloud_run_service": "cove", "repo": "acme/cove", "tenant_id": "cove"},
        )
        assert wired.status_code == 200
        assert wired.json()["token"] == "once-token"

        verified = client.post("/api/tenants/cove/verify")
        assert verified.status_code == 200
        assert verified.json()["ready"] is True
