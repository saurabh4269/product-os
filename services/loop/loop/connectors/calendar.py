"""Google Calendar connector — list, free/busy, suggest, create (MCP-shaped tools).

Honest skip without Workspace OAuth. Never invent Meet links when create fails.
Send stays out of scope (mail connector). Merge stays out of scope (never).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from loop.connectors.google_oauth import access_token, calendar_json
from loop.tenant import ConnectorReport


def _parse_when(when_iso: str) -> datetime:
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


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capabilities() -> dict[str, Any]:
    oauth = bool(access_token())
    return {
        "oauth": oauth,
        "tools": ["list_events", "check_availability", "suggest_times", "create_event", "hold"],
        "mode": "google_calendar" if oauth else "simulated",
        "detail": (
            "Workspace OAuth connected — Calendar API live."
            if oauth
            else "No Workspace OAuth — availability/suggest are simulated; create/hold skip."
        ),
    }


def list_events(*, time_min: str = "", time_max: str = "", max_results: int = 10) -> ConnectorReport:
    if not access_token():
        return ConnectorReport(
            status="skipped",
            connector="calendar.list",
            detail="no Workspace OAuth",
        )
    start = _parse_when(time_min) if time_min else datetime.now(timezone.utc)
    end = _parse_when(time_max) if time_max else start + timedelta(days=7)
    code, payload = calendar_json(
        "GET",
        "/calendars/primary/events"
        f"?timeMin={_iso(start)}&timeMax={_iso(end)}&singleEvents=true"
        f"&orderBy=startTime&maxResults={max_results}",
        None,
    )
    if code == 200:
        items = payload.get("items") or []
        return ConnectorReport(
            status="applied",
            connector="calendar.list",
            detail=f"{len(items)} events",
            url=None,
        )
    err = payload.get("error") or payload
    return ConnectorReport(status="skipped", connector="calendar.list", detail=str(err))


def check_availability(
    *,
    calendars: list[str] | None = None,
    time_min: str = "",
    time_max: str = "",
) -> dict[str, Any]:
    """Return busy blocks. Simulated when OAuth missing."""
    start = _parse_when(time_min) if time_min else datetime.now(timezone.utc)
    end = _parse_when(time_max) if time_max else start + timedelta(days=3)
    ids = calendars or ["primary"]
    if not access_token():
        # Deterministic busy: lunch 12–13 UTC each day in window
        busy: list[dict[str, str]] = []
        day = start.replace(hour=0, minute=0, second=0, microsecond=0)
        while day < end:
            lunch0 = day.replace(hour=12)
            lunch1 = day.replace(hour=13)
            if lunch1 > start and lunch0 < end:
                busy.append({"start": _iso(max(lunch0, start)), "end": _iso(min(lunch1, end))})
            day += timedelta(days=1)
        return {
            "status": "simulated",
            "connector": "calendar.freebusy",
            "calendars": ids,
            "time_min": _iso(start),
            "time_max": _iso(end),
            "busy": busy,
            "detail": "simulated free/busy (no Workspace OAuth)",
        }
    code, payload = calendar_json(
        "POST",
        "/freeBusy",
        {
            "timeMin": _iso(start),
            "timeMax": _iso(end),
            "items": [{"id": c} for c in ids],
        },
    )
    busy_all: list[dict[str, str]] = []
    if code == 200:
        for cal in (payload.get("calendars") or {}).values():
            for b in cal.get("busy") or []:
                busy_all.append({"start": b.get("start", ""), "end": b.get("end", "")})
        return {
            "status": "applied",
            "connector": "calendar.freebusy",
            "calendars": ids,
            "time_min": _iso(start),
            "time_max": _iso(end),
            "busy": busy_all,
            "detail": f"{len(busy_all)} busy blocks",
        }
    return {
        "status": "skipped",
        "connector": "calendar.freebusy",
        "calendars": ids,
        "time_min": _iso(start),
        "time_max": _iso(end),
        "busy": [],
        "detail": str(payload.get("error") or payload),
    }


def suggest_times(
    *,
    duration_minutes: int = 30,
    calendars: list[str] | None = None,
    time_min: str = "",
    time_max: str = "",
    workday_start_hour: int = 9,
    workday_end_hour: int = 17,
    limit: int = 5,
) -> dict[str, Any]:
    """Suggest free slots overlapping work hours, avoiding busy blocks."""
    start = _parse_when(time_min) if time_min else datetime.now(timezone.utc) + timedelta(hours=1)
    # Snap to next half hour
    start = start.replace(minute=(0 if start.minute < 30 else 30), second=0, microsecond=0)
    if start.minute == 0 and datetime.now(timezone.utc) > start:
        start += timedelta(minutes=30)
    end = _parse_when(time_max) if time_max else start + timedelta(days=5)
    avail = check_availability(calendars=calendars, time_min=_iso(start), time_max=_iso(end))
    busy = []
    for b in avail.get("busy") or []:
        try:
            busy.append((_parse_when(b["start"]), _parse_when(b["end"])))
        except (KeyError, TypeError, ValueError):
            continue

    def overlaps(a0: datetime, a1: datetime) -> bool:
        return any(a0 < b1 and b0 < a1 for b0, b1 in busy)

    slots: list[dict[str, Any]] = []
    cursor = start
    dur = timedelta(minutes=max(15, duration_minutes))
    while cursor + dur <= end and len(slots) < limit:
        if workday_start_hour <= cursor.hour < workday_end_hour:
            slot_end = cursor + dur
            if slot_end.hour < workday_end_hour or (
                slot_end.hour == workday_end_hour and slot_end.minute == 0
            ):
                if not overlaps(cursor, slot_end):
                    slots.append(
                        {
                            "start": _iso(cursor),
                            "end": _iso(slot_end),
                            "duration_minutes": duration_minutes,
                        }
                    )
        cursor += timedelta(minutes=30)

    return {
        "status": avail.get("status"),
        "connector": "calendar.suggest",
        "duration_minutes": duration_minutes,
        "slots": slots,
        "detail": f"{len(slots)} candidate slots ({avail.get('detail')})",
    }


def create_event(
    summary: str,
    when_iso: str,
    *,
    duration_minutes: int = 30,
    description: str = "",
    attendees: list[str] | None = None,
    with_meet: bool = False,
) -> ConnectorReport:
    if not access_token():
        return ConnectorReport(
            status="skipped",
            connector="calendar.create",
            detail="no Workspace OAuth",
        )
    start = _parse_when(when_iso)
    end = start + timedelta(minutes=max(15, duration_minutes))
    body: dict[str, Any] = {
        "summary": summary,
        "description": description or "Product OS coordination hold.",
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees if "@" in e]
    path = "/calendars/primary/events"
    if with_meet:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": f"loop-{int(start.timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
        path = "/calendars/primary/events?conferenceDataVersion=1"
    code, payload = calendar_json("POST", path, body)
    if code in {200, 201} and payload.get("id"):
        meet = None
        for ep in payload.get("conferenceData", {}).get("entryPoints") or []:
            if ep.get("entryPointType") == "video":
                meet = ep.get("uri")
                break
        return ConnectorReport(
            status="applied",
            connector="calendar.create",
            detail="calendar event created" + (" with Meet" if meet else ""),
            url=meet or payload.get("htmlLink"),
        )
    err = payload.get("error") or payload
    if isinstance(err, dict):
        err = err.get("message") or err
    return ConnectorReport(
        status="skipped",
        connector="calendar.create",
        detail=f"calendar create failed: {err}",
    )


def hold(summary: str, when_iso: str, *, duration_minutes: int = 30) -> ConnectorReport:
    """Back-compat: create a simple hold (no Meet)."""
    report = create_event(summary, when_iso, duration_minutes=duration_minutes, with_meet=False)
    if report.connector == "calendar.create":
        return ConnectorReport(
            status=report.status,
            connector="calendar.hold",
            detail=report.detail.replace("create", "hold") if "create" in report.detail else report.detail,
            url=report.url,
        )
    return report
