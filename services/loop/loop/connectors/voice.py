"""Outbound call stays text-fallback. Ingest is HTTP, not this connector."""

from __future__ import annotations

import os

from loop.tenant import ConnectorReport


def place_call(tokenized_user: str, reason: str) -> ConnectorReport:
    if not os.environ.get("LOOP_LIVE_ENTITLED"):
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail="Live API not entitled — text fallback only, no PSTN",
        )
    _ = tokenized_user, reason
    return ConnectorReport(
        status="skipped",
        connector="voice.place_call",
        detail="Live entitled but outbound call is not implemented; no PSTN",
    )
