"""Outbound customer calls — Gemini brain + Twilio carrier (no ElevenLabs).

Cost path for this hackathon:
  - Gemini: GCP credits / AI Studio key (GOOGLE_API_KEY) — Cloud TTS not required;
    Twilio <Say> uses trial-included TTS.
  - PSTN: Twilio free trial (~$15 credit). Google has no free outbound PSTN for ADK.

Flow (Google-documented Twilio path):
  place_call → Twilio REST create call → TwiML Say/Gather loop →
  Gemini text replies → hangup → classify transcript → room artifact.
"""

from __future__ import annotations

import os
import re
import xml.sax.saxutils as xml
from typing import Any
from urllib.parse import urlencode

import httpx

from loop.classify import classify_call_outcome
from loop.tenant import ConnectorReport

# In-memory active call sessions (Cloud Run instance-local; fine for demo + min-instances 1).
_SESSIONS: dict[str, dict[str, Any]] = {}


def twilio_configured() -> bool:
    return bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_FROM_NUMBER")
    )


def gemini_configured() -> bool:
    from loop.vertex_gemini import gemini_configured as _cfg

    return _cfg() or bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))


def normalize_e164(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if phone.startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return None


def _public_base() -> str:
    return (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")


def get_session(call_sid: str) -> dict[str, Any] | None:
    return _SESSIONS.get(call_sid)


def put_session(call_sid: str, data: dict[str, Any]) -> None:
    _SESSIONS[call_sid] = data


def _gemini_reply(system: str, user: str, history: list[dict[str, str]]) -> str:
    """Short spoken reply. Falls back to a scripted line if Gemini unavailable."""
    from loop.vertex_gemini import gemini_configured, generate_content

    fallback = (
        "Thanks for taking the call. I am looking into what happened at checkout. "
        "Can you tell me whether the payment screen spun forever or showed an error?"
    )
    if not gemini_configured():
        return fallback
    blob = f"System: {system}\n\nConversation so far:\n"
    for turn in history[-8:]:
        blob += f"{turn.get('role', 'user')}: {turn.get('message', '')}\n"
    blob += f"\nCustomer just said: {user}\nReply in under 40 spoken words. No markdown."
    try:
        text = generate_content(blob, timeout=25.0).strip()
        return text or fallback
    except Exception:
        return fallback


def opening_line(reason: str, product: str = "your product") -> str:
    r = (reason or "a checkout problem").strip()[:200]
    return (
        f"Hi, this is Lexi from the {product} product team. "
        f"We saw {r}. Do you have thirty seconds to tell me what you saw on screen?"
    )


def place_call(
    *,
    to_number: str,
    reason: str,
    room_id: str = "",
    product: str = "",
    tokenized_user: str = "tok_anon",
    brief: dict[str, Any] | None = None,
    system_prompt: str = "",
) -> ConnectorReport:
    """Start an outbound PSTN call. Duplicate numbers within a room are skipped."""
    if not twilio_configured():
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail=(
                "Twilio not configured. Sign up for a free Twilio trial, set "
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER. "
                "Gemini replies use GOOGLE_API_KEY / GCP credits — no ElevenLabs."
            ),
        )
    base = _public_base()
    if not base:
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail="LOOP_PUBLIC_URL unset — Twilio cannot webhook back to Product OS",
        )
    e164 = normalize_e164(to_number)
    if not e164:
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail=f"Invalid US phone number: {to_number}",
        )

    # prevent_duplicate_call — same room + number already in flight or done recently
    for sid, sess in list(_SESSIONS.items()):
        if sess.get("room_id") == room_id and sess.get("to") == e164:
            if sess.get("status") in {"in-progress", "initiated", "done"}:
                return ConnectorReport(
                    status="reused",
                    connector="voice.place_call",
                    detail=f"Call already placed for {e164} in this room ({sid})",
                    url=sess.get("url"),
                )

    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    frm = os.environ["TWILIO_FROM_NUMBER"]
    voice_url = f"{base}/api/twilio/voice?{urlencode({'room': room_id, 'reason': reason[:180], 'product': product})}"
    status_url = f"{base}/api/twilio/status"

    try:
        with httpx.Client(timeout=30.0) as client:
            # Trial accounts may reject StatusCallbackEvent lists; StatusCallback alone is ok.
            data = {
                "To": e164,
                "From": frm,
                "Url": voice_url,
                "StatusCallback": status_url,
                "StatusCallbackMethod": "POST",
            }
            res = client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                auth=(sid, token),
                data=data,
            )
            if res.status_code >= 400:
                return ConnectorReport(
                    status="skipped",
                    connector="voice.place_call",
                    detail=f"Twilio error {res.status_code}: {res.text[:240]}",
                )
            payload = res.json()
    except Exception as exc:
        return ConnectorReport(
            status="skipped",
            connector="voice.place_call",
            detail=f"Twilio request failed: {exc}",
        )

    call_sid = str(payload.get("sid") or "")
    put_session(
        call_sid,
        {
            "to": e164,
            "room_id": room_id,
            "reason": reason,
            "product": product,
            "tokenized_user": tokenized_user,
            "status": "initiated",
            "turns": 0,
            "transcript": [],
            "brief": brief or {},
            "system_prompt": system_prompt,
            "scripted_questions": ((brief or {}).get("call_plan") or {}).get("questions") or [],
            "url": f"https://www.twilio.com/console/voice/calls/{call_sid}" if call_sid else None,
        },
    )
    return ConnectorReport(
        status="applied",
        connector="voice.place_call",
        detail=f"Outbound call started to {e164}",
        url=call_sid,
    )


