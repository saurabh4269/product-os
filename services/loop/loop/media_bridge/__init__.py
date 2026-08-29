"""Media-bridge interface. Live API is mocked. Transcript screening is real (K-11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..engine import redact_pii, screen_tool_output


@dataclass
class BridgeSession:
    session_id: str
    resumption_handle: str
    opened_at: str
    turns: list[dict] = field(default_factory=list)
    screened: bool = False


class MediaBridge:
    """Twilio-shaped interface without a carrier. Transcode hooks are no-ops on mock PCM."""

    def __init__(self):
        self.sessions: dict[str, BridgeSession] = {}

    def open_session(self, session_id: str) -> BridgeSession:
        sess = BridgeSession(
            session_id=session_id,
            resumption_handle=f"resume_{session_id}",
            opened_at=datetime.now(timezone.utc).isoformat(),
        )
        self.sessions[session_id] = sess
        return sess

    def resume(self, handle: str) -> BridgeSession | None:
        for s in self.sessions.values():
            if s.resumption_handle == handle:
                return s
        return None

    def ingest_transcript_turn(self, session_id: str, role: str, text: str) -> dict:
        sess = self.sessions[session_id]
        if not text.strip():
            return {"blocked": True, "reason": "missing_transcription"}
        hit, needle = screen_tool_output(text)
        redacted = redact_pii(text)
        turn = {
            "role": role,
            "redacted": redacted,
            "blocked": hit,
            "needle": needle,
            "trust": "untrusted" if role == "customer" else "trusted",
        }
        sess.turns.append(turn)
        sess.screened = True
        return turn

    def transcode_in(self, _ulaw_8k: bytes) -> bytes:
        return b"PCM16_16KHZ_MOCK"

    def transcode_out(self, _pcm_24k: bytes) -> bytes:
        return b"ULAW_8KHZ_MOCK"
