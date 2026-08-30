"""Calendar hold. No fake Meet link."""

from __future__ import annotations

import os

from loop.tenant import ConnectorReport


def hold(summary: str, when_iso: str) -> ConnectorReport:
    if not os.environ.get("LOOP_CALENDAR_ACCESS_TOKEN"):
        return ConnectorReport(
            status="skipped",
            connector="calendar.hold",
            detail="no LOOP_CALENDAR_ACCESS_TOKEN",
        )
    return ConnectorReport(
        status="skipped",
        connector="calendar.hold",
        detail="Calendar API client not wired yet; token present but unused",
    )
