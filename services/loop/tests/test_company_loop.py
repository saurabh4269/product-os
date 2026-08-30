"""Northstar is a real dummy tenant: shop + ads + a full detect→approve→verify loop."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.models import OutcomeVerdict, RiskTier

ROOT = Path(__file__).resolve().parents[3]
SHOP = ROOT / "apps" / "northstar-shop"


def test_shop_and_ads_exist():
    for name in ("index.html", "checkout.html", "start.html", "ads.html", "runtime.js"):
        assert (SHOP / "web" / name).is_file()
    assert (SHOP / "pay-sdk-adapter.js").is_file()
    assert (SHOP / "onboarding.js").is_file()
    assert (SHOP / "checkout.js").is_file()


def test_ads_are_flat_and_joined(engine):
    spend = engine.wh.ads_spend_by_date()
    assert spend
    values = list(spend.values())
    assert all(200 < v < 2000 for v in values)
    # Two campaigns, spend should not swing like a conversion cliff.
    assert max(values) / min(values) < 1.25


def test_full_loop_changes_the_product(engine):
    world = engine.seed_world()
    assert len(world["scenarios"]) == 6
    signals = engine.detect_signals()
    assert signals, "warehouse must fire an unprompted conversion signal"

    pending = engine.store.pending_approvals()
    assert len(pending) >= 5
    high = next(a for a in pending if a.risk_tier == RiskTier.HIGH)
    assert engine.store.get_flag("pay_sdk_4_3") in {None, "on"}

    out = engine.resume_after_approval(high.id, "oncall@northstar")
    assert out.verdict == OutcomeVerdict.RESOLVED
    assert engine.store.get_flag("pay_sdk_4_3") == "off"
    assert engine.store.list_outcomes()
    assert engine.store.list_lessons()
    inv = engine.store.get_investigation(high.investigation_id)
    assert inv and inv.closed_at

    medium = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.MEDIUM)
    out_b = engine.resume_after_approval(medium.id, "pm@northstar")
    assert out_b.verdict == OutcomeVerdict.RESOLVED
    assert engine.store.list_outcomes()[-1].investigation_id == medium.investigation_id


def test_company_http_and_shop_follow_flags(engine, monkeypatch):
    engine.seed_world()
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    with TestClient(api_mod.app) as client:
        shop = client.get("/shop/")
        assert shop.status_code == 200
        assert b"Quiet things for a house" in shop.content
        checkout = client.get("/shop/checkout.html")
        assert checkout.status_code == 200
        assert b"Pay SDK" in checkout.content
        ads = client.get("/shop/ads.html")
        assert ads.status_code == 200

        before = client.get("/api/company")
        assert before.status_code == 200
        body = before.json()
        assert body["company"]["name"] == "Northstar"
        assert body["company"]["tagline"] == "Quiet things for a house"
        assert body["flags"]["pay_sdk_4_3"] == "on"
        assert len(body["ads"]) >= 2
        names = {a["name"] for a in body["ads"]}
        assert "US-Search-Brand" in names
        assert "US-Shopping-Home" in names
        assert body["loop"]["pending"] >= 5

        high = next(a for a in engine.store.pending_approvals() if a.risk_tier == RiskTier.HIGH)
        decided = client.post(f"/api/approvals/{high.id}", json={"approver": "oncall@northstar", "decision": "approve"})
        assert decided.status_code == 200
        after = client.get("/api/company")
        assert after.json()["flags"]["pay_sdk_4_3"] == "off"
        assert after.json()["loop"]["resolved"] >= 1
