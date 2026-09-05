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

# In-memory active call sessions — mirrored to LOOP_DATA_DIR for min-instances>1 recovery.
_SESSIONS: dict[str, dict[str, Any]] = {}


def _sessions_path() -> str:
    base = (os.environ.get("LOOP_DATA_DIR") or "/tmp").rstrip("/")
    return f"{base}/call_sessions.json"


def _load_sessions() -> None:
    global _SESSIONS
    path = _sessions_path()
    if not os.path.isfile(path):
        return
    try:
        import json

        raw = json.loads(open(path, encoding="utf-8").read())
        if isinstance(raw, dict):
            _SESSIONS.update(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        pass


def _persist_sessions() -> None:
    try:
        import json

        with open(_sessions_path(), "w", encoding="utf-8") as fh:
            json.dump(_SESSIONS, fh)
    except OSError:
        pass


_load_sessions()


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
    """Normalize to E.164. Accepts US shorthand and international +[10-15 digits]."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if raw.startswith("+") and 10 <= len(digits) <= 15:
        return f"+{digits}"
    # Bare international digits without + (e.g. 919508709729 for India)
    if not raw.startswith("+") and 10 <= len(digits) <= 15:
        return f"+{digits}"
    return None


def _public_base() -> str:
    return (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")


def get_session(call_sid: str) -> dict[str, Any] | None:
    return _SESSIONS.get(call_sid)


def put_session(call_sid: str, data: dict[str, Any]) -> None:
    _SESSIONS[call_sid] = data
    _persist_sessions()


def _generic_gemini_fallback() -> str:
    return (
        "Thanks for taking the call. Can you walk me through what happened on your side — "
        "what you saw on screen and whether you tried again?"
    )


def _gemini_gather_timeout() -> float:
    return float(os.environ.get("LOOP_LEXI_GEMINI_TIMEOUT") or "4")


def _gemini_reply(system: str, user: str, history: list[dict[str, str]], *, brief: dict[str, Any] | None = None) -> str | None:
    """Short spoken reply via Gemini. Returns None when Gemini is unavailable or fails."""
    from loop.outreach import LEXI_SPOKEN_SAFETY_RULES
    from loop.vertex_gemini import gemini_configured, generate_content

    if not gemini_configured():
        return None
    blob = f"System: {system}\n\nCall brief context:\n"
    if brief:
        for key in ("metric", "signal_title", "voice_reason", "hypothesis", "purpose", "product"):
            val = brief.get(key)
            if val:
                blob += f"- {key}: {val}\n"
    blob += "\nConversation so far:\n"
    for turn in history[-8:]:
        blob += f"{turn.get('role', 'user')}: {turn.get('message', '')}\n"
    blob += (
        f"\nCustomer just said: {user}\n"
        "Reply as Lexi in under 40 spoken words. No markdown. "
        "Never ask for passwords, OTP codes, credit cards, SSN, or credentials. "
        "Never mention ML servers, Vertex, Gemini, API errors, or infrastructure. "
        f"{LEXI_SPOKEN_SAFETY_RULES} "
        "Never invent a specific failure mode that is not in the brief context. "
        "If evidence is thin, ask an open diagnostic question."
    )
    try:
        text = generate_content(blob, timeout=_gemini_gather_timeout()).strip()
        return text or None
    except Exception:
        return None


TWILIO_VOICE = "alice"
GATHER_TIMEOUT = "8"
GENERIC_LISTEN_PROMPT = "After the tone, tell me what you saw on your side."
LISTEN_PROMPT = GENERIC_LISTEN_PROMPT


def opening_line(reason: str, product: str = "your product") -> str:
    r = (reason or "a checkout problem").strip()[:200]
    product = product or "your product"
    return (
        f"Hi, this is Lexi from the {product} team. "
        f"We noticed {r}, and I am calling to learn what happened on your side. "
        "Do you have about thirty seconds?"
    )


def fix_notify_opening(product: str = "your product", fix_summary: str = "") -> str:
    product = product or "your product"
    fix = (fix_summary or "a recent issue").strip()[:180]
    return (
        f"Hi, this is Lexi from the {product} team. "
        f"We shipped a fix for {fix}. "
        "I wanted to check in and hear what you experienced."
    )


def _safe_spoken_line(text: str, *, fallback: str | None = None) -> str:
    from loop.outreach import prepare_spoken_line

    cleaned = prepare_spoken_line(text)
    if cleaned:
        return cleaned
    return fallback or _generic_gemini_fallback()


def _brief_opening(brief: dict[str, Any] | None, reason: str, product: str) -> str:
    b = brief or {}
    opening = b.get("opening") or ((b.get("call_plan") or {}).get("opening"))
    if opening:
        cleaned = _safe_spoken_line(str(opening), fallback="")
        if cleaned:
            return cleaned
    if b.get("purpose") == "fix_notify":
        return _safe_spoken_line(fix_notify_opening(product, str(b.get("fix_summary") or "")))
    return _safe_spoken_line(opening_line(reason, product or "your product"))


def _brief_listen_prompt(brief: dict[str, Any] | None) -> str:
    b = brief or {}
    listen = b.get("listen_prompt") or ((b.get("call_plan") or {}).get("listen_prompt"))
    if listen:
        return _safe_spoken_line(str(listen), fallback=LISTEN_PROMPT)
    return LISTEN_PROMPT


def _brief_questions(brief: dict[str, Any] | None) -> list[str]:
    b = brief or {}
    qs = b.get("questions") or ((b.get("call_plan") or {}).get("questions")) or []
    out: list[str] = []
    for q in qs:
        cleaned = _safe_spoken_line(str(q), fallback="")
        if cleaned:
            out.append(cleaned)
    return out


def _gather_reply(
    *,
    turns: int,
    scripted: list[str],
    system: str,
    speech: str,
    history: list[dict[str, str]],
    brief: dict[str, Any],
) -> str:
    """Scripted plan first (fast), then short-timeout Gemini, always rails-safe."""
    idx = turns - 1
    if idx < len(scripted):
        reply = _safe_spoken_line(scripted[idx])
        if reply:
            return reply
    reply = _gemini_reply(
        system=system,
        user=speech or "(silence)",
        history=history,
        brief=brief if isinstance(brief, dict) else None,
    )
    if reply:
        safe = _safe_spoken_line(reply, fallback="")
        if safe:
            return safe
    return _generic_gemini_fallback()


def _twiml_gather_loop(reply: str, listen: str, action: str) -> str:
    voice = TWILIO_VOICE
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}">{xml.escape(reply)}</Say>
  <Gather input="speech" speechTimeout="auto" timeout="{GATHER_TIMEOUT}" action="{xml.escape(action)}" method="POST">
    <Say voice="{voice}">{xml.escape(listen)}</Say>
  </Gather>
  <Say voice="{voice}">Thanks again for your time. Goodbye.</Say>
  <Hangup/>
</Response>
"""


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
            detail=f"Invalid phone number (need E.164, e.g. +919508709729): {to_number}",
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
            # Trial accounts: keep params minimal — Url, To, From, optional StatusCallback.
            data: dict[str, str] = {
                "To": e164,
                "From": frm,
                "Url": voice_url,
            }
            if status_url:
                data["StatusCallback"] = status_url
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
            "scripted_questions": _brief_questions(brief),
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
    b = brief or {}
    opening = _brief_opening(b, reason, product or "your product")
    say = xml.escape(opening)
    listen = xml.escape(_brief_listen_prompt(b))
    base = _public_base()
    action = f"{base}/api/twilio/gather?{urlencode({'room': room})}"
    voice = TWILIO_VOICE
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}">{say}</Say>
  <Gather input="speech" speechTimeout="auto" timeout="{GATHER_TIMEOUT}" action="{xml.escape(action)}" method="POST">
    <Say voice="{voice}">{listen}</Say>
  </Gather>
  <Say voice="{voice}">I did not catch that. We will follow up by email. Goodbye.</Say>
  <Hangup/>