def twiml_open(room: str, reason: str, product: str, brief: dict[str, Any] | None = None) -> str:
    from loop.abandon_research import build_customer_context_brief

    b = brief or build_customer_context_brief()
    opening = ((b.get("call_plan") or {}).get("opening")) or opening_line(reason, product or "your product")
    say = xml.escape(opening)
    base = _public_base()
    action = f"{base}/api/twilio/gather?{urlencode({'room': room})}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{say}</Say>
  <Gather input="speech" speechTimeout="auto" timeout="5" action="{xml.escape(action)}" method="POST">
    <Say voice="Polly.Joanna">I am listening.</Say>
  </Gather>
  <Say voice="Polly.Joanna">I did not catch that. We will follow up by email. Goodbye.</Say>
  <Hangup/>
</Response>
"""


def twiml_gather(call_sid: str, speech: str, room: str) -> str:
    from loop.abandon_research import call_system_prompt

    sess = get_session(call_sid) or {
        "transcript": [],
        "turns": 0,
        "reason": "checkout",
        "product": "your product",
        "room_id": room,
        "brief": {},
        "scripted_questions": [],
    }
    speech = (speech or "").strip()
    if speech:
        sess.setdefault("transcript", []).append({"role": "user", "message": speech})
    turns = int(sess.get("turns") or 0) + 1
    sess["turns"] = turns
    sess["status"] = "in-progress"

    if turns >= 4 or re.search(r"\b(bye|goodbye|hang up|stop)\b", speech, re.I):
        sess["status"] = "done"
        put_session(call_sid, sess)
        bye = xml.escape("Thanks for your time. We will take it from here. Goodbye.")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="Polly.Joanna">{bye}</Say><Hangup/></Response>
"""

    scripted = list(sess.get("scripted_questions") or [])
    # Prefer call-plan questions in order (targeted research), then Gemini
    if turns <= len(scripted):
        reply = scripted[turns - 1]
    else:
        system = sess.get("system_prompt") or call_system_prompt(sess.get("brief") or {})
        reply = _gemini_reply(
            system=system,
            user=speech or "(silence)",
            history=list(sess.get("transcript") or []),
        )
    sess.setdefault("transcript", []).append({"role": "agent", "message": reply})
    put_session(call_sid, sess)

    base = _public_base()
    action = f"{base}/api/twilio/gather?{urlencode({'room': room or sess.get('room_id') or ''})}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{xml.escape(reply)}</Say>
  <Gather input="speech" speechTimeout="auto" timeout="5" action="{xml.escape(action)}" method="POST">
    <Say voice="Polly.Joanna">Go ahead.</Say>
  </Gather>
  <Say voice="Polly.Joanna">Thanks again. Goodbye.</Say>
  <Hangup/>
</Response>
"""


def finalize_call(call_sid: str, status: str = "completed") -> dict[str, Any]:
    from loop.abandon_research import extract_structured_evidence

    sess = get_session(call_sid)
    if not sess:
        return {"ok": False, "reason": "unknown call"}
    sess["status"] = "done" if status == "completed" else status
    transcript = list(sess.get("transcript") or [])
    outcome = classify_call_outcome(transcript)
    structured = extract_structured_evidence(transcript)
    sess["outcome"] = outcome
    sess["structured"] = structured
    put_session(call_sid, sess)
    return {"ok": True, "session": sess, "outcome": outcome, "structured": structured}
