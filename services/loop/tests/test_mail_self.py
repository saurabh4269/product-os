from __future__ import annotations

from loop.connectors import mail


def test_send_third_party_denied(monkeypatch):
    monkeypatch.setattr(mail, "access_token", lambda: "")
    monkeypatch.setattr(mail, "connected_email", lambda: "me@example.com")
    out = mail.send("other@example.com", "hi", "body")
    assert out.status == "denied"
    assert out.detail == "GMAIL_SEND_SELF_ONLY"


def test_send_empty_to_denied(monkeypatch):
    monkeypatch.setattr(mail, "connected_email", lambda: "me@example.com")
    out = mail.send("", "hi", "body")
    assert out.status == "denied"


def test_send_self_calls_gmail(monkeypatch):
    calls: list[tuple] = []

    monkeypatch.setattr(mail, "access_token", lambda: "tok")
    monkeypatch.setattr(mail, "connected_email", lambda: "me@example.com")

    def fake_gmail(method, path, body=None):
        calls.append((method, path, body))
        return 200, {"id": "msg_1"}

    monkeypatch.setattr(mail, "gmail_json", fake_gmail)
    out = mail.send_to_self("Subject", "Hello")
    assert out.status == "applied"
    assert out.detail == "Sent to me@example.com"
    assert calls and calls[0][0] == "POST" and calls[0][1] == "/messages/send"


def test_send_without_oauth_skips(monkeypatch):
    monkeypatch.setattr(mail, "access_token", lambda: "")
    monkeypatch.setattr(mail, "connected_email", lambda: "")
    out = mail.send_to_self("Subject", "Hello")
    assert out.status == "skipped"


def test_draft_rejects_invalid_to(monkeypatch):
    monkeypatch.setattr(mail, "access_token", lambda: "tok")
    monkeypatch.setattr(mail, "connected_email", lambda: "")
    out = mail.draft("reviewers", "Subject", "Hello")
    assert out.status == "skipped"
    assert "Invalid To" in out.detail
