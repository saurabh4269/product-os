"""Side effects that apply, skip honestly, or deny. Never fake a GitHub URL."""

from __future__ import annotations

from .calendar import (
    check_availability,
    create_event,
    list_events,
    suggest_times,
)
from .calendar import (
    hold as calendar_hold,
)
from .github import create_issue, open_pr
from .mail import draft as mail_draft
from .voice import place_call
from .warehouse import publish_signal

__all__ = [
    "calendar_hold",
    "check_availability",
    "create_event",
    "create_issue",
    "list_events",
    "mail_draft",
    "open_pr",
    "place_call",
    "publish_signal",
    "suggest_times",
]
