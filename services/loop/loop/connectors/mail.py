"""Draft mail. Send stays denied. Drafts hit Gmail only after Workspace OAuth."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

from loop.connectors.google_oauth import access_token, gmail_json
from loop.tenant import ConnectorReport


def draft(to: str, subject: str, body: str) -> ConnectorReport:
    if not access_token():
        return ConnectorReport(
            status="skipped",
            connector="mail.draft",
            detail="no Workspace OAuth — draft not sent to Gmail",
        )
    msg = MIMEText(body or "")
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")
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


def send(*_a, **_k) -> ConnectorReport:
    return ConnectorReport(status="denied", connector="mail.send", detail="GMAIL_CANNOT_SEND")
