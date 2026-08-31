"""Customer contact — identity (email at registration) + non-spammy resolve helpers.

Calls are never the first touch. See loop.outreach for the mail → wait → call ladder.
"""

from __future__ import annotations

import re
from typing import Any

from loop.store import Store
from loop.telephony import normalize_e164


def _phone_from_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    for key in ("phone", "callback_phone", "to_number", "mobile"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    meta = payload.get("meta")
    if isinstance(meta, dict):
        raw = meta.get("phone")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _email_from_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    for key in ("email", "user_email", "mail"):
        raw = payload.get(key)
        if isinstance(raw, str) and "@" in raw.strip():
            return raw.strip().lower()
    meta = payload.get("meta")
    if isinstance(meta, dict):
        raw = meta.get("email")
        if isinstance(raw, str) and "@" in raw.strip():
            return raw.strip().lower()
    return ""


def upsert_registration(
    store: Store,
    *,
    tokenized_user: str,
    tenant_id: str = "",
    email: str = "",
    phone: str = "",
    consent_email: bool = True,
    consent_voice: bool = True,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Product Y registration — capture email (and optional phone) once."""
    tok = (tokenized_user or "").strip() or "tok_anon"
    e164 = normalize_e164(phone) if phone else ""
    body: dict[str, Any] = {
        "tokenized_user": tok,
        "tenant_id": tenant_id or None,
        "consent_email": bool(consent_email),
        "consent_voice": bool(consent_voice),
    }
    if email and "@" in email:
        body["email"] = email.strip().lower()
    if e164 or phone:
        body["phone"] = e164 or phone.strip()
    if meta:
        body["meta"] = meta
    return store.put_customer_identity(body)


def resolve_callback_phone(store: Store, room_id: str = "") -> dict[str, Any]:
    """Find the best callback number for a room (Cove feedback → identity → memory)."""
    contact = resolve_customer_contact(store, room_id=room_id)
    if contact.get("phone"):
        return {
            "phone": contact["phone"],
            "found": True,
            "source": contact.get("phone_source") or contact.get("source"),
            "detail": contact.get("detail") or f"Found callback number {contact['phone']}.",
            "feedback": contact.get("feedback") or "",
            "raw": contact.get("raw"),
            "email": contact.get("email"),
            "tokenized_user": contact.get("tokenized_user"),
        }
    return {"phone": None, "found": False, "detail": "No callback number on file for this room."}


def resolve_customer_contact(store: Store, room_id: str = "", tokenized_user: str = "") -> dict[str, Any]:
    """Resolve email + phone for outreach (registration identity preferred)."""
    candidates: list[dict[str, Any]] = []

    if room_id:
        for msg in reversed(store.list_messages(room_id)):
            art = msg.artifact if isinstance(msg.artifact, dict) else {}
            phone = _phone_from_payload(art)
            email = _email_from_payload(art)
            tok = str(art.get("tokenized_user") or "")
            if not phone and not email and not tok:
                continue
            e164 = normalize_e164(phone) if phone else None
            candidates.append(
                {
                    "phone": e164,
                    "raw": phone or None,
                    "email": email or None,
                    "tokenized_user": tok or None,
                    "source": "room_message",
                    "message_id": msg.id,
                    "author": msg.author,
                    "text": (msg.text or "")[:240],
                }
            )

    for payload in reversed(store.list_memory(kind="customer")):
        phone = _phone_from_payload(payload)
        email = _email_from_payload(payload)
        tok = str(payload.get("tokenized_user") or "")
        if not phone and not email and not tok:
            continue
        e164 = normalize_e164(phone) if phone else None
        candidates.append(
            {
                "phone": e164,
                "raw": phone or None,
                "email": email or None,
                "tokenized_user": tok or None,
                "source": "memory",
                "text": str(payload.get("text") or "")[:240],
            }
        )

    tok_hint = (tokenized_user or "").strip()
    if not tok_hint:
        for c in candidates:
            if c.get("tokenized_user"):
                tok_hint = str(c["tokenized_user"])
                break

    identity = store.get_customer_identity(tok_hint) if tok_hint else None
    email = (identity or {}).get("email") if identity else None
    phone = (identity or {}).get("phone") if identity else None
    phone_source = "identity" if phone else None
    email_source = "identity" if email else None
    feedback = ""

    room_hits = [c for c in candidates if c["source"] == "room_message"]
    pool = room_hits or candidates
    if pool:
        pick = pool[0]
        feedback = str(pick.get("text") or "")
        if not phone and pick.get("phone"):
            phone = pick["phone"]
            phone_source = pick["source"]
        if not email and pick.get("email"):
            email = pick["email"]
            email_source = pick["source"]
        if not tok_hint and pick.get("tokenized_user"):
            tok_hint = str(pick["tokenized_user"])
            if not identity:
                identity = store.get_customer_identity(tok_hint)
                if identity:
                    email = email or identity.get("email")
                    phone = phone or identity.get("phone")

    if not email and not phone:
        return {
            "found": False,
            "email": None,
            "phone": None,
            "tokenized_user": tok_hint or None,
            "detail": "No email or phone on file. Capture email at Product Y registration.",
        }

    bits = []
    if email:
        bits.append(f"email {email}")
    if phone:
        bits.append(f"phone {phone}")
    return {
        "found": True,
        "email": email,
        "phone": phone,
        "email_source": email_source,
        "phone_source": phone_source,
        "source": email_source or phone_source,
        "tokenized_user": tok_hint or None,
        "consent_email": (identity or {}).get("consent_email", True) if identity else True,
        "consent_voice": (identity or {}).get("consent_voice", True) if identity else True,
        "detail": "Found " + " · ".join(bits) + ".",
        "feedback": feedback,
        "raw": phone,
    }


def feedback_summary_from_transcript(transcript: list[dict[str, Any]] | list[Any]) -> str:
    """Turn call turns into one short sentence for the room."""
    customer_bits: list[str] = []
    for turn in transcript or []:
        if isinstance(turn, dict):
            role = str(turn.get("role") or turn.get("speaker") or "")
            text = str(turn.get("text") or turn.get("speech") or "").strip()
        elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
            role, text = str(turn[0]), str(turn[1]).strip()
        else:
            continue
        if not text:
            continue
        if role.lower() in {"customer", "user", "human", "caller"}:
            customer_bits.append(text)
    if not customer_bits:
        return "Call finished. No customer speech captured."
    joined = " ".join(customer_bits)
    if len(joined) > 280:
        joined = joined[:277] + "…"
    return f"Customer said: {joined}"


def pattern_key_from_event(
    *,
    metric: str = "",
    funnel_position: str = "",
    failure: str = "",
    device: str = "",
    hypothesis: str = "",
    dimensions: dict[str, Any] | None = None,
) -> str:
    """Stable key for 'users showing a similar pattern' — not a fixture id."""
    dims = dimensions if isinstance(dimensions, dict) else {}
    voice = dims.get("voice_subject") if isinstance(dims.get("voice_subject"), dict) else {}
    segs = dims.get("segments") if isinstance(dims.get("segments"), dict) else {}
    fail = failure or str(voice.get("failure") or voice.get("reason") or "")
    dev = device or str(voice.get("device") or segs.get("browser") or segs.get("os") or "")
    parts = [
        (metric or str(dims.get("metric") or "")).strip().lower(),
        (funnel_position or "").strip().lower(),
        re.sub(r"\s+", " ", fail.strip().lower())[:80],
        re.sub(r"\s+", " ", dev.strip().lower())[:40],
    ]
    key = "|".join(p for p in parts if p)
    if not key and hypothesis:
        key = re.sub(r"\s+", " ", hypothesis.strip().lower())[:100]
    return key or "unknown_pattern"


def users_matching_pattern(store: Store, pattern: str, *, tenant_id: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Find registered / memory users that look like the same failure pattern."""
    if not pattern or pattern == "unknown_pattern":
        return []
    needle = pattern.lower()
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ident in store.list_customer_identities(tenant_id=tenant_id):
        tok = str(ident.get("tokenized_user") or "")
        if not tok or tok in seen:
            continue
        blob = json_blob(ident).lower()
        # Soft match: identity meta may carry last_failure / pattern
        meta = ident.get("meta") if isinstance(ident.get("meta"), dict) else {}
        ident_pattern = str(meta.get("pattern") or meta.get("last_failure") or "")
        if ident_pattern and (ident_pattern.lower() in needle or needle in ident_pattern.lower()):
            hits.append(ident)
            seen.add(tok)
            continue
        if needle.split("|")[0] and needle.split("|")[0] in blob:
            # Weak — only if they have email (registration)
            if ident.get("email"):
                hits.append(ident)
                seen.add(tok)

    for payload in store.list_memory(kind="customer", tenant_id=tenant_id):
        tok = str(payload.get("tokenized_user") or "")
        if not tok or tok in seen:
            continue
        text = str(payload.get("text") or "").lower()
        fail_bits = [p for p in needle.split("|") if p]
        if fail_bits and any(b in text for b in fail_bits if len(b) > 3):
            ident = store.get_customer_identity(tok) or {
                "tokenized_user": tok,
                "email": _email_from_payload(payload),
                "phone": _phone_from_payload(payload),
                "tenant_id": payload.get("tenant_id") or payload.get("tenant"),
            }
            if ident.get("email") or ident.get("phone"):
                hits.append(ident)
                seen.add(tok)
        if len(hits) >= limit:
            break

    return hits[:limit]


def json_blob(obj: dict[str, Any]) -> str:
    parts = [str(obj.get("email") or ""), str(obj.get("phone") or ""), str((obj.get("meta") or {}))]
    return " ".join(parts)
