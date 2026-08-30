"""Draft mail. Send stays denied until an explicit product decision + OAuth."""

from __future__ import annotations

import os

from loop.tenant import ConnectorReport


def draft(to: str, subject: str, body: str) -> ConnectorReport:
    if not os.environ.get("LOOP_GMAIL_ACCESS_TOKEN"):
        return ConnectorReport(
            status="skipped",
            connector="mail.draft",
            detail="no LOOP_GMAIL_ACCESS_TOKEN — draft not sent to Gmail",
        )
    # Real Gmail draft insert lands in a later slice when the OAuth client exists.
    return ConnectorReport(
        status="skipped",
        connector="mail.draft",
        detail="Gmail API client not wired yet; token present but unused",
    )


def send(*_a, **_k) -> ConnectorReport:
    return ConnectorReport(status="denied", connector="mail.send", detail="GMAIL_CANNOT_SEND")
