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
    pr_url = "https://github.com/saurabh4269/cove/pull/1"
    monkeypatch.setattr(
        "loop.code_fix.run_code_fix",
        lambda **k: ConnectorReport(
            status="applied",
            connector="github.pr",
            detail="pull request opened (3 files)",
            url=pr_url,
        ),
    )

    def sync_enqueue(engine, **kwargs):
        from loop.code_fix import run_code_fix_job
        from loop.jobs import enqueue_code_fix

        job = enqueue_code_fix(
            engine.store,
            action_id=kwargs["action_id"],
            investigation_id=kwargs["inv"].id,
            tenant_id=kwargs["tenant"].id,
            brief=kwargs["brief"],
            flag_patch=kwargs["flag_patch"],
            pr_title=kwargs["pr_title"],
            pr_body=kwargs["pr_body"],
        )
        run_code_fix_job(engine, job)

    engine.seed_world()
    engine.store.put_tenant(
        Tenant(id="acme", name="Cove", product="Y", repo="saurabh4269/cove", connected=True, token_hash=hash_token("dev-token"))
    )
    monkeypatch.setattr("loop.code_fix.enqueue_code_fix_job", sync_enqueue)
    high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
    engine.resume_after_approval(high.id, "oncall@acme")
    exe = engine.store.get_action(high.id).artifacts["execution"]
    assert exe.get("code_fix") == "queued" or isinstance(exe.get("code_fix"), dict)
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
                "repo": "saurabh4269/cove",
                "deploy_url": "https://example.test",
                "token": "dev-token",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["tenant"]["repo"] == "saurabh4269/cove"
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
        assert "saurabh4269/cove" in gates.json()["gate"]["label"]
        pending = gates.json()["pending"]
        flag_rows = [p for p in pending if (p.get("artifacts") or {}).get("flag")]
        issue_rows = [p for p in pending if (p.get("artifacts") or {}).get("github_issue")]
        assert flag_rows
        assert all(p["gate_mode"] == "github_pr" for p in flag_rows)
        if issue_rows:
            assert issue_rows[0]["gate_mode"] == "github_issue"
            assert "issue" in issue_rows[0]["gate"]
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


def test_oauth_status_start_and_never_echo_secret(tmp_path, monkeypatch, engine):
    monkeypatch.setenv("LOOP_DATA_DIR", str(tmp_path))
    for key in (
        "LOOP_GOOGLE_OAUTH_CLIENT_ID",
        "LOOP_GOOGLE_OAUTH_CLIENT_SECRET",
        "LOOP_OAUTH_GCS_URI",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        st = client.get("/api/oauth/google")
        assert st.status_code == 200
        body = st.json()
        assert body["configured"] is False
        assert body["connected"] is False
        assert "client_secret" not in body
        assert body["authorize_url"].endswith("/api/oauth/google/start")
        assert "auth/overview" in body["console"]["overview"]
        start = client.get("/api/oauth/google/start", follow_redirects=False)
        assert start.status_code == 302
        assert "/connect" in start.headers["location"]
        assert "workspace=error" in start.headers["location"]
        saved = client.post(
            "/api/oauth/google/client",
            json={"client_id": "cid.apps.googleusercontent.com", "client_secret": "super-secret"},
        )
        assert saved.status_code == 200
        assert saved.json()["configured"] is True
        assert "super-secret" not in str(saved.json())
        assert "client_secret" not in saved.json()
        start2 = client.get("/api/oauth/google/start", follow_redirects=False)
        assert start2.status_code == 302
        loc = start2.headers["location"]
        assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "access_type=offline" in loc
        assert "prompt=consent" in loc
        assert "cid.apps.googleusercontent.com" in loc
        bad = client.get("/api/oauth/google/callback?code=x&state=wrong", follow_redirects=False)
        assert bad.status_code == 302
        assert "workspace=error" in bad.headers["location"]


def test_mail_draft_applies_when_gmail_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("LOOP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOOP_GMAIL_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(
        "loop.connectors.mail.gmail_json",
        lambda *a, **k: (200, {"id": "dr_1"}),
    )
    r = draft("a@b.c", "s", "b")
    assert r.status == "applied"
    assert r.url and "dr_1" in r.url
    assert send().status == "denied"
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
    api_src = (ROOT / "services" / "loop" / "loop" / "api.py").read_text()
    assert 'rel.split("/", 1)[0] in {"shop", "company"}' in api_src
