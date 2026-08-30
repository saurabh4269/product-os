from __future__ import annotations

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.connectors.github import open_pr
from loop.connectors.mail import draft, send
from loop.models import OutcomeVerdict, RiskTier
from loop.tenant import Tenant, hash_token, token_ok


def test_token_hash_roundtrip():
    t = Tenant(id="x", name="X", product="Y", token_hash=hash_token("secret"))
    assert token_ok(t, "secret")
    assert not token_ok(t, "nope")
    assert not token_ok(t, None)


def test_connectors_skip_without_secrets():
    t = Tenant(id="acme", name="Acme", product="Y")
    gh = open_pr(t, "hi", "body")
    assert gh.status == "skipped"
    assert gh.url is None
    assert draft("a@b.c", "s", "b").status == "skipped"
    assert send().status == "denied"


def test_execute_does_not_claim_a_pr_without_github(engine):
    from loop.tenant import seed_placeholder

    seed_placeholder(engine.store)
    engine.seed_world()
    engine.detect_signals()
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


def test_tenant_http_flags_and_ingest(engine, monkeypatch):
    from loop.tenant import Tenant, hash_token

    engine.seed_world()
    engine.store.put_tenant(
        Tenant(id="acme", name="Acme", product="Y", token_hash=hash_token("dev-token"), repo="")
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
        assert any(t["id"] == "acme" for t in listed.json()["tenants"])
        assert "token_hash" not in listed.json()["tenants"][0]
        sig = client.post(
            "/api/t/acme/signals",
            headers={"Authorization": "Bearer dev-token"},
            json={"metric": "purchase_conversion", "magnitude": -0.2, "note": "from Y"},
        )
        assert sig.status_code == 200
        assert sig.json()["signal"]["source"] == "tenant.acme"
        voice = client.post(
            "/api/t/acme/voice",
            headers={"Authorization": "Bearer dev-token"},
            json={"text": "checkout felt slow", "tokenized_user": "tok_1"},
        )
        assert voice.status_code == 200
        assert voice.json()["voice"]["kind"] == "customer"
