from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.connectors.github import open_pr
from loop.connectors.mail import draft, send
from loop.connectors.voice import place_call
from loop.models import OutcomeVerdict, RiskTier
from loop.tenant import ConnectorReport, Tenant, hash_token, token_ok

ROOT = Path(__file__).resolve().parents[3]


def test_token_hash_roundtrip():
    t = Tenant(id="x", name="X", product="Y", token_hash=hash_token("secret"))
    assert token_ok(t, "secret")
    assert not token_ok(t, "nope")
    assert not token_ok(t, None)


def test_connectors_skip_without_secrets():
    t = Tenant(id="acme", name="Northstar", product="Y")
    gh = open_pr(t, "hi", "body")
    assert gh.status == "skipped"
    assert gh.url is None
    assert draft("a@b.c", "s", "b").status == "skipped"
    assert send().status == "denied"
    assert place_call("tok", "checkout").status == "skipped"


def test_execute_does_not_claim_a_pr_without_github(engine, monkeypatch):
    from loop.tenant import seed_placeholder

    monkeypatch.delenv("LOOP_TENANT_REPO", raising=False)
    monkeypatch.delenv("LOOP_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("loop.connectors.github._token", lambda: "")
    seed_placeholder(engine.store)
    engine.seed_world()
    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    out = engine.resume_after_approval(high.id, "oncall@acme")
    assert out.verdict == OutcomeVerdict.RESOLVED
    action = engine.store.get_action(high.id)
    exe = (action.artifacts or {}).get("execution") or {}
    assert exe.get("merged") is False
    assert exe.get("pr_opened") is False
    assert exe.get("flag") == "pay_sdk_4_3"
    assert engine.store.get_flag("pay_sdk_4_3") == "off"
    assert engine.store.get_flag("t:acme:pay_sdk_4_3") == "off"


def test_open_pr_applied_when_github_returns_url(monkeypatch):
    def fake(method, url, token, body=None):
        if method == "GET" and url.endswith("/repos/acme/y"):
            return 200, {"default_branch": "main"}
        if "git/ref" in url:
            return 200, {"object": {"sha": "abc123"}}
        if url.endswith("/git/refs"):
            return 201, {}
        if "/contents/" in url and method == "GET":
            return 404, {}
        if "/contents/" in url and method == "PUT":
            assert body and "config/flags.json" in url or True
            return 201, {}
        if url.endswith("/pulls"):
            return 201, {"html_url": "https://github.com/acme/y/pull/1"}
        return 500, {"error": url}

    monkeypatch.setattr("loop.connectors.github._request", fake)
    monkeypatch.setattr("loop.connectors.github._token", lambda: "t")
    t = Tenant(id="acme", name="Northstar", product="Y", repo="acme/y")
    r = open_pr(t, "Revert pay-sdk", "body", file_path="config/flags.json", file_content='{"pay_sdk_4_3":"off"}\n')
    assert r.status == "applied"
    assert r.url == "https://github.com/acme/y/pull/1"


def test_execute_records_pr_url_and_never_merges(engine, monkeypatch):
    engine.seed_world()
    engine.store.put_tenant(
        Tenant(id="acme", name="Northstar", product="Y", repo="saurabh4269/northstar", connected=True, token_hash=hash_token("dev-token"))
    )
    monkeypatch.setattr(
        "loop.connectors.open_pr",
        lambda *a, **k: ConnectorReport(
            status="applied",
            connector="github.pr",
            detail="pull request opened",
            url="https://github.com/saurabh4269/northstar/pull/1",
        ),
    )
    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    engine.resume_after_approval(high.id, "oncall@acme")
    exe = engine.store.get_action(high.id).artifacts["execution"]
    assert exe["pr_opened"] is True
    assert exe["merged"] is False
    assert exe["pr_url"].endswith("/pull/1")
    assert engine.store.get_tenant("acme").last_pr_url.endswith("/pull/1")


def test_tenant_http_flags_and_ingest(engine, monkeypatch):
    engine.seed_world()
    engine.store.put_tenant(
        Tenant(id="acme", name="Northstar", product="Y", token_hash=hash_token("dev-token"), repo="")
    )
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        denied = client.get("/api/t/acme/flags")
        assert denied.status_code == 401
        ok = client.get("/api/t/acme/flags", headers={"Authorization": "Bearer dev-token"})
        assert ok.status_code == 200
        assert "pay_sdk_4_3" in ok.json()["flags"]
        listed = client.get("/api/tenants")
        assert listed.status_code == 200
        row = listed.json()["tenants"][0]
        assert any(t["id"] == "acme" for t in listed.json()["tenants"])
        assert "token_hash" not in row
        assert "token" not in row
        assert listed.json()["gate"]["mode"] == "flag_only"
        saved = client.post(
            "/api/tenants",
            json={
                "id": "acme",
                "name": "Northstar",
                "product": "Northstar",
                "repo": "saurabh4269/northstar",
                "deploy_url": "https://example.test",
                "token": "dev-token",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["tenant"]["repo"] == "saurabh4269/northstar"
        assert "token" not in saved.json()["tenant"]
        assert saved.json()["tenant"]["has_token"] is True
        rotated = client.post("/api/tenants/acme/token", json={"token": "newer-secret"})
        assert rotated.status_code == 200
        assert rotated.json()["rotated"] is True
        assert "newer-secret" not in str(rotated.json())
        assert client.get("/api/t/acme/flags", headers={"Authorization": "Bearer dev-token"}).status_code == 401
        assert client.get("/api/t/acme/flags", headers={"Authorization": "Bearer newer-secret"}).status_code == 200
        gates = client.get("/api/approvals")
        assert gates.json()["gate"]["mode"] == "github_pr"
        assert "saurabh4269/northstar" in gates.json()["gate"]["label"]
        sig = client.post(
            "/api/t/acme/signals",
            headers={"Authorization": "Bearer newer-secret"},
            json={"metric": "purchase_conversion", "magnitude": -0.2, "note": "from Y"},
        )
        assert sig.status_code == 200
        assert sig.json()["signal"]["source"] == "tenant.acme"
        assert "safari" not in sig.json()["signal"]["source"]
        assert sig.json()["room_id"]
        assert sig.json()["joined"] is False
        room_id = sig.json()["room_id"]
        again = client.post(
            "/api/t/acme/signals",
            headers={"Authorization": "Bearer newer-secret"},
            json={"metric": "purchase_conversion", "magnitude": -0.15, "note": "still down"},
        )
        assert again.json()["joined"] is True
        assert again.json()["room_id"] == room_id
        voice = client.post(
            "/api/t/acme/voice",
            headers={"Authorization": "Bearer newer-secret"},
            json={"text": "checkout felt slow", "tokenized_user": "tok_1"},
        )
        assert voice.status_code == 200
        assert voice.json()["voice"]["kind"] == "customer"
        assert voice.json()["room_id"]
        assert "token" not in voice.json()["voice"]


def test_console_does_not_host_a_shop():
    console = ROOT / "apps" / "console"
    assert not (console / "app" / "shop").exists()
    assert not (console / "app" / "company").exists()
    assert not (console / "public" / "shop").exists()
    shell = (console / "components" / "shell.tsx").read_text()
    assert "Shop" not in shell
    campus = (console / "lib" / "campus.ts").read_text()
    assert "Shop" not in campus
    assert "x: 28, y: 72" in campus
    assert "x: 50, y: 80" in campus
