"""Collect openable workflow links (Calendar, Meet, Gmail drafts, GitHub PRs)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


def _calendar_template_url(title: str, start: str, end: str) -> str:
    """Prefilled Google Calendar compose — works without API create."""
    def compact(iso: str) -> str:
        raw = (iso or "").replace("-", "").replace(":", "")
        if raw.endswith("Z"):
            raw = raw[:-1] + "Z"
        return raw.replace("+00:00", "Z").replace(".000", "")[:15] + "Z"

    s = compact(start)
    e = compact(end) if end else s
    text = quote(title or "Product OS review")
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={text}&dates={s}/{e}"


def collect_workflow_links(engine: Any) -> dict[str, Any]:
    from loop.connectors import calendar as cal
    from loop.connectors import google_oauth

    oauth = google_oauth.status()
    links: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(
        kind: str,
        label: str,
        url: str,
        *,
        room_id: str | None = None,
        detail: str = "",
        simulated: bool = False,
    ) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        links.append(
            {
                "kind": kind,
                "label": label,
                "url": url,
                "room_id": room_id,
                "detail": detail,
                "simulated": simulated,
            }
        )

    for act in engine.store.list_actions():
        arts = act.artifacts or {}
        exe = arts.get("execution") if isinstance(arts.get("execution"), dict) else {}
        pr = (exe or {}).get("pr_url") or (exe or {}).get("code_pr_url")
        if not pr and isinstance(arts.get("pr"), dict):
            pr = arts["pr"].get("url")
        if pr:
            add("github", f"Pull request · {act.type}", str(pr), detail=act.consequence or "")

    for room in engine.store.list_rooms():
        for msg in reversed(engine.store.list_messages(room.id)):
            if msg.artifact_type != "coordination":
                continue
            art = msg.artifact or {}
            title = str(art.get("kind") or room.title or "Review")
            slot = art.get("slot") if isinstance(art.get("slot"), dict) else {}
            if slot.get("event_url"):
                url = str(slot["event_url"])
                is_meet = "meet.google" in url
                add(
                    "meet" if is_meet else "calendar",
                    f"{'Meet' if is_meet else 'Calendar'} · {room.title[:48]}",
                    url,
                    room_id=room.id,
                    detail=str(slot.get("start") or "")[:16].replace("T", " "),
                )
            elif slot.get("start"):
                url = _calendar_template_url(title, str(slot["start"]), str(slot.get("end") or ""))
                add(
                    "calendar",
                    f"Suggested hold · {room.title[:40]}",
                    url,
                    room_id=room.id,
                    detail="Open in Google Calendar (compose)",
                    simulated=True,
                )
            gmail_url = art.get("gmail_url")
            if gmail_url:
                add(
                    "gmail",
                    f"Gmail draft · {room.title[:40]}",
                    str(gmail_url),
                    room_id=room.id,
                    detail="Draft only — send denied",
                )

    for mem in engine.store.list_memory(kind="coordination"):
        slot = mem.get("slot") if isinstance(mem.get("slot"), dict) else {}
        if slot.get("event_url"):
            url = str(slot["event_url"])
            is_meet = "meet.google" in url
            add(
                "meet" if is_meet else "calendar",
                f"{'Meet' if is_meet else 'Calendar'} · coordination",
                url,
                detail=str(slot.get("start") or "")[:16],
            )

    shortcuts: list[dict[str, str]] = [
        {"kind": "calendar", "label": "Google Calendar", "url": "https://calendar.google.com/"},
        {"kind": "gmail", "label": "Gmail drafts", "url": "https://mail.google.com/mail/#drafts"},
        {"kind": "meet", "label": "Google Meet", "url": "https://meet.google.com/"},
    ]

    return {
        "oauth": {
            "connected": bool(oauth.get("connected")),
            "email": oauth.get("email") or "",
            "authorize_path": oauth.get("authorize_path") or "/api/oauth/google/start",
        },
        "calendar": cal.capabilities(),
        "links": links[:40],
        "shortcuts": shortcuts,
        "workflows_href": "/labs/architecture?tab=fleet",
    }
