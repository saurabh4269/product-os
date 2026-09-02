"""Tenant incident lifecycle — Cove checkout regression without fixture scripts."""

from __future__ import annotations

from loop.incident_lifecycle import (
    arm_checkout_regression,
    incident_lifecycle,
    sync_regression_from_product,
)
from loop.models import InvestigationState
from loop.tenant import Tenant, flag_key, hash_token


def test_lifecycle_before_trigger(engine):
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    out = incident_lifecycle(engine, "acme")
    assert out["status"] == "ok"
    assert out["checkout_url"] == "https://cove.example.test/checkout"
    assert out["regression_active"] is True
    assert out["phase"] == "degraded"
    assert out["headline"]
    assert out["steps"][0]["id"] == "degraded"
    assert out["steps"][0]["done"] is True
    assert out["steps"][1]["id"] == "trigger"
    assert out["steps"][1]["done"] is False


def test_lifecycle_after_ingest(engine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    from loop.world import ingest_tenant_signal

    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.22,
        baseline=0.72,
        note="Checkout hung on payment SDK",
        source="cove.checkout",
        async_finish=False,
    )
    out = incident_lifecycle(engine, "acme")
    assert out["room_id"]
    assert out["steps"][1]["done"] is True
    assert out["phase"] in {"signal_received", "diagnosing", "awaiting_approval"}
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv
    assert inv.tenant_id == "acme"


def test_lifecycle_awaiting_approval(engine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    from loop.world import ingest_tenant_signal

    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.22,
        baseline=0.72,
        note="Checkout hung on payment SDK",
        source="cove.checkout",
        async_finish=False,
    )
    out = incident_lifecycle(engine, "acme")
    inv = engine.store.get_investigation(out["investigation_id"])
    assert inv
    assert inv.state == InvestigationState.AWAITING_APPROVAL
    assert out["steps"][2]["done"] is True
    assert out["phase"] == "awaiting_approval"
    assert out["pending_action_id"]


def test_arm_resets_after_rollback(engine):
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    engine.store.set_flag(flag_key("acme", "pay_sdk_4_3"), "off", "rollback")
    out = arm_checkout_regression(engine, "acme")
    assert out["value"] == "on"
    assert engine.store.get_flag(flag_key("acme", "pay_sdk_4_3")) == "on"


def test_publish_incident_lifecycle_ws(engine, monkeypatch):
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    from loop.incident_lifecycle import publish_incident_lifecycle

    published: list[dict] = []

    class _Hub:
        def publish_global(self, event: dict) -> None:
            published.append(event)

    import loop.live as live_mod

    monkeypatch.setattr(live_mod, "HUB", _Hub())
    out = publish_incident_lifecycle(engine, "acme")
    assert out and out["tenant_id"] == "acme"
    assert published and published[0]["type"] == "incident_lifecycle"


def test_ingest_after_terminal_investigation_opens_new_room(engine, monkeypatch):
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    from loop.world import ingest_tenant_signal

    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.22,
        baseline=0.72,
        note="first hang",
        source="cove.checkout",
        async_finish=False,
    )
    inv = engine.store.list_investigations()[-1]
    inv.state = InvestigationState.RESOLVED
    engine.store.put_investigation(inv)
    before_rooms = len(engine.store.list_rooms())
    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.18,
        baseline=0.7,
        note="second hang after recovery",
        source="cove.checkout",
        async_finish=False,
    )
    assert len(engine.store.list_rooms()) > before_rooms


def test_ingest_with_stuck_gathering_opens_new_pipeline(engine, monkeypatch):
    """Hosted repro: open room in GATHERING must not join-only — run investigation."""
    monkeypatch.setenv("LOOP_INGEST_ASYNC", "0")
    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="saurabh4269/cove",
            deploy_url="https://cove.example.test",
            token_hash=hash_token("tok"),
            flag_names=["pay_sdk_4_3"],
            connected=True,
        )
    )
    sync_regression_from_product(engine, "acme")
    from loop.world import ingest_tenant_signal

    ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.22,
        baseline=0.72,
        note="first hang",
        source="cove.checkout",
        async_finish=False,
    )
    inv = engine.store.list_investigations()[-1]
    inv.state = InvestigationState.GATHERING
    engine.store.put_investigation(inv)
    before = len(engine.store.list_investigations())
    out = ingest_tenant_signal(
        engine,
        engine.store.get_tenant("acme"),
        metric="checkout_conversion",
        magnitude=-0.2,
        baseline=0.7,
        note="checkout hang again",
        source="cove.checkout",
        async_finish=False,
    )
    assert out.get("joined") is not True
    assert len(engine.store.list_investigations()) > before
    assert engine.store.list_evidence(engine.store.list_investigations()[-1].id)