</Response>
"""


def twiml_gather(call_sid: str, speech: str, room: str) -> str:
    """Always return valid TwiML quickly — never dead air on Gemini/infra failures."""
    try:
        return _twiml_gather_inner(call_sid, speech, room)
    except Exception:
        voice = TWILIO_VOICE
        fallback = xml.escape(_generic_gemini_fallback())
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="{voice}">{fallback}</Say><Hangup/></Response>
"""


def _twiml_gather_inner(call_sid: str, speech: str, room: str) -> str:
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
        bye = xml.escape(
            "Thank you so much for sharing that with us. "
            "We will use your feedback to make sure this stays fixed. Goodbye."
        )
        voice = TWILIO_VOICE
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="{voice}">{bye}</Say><Hangup/></Response>
"""

    scripted = list(sess.get("scripted_questions") or [])
    brief = sess.get("brief") or {}
    if not isinstance(brief, dict):
        brief = {}
    system = sess.get("system_prompt") or call_system_prompt(brief)
    reply = _gather_reply(
        turns=turns,
        scripted=scripted,
        system=system,
        speech=speech,
        history=list(sess.get("transcript") or []),
        brief=brief,
    )
    sess.setdefault("transcript", []).append({"role": "agent", "message": reply})
    put_session(call_sid, sess)

    base = _public_base()
    action = f"{base}/api/twilio/gather?{urlencode({'room': room or sess.get('room_id') or ''})}"
    listen = _brief_listen_prompt(brief) if turns < 3 else "Anything else before I let you go?"
    return _twiml_gather_loop(reply, listen, action)


def _metric_for_session(sess: dict[str, Any]) -> str:
    metric = str(sess.get("metric") or "")
    if metric:
        return metric
    room_id = sess.get("room_id")
    if not room_id:
        return ""
    try:
        from loop.api import get_engine

        eng = get_engine()
        room = eng.store.get_room(str(room_id))
        if not room or not room.investigation_id:
            return ""
        inv = eng.store.get_investigation(room.investigation_id)
        if not inv:
            return ""
        scenario = str(inv.scenario_id or "")
        if scenario.startswith("t:") and scenario.count(":") >= 2:
            return scenario.split(":", 2)[2]
        title = str(inv.title or "")
        if ":" in title:
            return title.split(":", 1)[-1].strip()
    except Exception:
        return ""
    return ""


def finalize_call(call_sid: str, status: str = "completed") -> dict[str, Any]:
    from loop.abandon_research import extract_structured_evidence

    sess = get_session(call_sid)
    if not sess:
        return {"ok": False, "reason": "unknown call"}
    sess["status"] = "done" if status == "completed" else status
    transcript = list(sess.get("transcript") or [])
    outcome = classify_call_outcome(transcript)
    structured = extract_structured_evidence(transcript, metric=_metric_for_session(sess))
    sess["outcome"] = outcome
    sess["structured"] = structured
    put_session(call_sid, sess)
    return {"ok": True, "session": sess, "outcome": outcome, "structured": structured}
