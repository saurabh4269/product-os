"""Conversation classifier — Type A / Type B from text.

Heuristic first so hosted / CI work without Gemini. Optional Gemini refine when
GOOGLE_API_KEY or Vertex ADC is present.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from loop.models import LoopType, PathKind, RoomKind

Kind = Literal["bug", "feature", "security", "mixed"]

_BUG = re.compile(
    r"\b(hung|hang|crash|broken|error|timeout|fail(ed|ure)?|bug|stuck|"
    r"can't|cannot|won't|doesn't work|3ds|authorize|payment.*(fail|hang)|"
    r"sdk|regress)\b",
    re.I,
)
_FEATURE = re.compile(
    r"\b(wish|want|would love|apple pay|faster|unclear|confusing|"
    r"add|please support|missing|should show|delivery date|onboarding|"
    r"improve|better|feature)\b",
    re.I,
)
_SECURITY = re.compile(
    r"\b(exfil|leak|pii|ssn|password|credential|dump customers?|"
    r"unauthorized|breach)\b",
    re.I,
)


def classify_voice(text: str) -> dict[str, Any]:
    """Return loop/path/room kind + labels for customer voice or call transcript."""
    clipped = (text or "").strip()
    bug = bool(_BUG.search(clipped))
    feat = bool(_FEATURE.search(clipped))
    sec = bool(_SECURITY.search(clipped))

    if sec:
        kind: Kind = "security"
        loop_type = LoopType.TYPE_A
        path = PathKind.SECURITY
        room_kind = RoomKind.REVIEW
        label = "Security concern"
    elif bug and not feat:
        kind = "bug"
        loop_type = LoopType.TYPE_A
        path = PathKind.BUG
        room_kind = RoomKind.INCIDENT
        label = "Something broke"
    elif feat and not bug:
        kind = "feature"
        loop_type = LoopType.TYPE_B
        path = PathKind.FEATURE
        room_kind = RoomKind.OPPORTUNITY
        label = "Could be better"
    elif bug and feat:
        kind = "mixed"
        loop_type = LoopType.TYPE_A
        path = PathKind.BUG
        room_kind = RoomKind.INCIDENT
        label = "Broken path (also wants improvements)"
    else:
        kind = "feature"
        loop_type = LoopType.TYPE_B
        path = PathKind.FEATURE
        room_kind = RoomKind.RESEARCH
        label = "Customer voice"

    return {
        "kind": kind,
        "label": label,
        "loop_type": loop_type,
        "path": path,
        "room_kind": room_kind,
        "confidence": 0.72 if bug or feat or sec else 0.45,
    }


def classify_call_outcome(transcript: list[dict[str, str]]) -> dict[str, Any]:
    """Fold call turns into the same shape as classify_voice."""
    text = " ".join(f"{t.get('role', '')}: {t.get('message', '')}" for t in transcript)
    out = classify_voice(text)
    interested = bool(re.search(r"\b(yes|sure|send|interested|please)\b", text, re.I))
    declined = bool(re.search(r"\b(no|not interested|busy|stop)\b", text, re.I))
    out["interested"] = interested and not declined
    out["declined"] = declined
    out["transcript_chars"] = len(text)
    return out
