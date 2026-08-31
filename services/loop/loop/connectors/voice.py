"""Outbound call connector — Twilio + Gemini (GCP credits / free trial)."""

from __future__ import annotations

from typing import Any

from loop.telephony import place_call as _place
from loop.tenant import ConnectorReport


def place_call(
    tokenized_user: str,
    reason: str,
    *,
    to_number: str = "",
    room_id: str = "",
    product: str = "",
    brief: dict[str, Any] | None = None,
    system_prompt: str = "",
) -> ConnectorReport:
    if not to_number:
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail="No phone number — ask the customer for a callback number first",
        )
    return _place(
        to_number=to_number,
        reason=reason,
        room_id=room_id,
        product=product,
        tokenized_user=tokenized_user,
        brief=brief,
        system_prompt=system_prompt,
    )
