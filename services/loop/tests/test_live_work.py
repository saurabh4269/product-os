from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from loop import api as api_mod
from loop.live_work import MAX_OPEN_ROOMS, MESSAGES_PER_ROOM, build_live_work, card_from_message
from loop.models import Room, RoomKind, RoomMessage
from loop.proof import enrich_card_proof
from loop.world import post


def test_live_work_endpoint_piles_receipts(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.status == "open")
    post(
        engine,
        room.id,
        author="analytics_agent",
        author_kind="agent",
        kind="artifact",
        text="BigQuery read checkout_conversion · Chrome · last 7d",
        artifact_type="warehouse",
        artifact={"metric": "checkout_conversion", "source": "bigquery"},
    )
    post(
        engine,
        room.id,
        author="code_agent",
        author_kind="agent",
        kind="artifact",
        text="Opened draft PR for SDK rollback",
        artifact_type="pr",
        artifact={"pr_url": "https://github.com/saurabh4269/cove/pull/9"},
    )
    post(
        engine,
        room.id,
        author="coordination_agent",
        author_kind="agent",
        kind="artifact",
        text="Mail sent to you@example.com: [LOOP] review",
        artifact_type="mail",
        artifact={
            "channel": "gmail",
            "gmail_url": "https://mail.google.com/mail/u/0/#inbox/abc",
            "report": {"status": "applied", "connector": "mail.send"},
        },
    )
    with TestClient(api_mod.app) as client:
        res = client.get("/api/live-work")
        assert res.status_code == 200
        body = res.json()
        assert [c["id"] for c in body["columns"]]
        assert set(c["id"] for c in body["columns"]).issubset(
            {"signal", "evidence", "customer", "code", "experiment", "approve", "verify"}
        )
        cards = body["cards"]
        assert any(c["badge"] == "BigQuery" and c["column"] == "evidence" for c in cards)
        assert any(c["badge"] == "PR open" and c["column"] == "code" and c.get("pr_url") for c in cards)
        assert any(c["badge"] == "Mail sent" and c["column"] == "verify" for c in cards)


def test_card_from_message_contact_phone():
    msg = RoomMessage(
        id="m1",
        room_id="r1",
        author="customer_voice_agent",
        author_kind="agent",
        kind="chat",
        text="Saved callback number +14155550100 from Cove feedback.",
        artifact_type="contact",
        artifact={"phone": "+14155550100"},
        created_at=datetime.now(UTC),
    )
    card = card_from_message(msg, room_title="Cove feedback")
    assert card is not None
    assert card["column"] == "customer"
    assert card["phone"] == "+14155550100"


def test_build_live_work_empty_store(engine):
    out = build_live_work(engine.store)
    assert out["columns"]
    assert isinstance(out["cards"], list)


def test_build_live_work_bounds_many_rooms_and_messages(engine):
    """Board scan stays bounded when many open rooms carry large histories."""
    now = datetime.now(UTC)
    for i in range(MAX_OPEN_ROOMS + 8):
        room = Room(
            id=f"room_bulk_{i}",
            kind=RoomKind.INCIDENT,
            title=f"Bulk room {i}",
            topic=f"topic {i}",
            status="open",
            created_at=now,
            last_message_at=now,
        )
        engine.store.put_room(room)
        for j in range(MESSAGES_PER_ROOM + 20):
            engine.store.put_message(
                RoomMessage(
                    id=f"msg_{i}_{j}",
                    room_id=room.id,
                    author="analytics_agent",
                    author_kind="agent",
                    kind="artifact",
                    text=f"Warehouse read metric_{i}_{j} · Chrome · last 7d",
                    artifact_type="warehouse",
                    artifact={"metric": f"metric_{i}_{j}", "source": "bigquery"},
                    created_at=now,
                )
            )

    started = time.monotonic()
    out = build_live_work(engine.store, limit=40, room_limit=MAX_OPEN_ROOMS, messages_per_room=MESSAGES_PER_ROOM)
    elapsed = time.monotonic() - started

    assert elapsed < 5.0
    assert len(out["cards"]) <= 40
    assert out["stats"]["total"] <= 40


def test_live_work_endpoint_does_not_hang_with_many_messages(engine, monkeypatch):
    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)

    now = datetime.now(UTC)
    room = Room(
        id="room_hang",
        kind=RoomKind.INCIDENT,
        title="Hang repro",
        topic="hang",
        status="open",
        created_at=now,
        last_message_at=now,
    )
    engine.store.put_room(room)
    for i in range(250):
        engine.store.put_message(
            RoomMessage(
                id=f"hang_msg_{i}",
                room_id=room.id,
                author="code_agent",
                author_kind="agent",
                kind="artifact",
                text=f"Opened draft PR #{i} for SDK rollback",
                artifact_type="pr",
                artifact={"pr_url": f"https://github.com/saurabh4269/cove/pull/{900 + i}"},
                created_at=now,
            )
        )

    github_calls: list[str] = []
    bq_calls: list[str] = []

    def _fake_github(url: str, *, tenant=None):
        github_calls.append(url)
        return {"kind": "github", "status": "applied", "url": url}

    def _fake_warehouse(*_args, **_kwargs):
        bq_calls.append("warehouse")
        return {"kind": "warehouse", "status": "applied", "rows": []}

    monkeypatch.setattr("loop.proof.github_pr_proof", _fake_github)
    monkeypatch.setattr("loop.proof.warehouse_proof", _fake_warehouse)

    started = time.monotonic()
    with TestClient(api_mod.app) as client:
        res = client.get("/api/live-work")
    elapsed = time.monotonic() - started

    assert res.status_code == 200
    assert elapsed < 5.0
    body = res.json()
    assert isinstance(body.get("cards"), list)
    assert github_calls == []
    assert bq_calls == []


def test_enrich_card_proof_skips_network_when_disabled(engine):
    card = {
        "id": "m1",
        "artifact_type": "pr",
        "pr_url": "https://github.com/saurabh4269/cove/pull/99",
        "room_id": "room_x",
    }
    out = enrich_card_proof(engine.store, dict(card), engine=engine, allow_network=False)
    assert out.get("proof") is None


def test_list_messages_recent_limits_rows(engine):
    now = datetime.now(UTC)
    room = Room(
        id="room_recent",
        kind=RoomKind.INCIDENT,
        title="Recent",
        topic="recent",
        status="open",
        created_at=now,
    )
    engine.store.put_room(room)
    for i in range(150):
        engine.store.put_message(
            RoomMessage(
                id=f"recent_{i}",
                room_id=room.id,
                author="system",
                author_kind="system",
                kind="chat",
                text=f"line {i}",
                created_at=datetime.fromtimestamp(now.timestamp() + i, tz=UTC),
            )
        )

    recent = engine.store.list_messages_recent(room.id, limit=40)
    assert len(recent) == 40
    assert recent[0].text == "line 110"
    assert recent[-1].text == "line 149"
