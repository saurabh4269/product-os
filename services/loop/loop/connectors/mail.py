"""Gmail drafts + send-to-self only. Never mail third parties."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

from loop.connectors.google_oauth import access_token, gmail_json
from loop.connectors.google_oauth import status as oauth_status
from loop.tenant import ConnectorReport


def _raw_message(to: str, subject: str, body: str) -> str:
    msg = MIMEText(body or "")
    msg["to"] = to
    msg["subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")


def connected_email() -> str:
    return (oauth_status().get("email") or "").strip().lower()


def draft(to: str, subject: str, body: str) -> ConnectorReport:
    if not access_token():
        return ConnectorReport(
            status="skipped",
            connector="mail.draft",
            detail="no Workspace OAuth",
        )
    raw = _raw_message(to, subject, body)
    code, payload = gmail_json("POST", "/drafts", {"message": {"raw": raw}})
    if code in {200, 201} and payload.get("id"):
        draft_id = payload["id"]
        return ConnectorReport(
            status="applied",
            connector="mail.draft",
            detail="Gmail draft created",
            url=f"https://mail.google.com/mail/#drafts?compose={draft_id}",
        )
    err = payload.get("error") or payload
    if isinstance(err, dict):
        err = err.get("message") or err
    return ConnectorReport(
        status="skipped",
        connector="mail.draft",
        detail=f"Gmail draft failed: {err}",
    )


def send(to: str = "", subject: str = "", body: str = "") -> ConnectorReport:
    """Send only when `to` is the connected Workspace inbox. All other recipients denied."""
    me = connected_email()
    dest = (to or "").strip().lower()
    if not dest or dest != me:
        return ConnectorReport(
            status="denied",
            connector="mail.send",
            detail="GMAIL_SEND_SELF_ONLY",
        )
    if not access_token() or not me:
        return ConnectorReport(
            status="skipped",
            connector="mail.send",
            detail="no Workspace OAuth",
        )
    raw = _raw_message(me, subject, body)
    code, payload = gmail_json("POST", "/messages/send", {"raw": raw})
    if code in {200, 201} and payload.get("id"):
        mid = payload["id"]
        return ConnectorReport(
            status="applied",
            connector="mail.send",
            detail=f"Sent to {me}",
            url=f"https://mail.google.com/mail/u/0/#inbox/{mid}",
        )
    err = payload.get("error") or payload
    if isinstance(err, dict):
        err = err.get("message") or err
    return ConnectorReport(
        status="skipped",
        connector="mail.send",
        detail=f"Gmail send failed: {err}",
    )


def send_to_self(subject: str, body: str) -> ConnectorReport:
    """Convenience: deliver to the connected Workspace inbox."""
    me = connected_email()
    if not me:
        return ConnectorReport(
            status="skipped",
            connector="mail.send",
            detail="no Workspace OAuth",
        )
    return send(me, subject, body)
