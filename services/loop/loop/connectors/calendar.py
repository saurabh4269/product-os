"""Calendar hold. No fake Meet link. Creates an event only after Workspace OAuth."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from loop.connectors.google_oauth import access_token, calendar_json
from loop.tenant import ConnectorReport


def hold(summary: str, when_iso: str) -> ConnectorReport:
    if not access_token():
        return ConnectorReport(
            status="skipped",
            connector="calendar.hold",
            detail="no Workspace OAuth",
        )
    start = _when(when_iso)
    end = start + timedelta(minutes=30)
    code, payload = calendar_json(
        "POST",
        "/calendars/primary/events",
        {
            "summary": summary,
            "description": "Product OS hold. Not a Meet link unless you add one.",
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        },
    )
    if code in {200, 201} and payload.get("id"):
        return ConnectorReport(
            status="applied",
            connector="calendar.hold",
            detail="calendar event created",
            url=payload.get("htmlLink"),
        )
    err = payload.get("error") or payload
    if isinstance(err, dict):
        err = err.get("message") or err
    return ConnectorReport(
        status="skipped",
        connector="calendar.hold",
        detail=f"calendar hold failed: {err}",
    )


def _when(when_iso: str) -> datetime:
    raw = (when_iso or "").strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc) + timedelta(hours=1)
