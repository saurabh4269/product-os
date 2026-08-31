from loop.narrate import ack_line, ask_line, build_workflow_chat, humanize_handoff


def test_humanize_bare_token():
    line = humanize_handoff("investigator_agent", "analytics_agent", "analytics")
    assert "Asked Analytics" in line
    assert "numbers" in line


def test_humanize_keeps_full_sentence():
    s = "funnel conversion by browser"
    assert humanize_handoff("orchestrator", "analytics_agent", s) == s


def test_ask_line_group_chat():
    line = ask_line("investigator_agent", "analytics_agent", "analytics")
    assert line.startswith("Analytics,")
    assert "numbers" in line.lower() or "pull" in line.lower()


def test_ack_line():
    assert "on it" in ack_line("analytics_agent").lower() or "checking" in ack_line("analytics_agent").lower()


def test_build_workflow_chat_end_to_end(engine):
    from datetime import UTC, datetime

    from loop.models import AgentCall, RoomMessage

    engine.seed_world()
    room = next(r for r in engine.store.list_rooms() if r.investigation_id)
    inv_id = room.investigation_id
    assert inv_id
    engine.store.put_agent_call(
        AgentCall(
            id="call_test_1",
            investigation_id=inv_id,
            from_agent="investigator_agent",
            to_agent="analytics_agent",
            trust_boundary="TB-2",
            summary="analytics",
            status="ok",
            started_at=datetime.now(UTC),
        )
    )
    engine.store.put_message(
        RoomMessage(
            id="msg_ev_1",
            room_id=room.id,
            author="analytics_agent",
            author_kind="agent",
            kind="artifact",
            text="Checkout conversion down 14% on Chrome",
            artifact_type="evidence",
            artifact={},
            created_at=datetime.now(UTC),
        )
    )
    calls = list(engine.store.list_agent_calls(inv_id))
    msgs = list(engine.store.list_messages(room.id))
    events = build_workflow_chat(
        investigation_id=inv_id,
        room=room,
        agent_calls=calls,
        messages=msgs,
    )
    kinds = {e["kind"] for e in events}
    assert "chat" in kinds
    assert "system" in kinds
    texts = " ".join(e.get("text", "") for e in events if e["kind"] == "chat")
    assert "Analytics" in texts or "analytics" in texts.lower()
    assert any(e.get("author") == "analytics_agent" for e in events if e["kind"] == "chat")
