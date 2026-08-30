"""Side effects that apply, skip honestly, or deny. Never fake a GitHub URL."""

from __future__ import annotations

from .calendar import hold as calendar_hold
from .github import create_issue, open_pr
from .mail import draft as mail_draft

__all__ = ["calendar_hold", "create_issue", "mail_draft", "open_pr"]
