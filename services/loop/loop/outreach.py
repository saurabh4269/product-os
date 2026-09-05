"""Mail-first customer outreach ladder — never spam-call.

Flow:
  1. Investigation agents gather evidence.
  2. If a few users share the same pattern → friendly feedback emails.
  3. Wait for replies.
  4. Only non-responders may be called (feedback ask, or fix-notify if mail replies already solved it).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from loop.connectors import mail as mail_connector
from loop.customer_contact import (
    pattern_key_from_event,
    resolve_customer_contact,
    upsert_registration,
    users_matching_pattern,
)
from loop.proof import mail_proof
from loop.telephony import normalize_e164

# Defaults — read live from env inside helpers so tests can override.


def _mail_wait_hours() -> float:
    return float(os.environ.get("LOOP_OUTREACH_MAIL_WAIT_HOURS") or "24")


def _min_cluster() -> int:
    return int(os.environ.get("LOOP_OUTREACH_MIN_CLUSTER") or "2")


def _max_mails() -> int:
    return int(os.environ.get("LOOP_OUTREACH_MAX_MAILS") or "5")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def friendly_feedback_email(*, product: str, pattern: str, hypothesis: str = "") -> tuple[str, str]:
    """User-friendly ask — short, no jargon, no spam tone."""
    product = product or "our product"
    subject = f"Quick question about {product}"
    body = (
        "Hi,\n\n"
        "We noticed a few people hit a snag recently"
        + (f" ({pattern.split('|')[0]})" if pattern and pattern != "unknown_pattern" else "")
        + f" in {product}.\n\n"
        f"If you have 30 seconds, reply to this email with what you saw — "
        f"a screenshot or one sentence is plenty. It helps us fix the right thing.\n\n"
    )
    if hypothesis:
        body += "(We're already looking into it on our side.)\n\n"
    body += "Thanks — we won't spam you, and we only follow up if we still need a quick clarification.\n"
    return subject, body


def friendly_fix_notify_email(*, product: str, summary: str = "") -> tuple[str, str]:
    product = product or "our product"
    subject = f"We fixed something in {product}"
    body = (
        "Hi,\n\n"
        "Thanks for the feedback earlier. We shipped a fix"
        + (f": {summary}" if summary else " for the issue you ran into")
        + ".\n\n"
        f"If anything still feels off, just reply to this email.\n\n"
        f"— {product} team\n"
    )
    return subject, body


def call_brief_for_outreach(row: dict[str, Any], *, fix_summary: str = "") -> dict[str, Any]:
    """Purpose for the call: feedback ask vs fix notify."""
    purpose = str(row.get("call_purpose") or row.get("purpose") or "feedback_ask")
    if purpose == "fix_notify" or fix_summary:
        return {
            "purpose": "fix_notify",
            "opening": (
                "Hi — quick call from support. We fixed the issue you reported earlier. "
                "Just confirming you're unblocked now?"
            ),
            "questions": [
                "Are you able to complete the flow that was broken before?",
                "Anything still stuck?",
            ],
            "fix_summary": fix_summary or row.get("fix_summary") or "",
        }
    return {
        "purpose": "feedback_ask",
        "opening": (
            "Hi — we emailed about a problem a few people hit and didn't hear back. "
            "Thirty seconds to tell us what you saw?"
        ),
        "questions": [
            "What happened on your screen?",
            "Did you see an error, or did it keep loading?",
            "Have you tried again since?",
        ],
    }


def _send_or_draft_feedback(to: str, subject: str, body: str) -> dict[str, Any]:
    """Draft to the customer (human can send). Simulate when no OAuth — never silent fake success."""
    mode = (os.environ.get("LOOP_CUSTOMER_MAIL_MODE") or "draft").strip().lower()
    from loop.connectors.google_oauth import access_token

    if mode == "simulate" or not access_token():
        return {
            "status": "queued",
            "connector": "mail.customer_feedback",
            "detail": "Feedback email queued (no Workspace OAuth — simulated for demo).",
            "url": None,
            "simulated": True,
        }
    # Prefer draft addressed to the customer — operator reviews before send (anti-spam).
    report = mail_connector.draft(to, subject, body)
    return {
        "status": "drafted" if report.status == "applied" else report.status,
        "connector": report.connector,
        "detail": report.detail,
        "url": report.url,
        "simulated": False,
    }


def start_mail_ladder(
    engine: Any,
    *,
    room: Any,
    inv: Any,
    event: Any | None = None,
    hypothesis: str = "",
    product: str = "",
) -> dict[str, Any]:
    """After evidence: cluster similar users and queue friendly feedback mails — no calls yet."""
    from loop.world import post

    dims = {}
    metric = ""
    funnel = ""
    if event is not None:
        dims = event.dimensions if isinstance(getattr(event, "dimensions", None), dict) else {}
        metric = str(getattr(event, "metric", "") or "")
        funnel = str(getattr(event, "funnel_position", "") or "")
        if not hypothesis:
            hypothesis = str((dims.get("hypothesis") or {}).get("statement") or "")

    pattern = pattern_key_from_event(
        metric=metric,
        funnel_position=funnel,
        hypothesis=hypothesis,
        dimensions=dims,
    )
    tenant_id = getattr(room, "tenant_id", None) or (getattr(inv, "tenant_id", None) if inv else None)
    cohort = users_matching_pattern(engine.store, pattern, tenant_id=tenant_id, limit=_max_mails())

    # Always include room-resolved contact if we have an email on the investigation subject.
    room_contact = resolve_customer_contact(engine.store, room_id=room.id)
    if room_contact.get("email") and room_contact.get("tokenized_user"):
        tok = str(room_contact["tokenized_user"])
        if not any(str(u.get("tokenized_user")) == tok for u in cohort):
            cohort = [
                {
                    "tokenized_user": tok,
                    "email": room_contact["email"],
                    "phone": room_contact.get("phone"),
                    "consent_email": room_contact.get("consent_email", True),
                    "consent_voice": room_contact.get("consent_voice", True),
                    "tenant_id": tenant_id,
                },
                *cohort,
            ]

    # Seed from voice_subject if registration email was attached on the event.
    voice = dims.get("voice_subject") if isinstance(dims.get("voice_subject"), dict) else {}
    if voice.get("email") and voice.get("user_id"):
        upsert_registration(
            engine.store,
            tokenized_user=str(voice.get("user_id")),
            tenant_id=str(tenant_id or ""),
            email=str(voice["email"]),
            phone=str(voice.get("phone") or ""),
            meta={"pattern": pattern},
        )
        tok = str(voice["user_id"])
        if not any(str(u.get("tokenized_user")) == tok for u in cohort):
            cohort.insert(
                0,
                {
                    "tokenized_user": tok,
                    "email": str(voice["email"]),
                    "phone": voice.get("phone"),
                    "consent_email": True,
                    "tenant_id": tenant_id,
                },
            )

    contact_tok = str(voice.get("user_id") or "") if voice else ""
    if not contact_tok and cohort:
        contact_tok = str(cohort[0].get("tokenized_user") or "")
    lookup = resolve_customer_contact(engine.store, room_id=room.id, tokenized_user=contact_tok)
    if not lookup.get("found") and cohort:
        first = cohort[0]
        if first.get("email") or first.get("phone"):
            lookup = {
                **first,
                "found": True,
                "tokenized_user": first.get("tokenized_user"),
                "detail": "Cohort contact from registration.",
            }
    if lookup.get("email") or lookup.get("phone"):
        phone = lookup.get("phone")
        email = lookup.get("email")
        post(
            engine,
            room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="chat",
            text=(
                "Looked up customer contact in memory."
                + (f" Callback number is {phone}." if phone else "")
                + (f" Email on file: {email}." if email else "")
            ),
            artifact_type="contact_lookup",
            artifact={**lookup, "found": True},
        )

    cluster_id = _id("cluster")
    cluster_art = {
        "cluster_id": cluster_id,
        "pattern": pattern,
        "users": [
            {
                "tokenized_user": u.get("tokenized_user"),
                "has_email": bool(u.get("email")),
                "has_phone": bool(u.get("phone")),
            }
            for u in cohort
        ],
        "min_cluster": _min_cluster(),
        "enough": len([u for u in cohort if u.get("email")]) >= _min_cluster()
        or (len(cohort) >= 1 and bool(room_contact.get("email"))),
    }

    post(
        engine,
        room.id,
        author="customer_voice_agent",
        author_kind="agent",
        kind="artifact",
        text=(
            f"Similar-pattern cohort: {len(cohort)} user(s) for `{pattern or 'pattern'}`. "
            + (
                "Sending friendly feedback emails first — no calls yet."
                if cluster_art["enough"]
                else "Not enough similar users with email yet; holding outreach."
            )
        ),
        artifact_type="user_cluster",
        artifact=cluster_art,
    )

    mailed: list[dict[str, Any]] = []
    if not cluster_art["enough"]:
        return {"cluster": cluster_art, "mailed": mailed, "calls": [], "held": True}

    product_name = product or ""
    if not product_name and tenant_id:
        t = engine.store.get_tenant(tenant_id)
        product_name = (t.product if t else "") or ""

    subject, body = friendly_feedback_email(product=product_name, pattern=pattern, hypothesis=hypothesis)
    for user in cohort[: _max_mails()]:
        email = str(user.get("email") or "").strip()
        tok = str(user.get("tokenized_user") or "")
        if not email or not tok:
            continue
        if user.get("consent_email") is False:
            continue
        # Idempotent: one feedback mail per investigation+user
        existing = [
            o
            for o in engine.store.list_outreach(investigation_id=getattr(inv, "id", "") or "")
            if o.get("tokenized_user") == tok and o.get("channel") == "email"
        ]
        if existing:
            mailed.append(existing[0])
            continue

        report = _send_or_draft_feedback(email, subject, body)
        row = {
            "id": _id("out"),
            "investigation_id": getattr(inv, "id", None),
            "room_id": room.id,
            "tokenized_user": tok,
            "channel": "email",
            "purpose": "feedback_ask",
            "status": report["status"] if report["status"] in {"queued", "drafted", "applied", "sent"} else "queued",
            "cluster_id": cluster_id,
            "pattern": pattern,
            "email": email,
            "phone": user.get("phone"),
            "idempotency_key": f"{getattr(inv, 'id', '')}:{tok}:email_feedback",
            "payload": {"subject": subject, "report": report},
            "created_at": _now().isoformat(),
            "sent_at": _now().isoformat(),
            "replied_at": None,
            "reply_summary": None,
        }
        if report["status"] in {"denied", "skipped"} and not report.get("simulated"):
            row["status"] = "skipped"
            row["payload"]["report"] = report
        engine.store.put_outreach(row)
        # Tag identity with pattern for future clustering
        upsert_registration(
            engine.store,
            tokenized_user=tok,
            tenant_id=str(tenant_id or ""),
            email=email,
            phone=str(user.get("phone") or ""),
            meta={"pattern": pattern, "last_outreach": row["id"]},
        )
        post(
            engine,
            room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text=f"Feedback email to {email}: {report.get('detail') or row['status']}",
            artifact_type="mail_outreach",
            artifact={
                **row,
                "subject": subject,
                "to": email,
                "gmail_url": report.get("url"),
                "channel": report.get("connector") or row.get("status"),
                "report": report,
                "proof": mail_proof(
                    {
                        "subject": subject,
                        "to": email,
                        "gmail_url": report.get("url"),
                        "channel": report.get("connector") or "gmail",
                        "report": report,
                    }
                ),
            },
        )
        mailed.append(row)

    return {"cluster": cluster_art, "mailed": mailed, "calls": [], "held": False}


def record_mail_reply(
    store: Any,
    *,
    tokenized_user: str,
    investigation_id: str = "",
    room_id: str = "",
    summary: str = "",
    solved: bool = False,
) -> dict[str, Any] | None:
    """Mark the latest feedback mail as replied (from Product Y / inbound)."""
    rows = store.list_outreach(investigation_id=investigation_id or None, room_id=room_id or None)
    rows = [
        r
        for r in rows
        if r.get("tokenized_user") == tokenized_user and r.get("channel") == "email"
    ]
    if not rows:
        return None
    row = rows[-1]
    row["status"] = "replied"
    row["replied_at"] = _now().isoformat()
    row["reply_summary"] = summary[:500] if summary else row.get("reply_summary")
    if solved:
        row["solved"] = True
    store.put_outreach(row)
    return row


def advance_outreach(
    engine: Any,
    *,
    room_id: str,
    force_call: bool = False,
    fix_summary: str = "",
) -> dict[str, Any]:
    """Call only non-responders after the mail wait — or notify fix if mail already solved it."""
    from loop.connectors import voice as voice_connector
    from loop.world import post

    room = engine.store.get_room(room_id)
    if not room:
        return {"ok": False, "detail": "room not found", "calls": []}

    inv_id = room.investigation_id or ""
    rows = engine.store.list_outreach(investigation_id=inv_id) if inv_id else engine.store.list_outreach(room_id=room_id)
    email_rows = [r for r in rows if r.get("channel") == "email"]
    wait = timedelta(hours=_mail_wait_hours())
    now = _now()

    # If any mail reply solved the issue, prefer fix-notify calls only to non-responders
    # and skip feedback-ask spam.
    any_solved = any(r.get("solved") or (r.get("status") == "replied" and r.get("solved")) for r in email_rows)
    replies = [r for r in email_rows if r.get("status") == "replied"]
    if replies and not fix_summary:
        fix_summary = str(replies[0].get("reply_summary") or "")[:200]

    calls: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in email_rows:
        tok = str(row.get("tokenized_user") or "")
        if row.get("status") == "replied":
            skipped.append({"tokenized_user": tok, "reason": "replied_to_mail"})
            continue
        if row.get("status") in {"skipped", "denied"}:
            skipped.append({"tokenized_user": tok, "reason": row["status"]})
            continue

        sent_at = _parse_ts(row.get("sent_at") or row.get("created_at"))
        if not force_call and sent_at and now < sent_at + wait:
            skipped.append({"tokenized_user": tok, "reason": "waiting_for_mail_reply", "until": (sent_at + wait).isoformat()})
            continue

        # Already called?
        prior_calls = [
            r
            for r in rows
            if r.get("tokenized_user") == tok and r.get("channel") == "voice"
        ]
        if prior_calls:
            skipped.append({"tokenized_user": tok, "reason": "already_called"})
            continue

        ident = engine.store.get_customer_identity(tok) or {}
        phone = normalize_e164(str(ident.get("phone") or row.get("phone") or "")) or str(
            row.get("phone") or ident.get("phone") or ""
        )
        if not phone:
            skipped.append({"tokenized_user": tok, "reason": "no_phone"})
            continue
        if ident.get("consent_voice") is False:
            skipped.append({"tokenized_user": tok, "reason": "no_voice_consent"})
            continue

        purpose = "fix_notify" if (any_solved or fix_summary) else "feedback_ask"
        brief = call_brief_for_outreach({**row, "call_purpose": purpose}, fix_summary=fix_summary)
        report = voice_connector.place_call(
            tok,
            reason=str(row.get("pattern") or "follow_up"),
            to_number=phone,
            room_id=room_id,
            product="",
            brief=brief,
            system_prompt="",
        )
        call_row = {
            "id": _id("out"),
            "investigation_id": inv_id,
            "room_id": room_id,
            "tokenized_user": tok,
            "channel": "voice",
            "purpose": purpose,
            "status": "called" if report.status == "applied" else report.status,
            "cluster_id": row.get("cluster_id"),
            "pattern": row.get("pattern"),
            "phone": phone,
            "email": row.get("email"),
            "idempotency_key": f"{inv_id}:{tok}:voice_{purpose}",
            "payload": {"brief": brief, "report": report.model_dump() if hasattr(report, "model_dump") else dict(report)},
            "created_at": now.isoformat(),
            "parent_outreach_id": row["id"],
        }
        engine.store.put_outreach(call_row)
        post(
            engine,
            room_id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text=(
                f"{'Fix-notify' if purpose == 'fix_notify' else 'Follow-up'} call to {phone} "
                f"(no reply to mail). {getattr(report, 'detail', '')}"
            ),
            artifact_type="call",
            artifact=call_row,
        )
        calls.append(call_row)

    return {
        "ok": True,
        "calls": calls,
        "skipped": skipped,
        "mail_wait_hours": _mail_wait_hours(),
        "fix_summary": fix_summary or None,
    }


def gate_place_call(
    store: Any,
    *,
    room_id: str = "",
    tokenized_user: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Block spammy first-touch calls unless mail ladder progressed or human forces."""
    if force:
        return {"allowed": True, "reason": "human_override"}

    inv_id = ""
    if room_id:
        room = store.get_room(room_id)
        inv_id = (room.investigation_id if room else "") or ""

    rows = store.list_outreach(investigation_id=inv_id) if inv_id else []
    if room_id and not rows:
        rows = store.list_outreach(room_id=room_id)

    email_rows = [
        r
        for r in rows
        if r.get("channel") == "email"
        and (not tokenized_user or r.get("tokenized_user") == tokenized_user)
    ]
    if not email_rows:
        return {
            "allowed": False,
            "reason": "mail_first",
            "detail": "Email similar-pattern users first; call only non-responders after the wait.",
        }

    for row in email_rows:
        if row.get("status") == "replied":
            continue
        sent_at = _parse_ts(row.get("sent_at") or row.get("created_at"))
        if sent_at is None:
            return {"allowed": True, "reason": "mail_queued"}
        if _now() >= sent_at + timedelta(hours=_mail_wait_hours()):
            return {"allowed": True, "reason": "non_responder_after_mail"}

    # All replied — only fix-notify makes sense
    if email_rows and all(r.get("status") == "replied" for r in email_rows):
        return {
            "allowed": False,
            "reason": "all_replied",
            "detail": "Everyone replied by email — no cold call needed. Use fix-notify if you still want a confirm call.",
        }

    return {
        "allowed": False,
        "reason": "waiting_for_mail_reply",
        "detail": f"Wait {_mail_wait_hours():g}h after feedback mail before calling non-responders.",
    }
