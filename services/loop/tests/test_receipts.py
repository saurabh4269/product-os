"""Work receipts land in the room thread when side effects run."""

from __future__ import annotations

from loop.models import Room, RoomKind
from loop.receipts import flag_proof, post_connector_receipts, post_receipt


def test_post_receipt_appears_in_room(engine):
    room = Room(
        id="room_receipt_test",
        kind=RoomKind.INCIDENT,
        title="Receipt room",
        topic="t",
        status="open",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        members=["code_agent", "you"],
    )
    engine.store.put_room(room)
    post_receipt(
        engine,
        room.id,
        kind="flags",
        title="Flag pay_sdk → off",
        status="done",
        proof=flag_proof(name="pay_sdk", value="off", previous="on"),
    )
    msgs = engine.store.list_messages(room.id)
    assert any(m.artifact_type == "receipt" for m in msgs)
    art = next(m.artifact for m in msgs if m.artifact_type == "receipt")
    assert art["proof"]["kind"] == "flags"
    assert art["status"] == "done"


def test_connector_bundle_posts_flag_and_mail(engine):
    room = Room(
        id="room_receipt_bundle",
        kind=RoomKind.INCIDENT,
        title="Bundle",
        topic="t",
        status="open",
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        members=["code_agent"],
    )
    engine.store.put_room(room)
    post_connector_receipts(
        engine,
        room.id,
        flag={"name": "feature_x", "value": "off", "from": "on"},
        connectors=[
            {
                "status": "applied",
                "connector": "gmail.draft",
                "detail": "draft ready",
                "url": "https://mail.google.com/mail/#drafts",
            }
        ],
    )
    types = [m.artifact_type for m in engine.store.list_messages(room.id)]
    assert types.count("receipt") >= 2
    kinds = [m.artifact.get("kind") for m in engine.store.list_messages(room.id) if m.artifact_type == "receipt"]
    assert "flags" in kinds
    assert "gmail" in kinds
