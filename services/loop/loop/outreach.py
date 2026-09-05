"""Mail-first customer outreach ladder — never spam-call.

Flow:
  1. Investigation agents gather evidence.
  2. If a few users share the same pattern → friendly feedback emails.
  3. Wait for replies.
  4. Only non-responders may be called (feedback ask, or fix-notify if mail replies already solved it).
"""

from __future__ import annotations

import json
import os
import re
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


_PLACEHOLDER_BRACKET = re.compile(r"\[[^\]]+\]")
_PLACEHOLDER_CURLY = re.compile(r"\{[^}]+\}")
_PLACEHOLDER_CUSTOMER_NAME = re.compile(r"\bCustomer Name\b", re.I)
_VAGUE_FEEDBACK_PHRASE = re.compile(r"feedback you shared", re.I)

# Never speak credential requests or infra failures to customers on PSTN.
_CREDENTIAL_ASK_PATTERNS = (
    re.compile(r"\binitial\s+password\b", re.I),
    re.compile(r"\b(your|the|an?)\s+password\b", re.I),
    re.compile(r"\bpassword\b.*\b(provide|share|give|tell|enter|confirm|need|verify)\b", re.I),
    re.compile(r"\b(provide|share|give|tell|enter|confirm|need|verify).*\bpassword\b", re.I),
    re.compile(r"\b(share|provide|give|tell|enter|confirm).*\b(otp|pin code|security code)\b", re.I),
    re.compile(r"\b(one.?time|verification)\s+(code|password)\b.*\b(share|provide|give|tell|enter)\b", re.I),
    re.compile(r"\bcredit\s+card\b", re.I),
    re.compile(r"\bcvv\b", re.I),
    re.compile(r"\bssn\b", re.I),
    re.compile(r"\bsocial\s+security\b", re.I),
    re.compile(r"\bcredentials\b", re.I),
    re.compile(r"\blogin\s+(details|credentials|info)\b", re.I),
)

_INFRA_SPEAK_PATTERNS = (
    re.compile(r"\b(ml|machine learning)\s+server\b", re.I),
    re.compile(r"\b(vertex|gemini|openai|anthropic)\b", re.I),
    re.compile(r"\b(can'?t|cannot)\s+reach\b", re.I),
    re.compile(r"\b(503|502|500|429)\b"),
    re.compile(r"\b(server|service)\s+(error|unavailable|down|timeout)\b", re.I),
    re.compile(r"\btry again later\b", re.I),
    re.compile(r"\binfrastructure\b", re.I),
    re.compile(r"\bapi\s+(error|timeout|failed)\b", re.I),
    re.compile(r"\bmodel\s+server\b", re.I),
)

LEXI_SPOKEN_SAFETY_RULES = (
    "Never ask for passwords, OTP codes, credit cards, SSN, or any credentials. "
    "Never mention ML servers, Vertex, Gemini, API errors, or other infrastructure. "
    "If unsure, thank the caller and ask one open diagnostic question about what they saw on screen."
)


def contains_spoken_placeholder(text: str) -> bool:
    """True when text still has bracket/curly placeholders or literal Customer Name."""
    if not text:
        return False
    return bool(
        _PLACEHOLDER_BRACKET.search(text)
        or _PLACEHOLDER_CURLY.search(text)
        or _PLACEHOLDER_CUSTOMER_NAME.search(text)
    )


def sanitize_spoken_line(text: str) -> str:
    """Strip placeholder tokens and tidy spacing — never speak [Customer Name] aloud."""
    t = str(text or "")
    t = _PLACEHOLDER_BRACKET.sub("", t)
    t = _PLACEHOLDER_CURLY.sub("", t)
    t = _PLACEHOLDER_CUSTOMER_NAME.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)
    t = re.sub(r"Hi\s+,", "Hi,", t, flags=re.I)
    return t


def spoken_line_fails_rails(text: str) -> bool:
    """True when text must not be spoken on a customer PSTN call."""
    if not (text or "").strip():
        return True
    if contains_spoken_placeholder(text):
        return True
    if _VAGUE_FEEDBACK_PHRASE.search(text):
        return True
    for pat in _CREDENTIAL_ASK_PATTERNS:
        if pat.search(text):
            return True
    for pat in _INFRA_SPEAK_PATTERNS:
        if pat.search(text):
            return True
    return False


def prepare_spoken_line(text: str) -> str | None:
    """Sanitize and enforce customer-call safety rails. None → use generic fallback."""
    cleaned = sanitize_spoken_line(text)
    if spoken_line_fails_rails(cleaned):
        return None
    return cleaned


def _voice_reason_phrase(voice_reason: str) -> str:
    return str(voice_reason or "").replace("_", " ").strip()


def _reflects_voice_reason(blob: str, voice_reason: str) -> bool:
    if not voice_reason:
        return True
    lower = blob.lower()
    vr = voice_reason.lower()
    if vr in lower:
        return True
    phrase = _voice_reason_phrase(voice_reason).lower()
    if phrase and phrase in lower:
        return True
    tokens = [t for t in phrase.split() if len(t) > 3]
    return any(t in lower for t in tokens)


def _grounded_feedback_opening(ctx: dict[str, Any], *, purpose: str, fix_summary: str = "") -> str:
    product = ctx.get("product") or "your product"
    if purpose == "fix_notify":
        fix = (fix_summary or "a recent issue").strip()[:180]
        return (
            f"Hi, this is Lexi from the {product} team. "
            f"We shipped a fix for {fix}. "
            "I wanted to check in and hear what you experienced."
        )
    voice_reason = str(ctx.get("voice_reason") or "").strip()
    metric = str(ctx.get("metric") or ctx.get("signal_title") or "").strip()
    hypothesis = str(ctx.get("hypothesis") or "").strip()
    if voice_reason:
        issue = _voice_reason_phrase(voice_reason)
    elif metric:
        issue = metric.replace("_", " ")
    elif hypothesis:
        issue = hypothesis[:140]
    else:
        return _GENERIC_FALLBACK_OPENING_FEEDBACK.format(product=product)
    return (
        f"Hi, this is Lexi from the {product} team. "
        f"We are looking into {issue} and wanted to hear what you saw on your side. "
        "Do you have about thirty seconds?"
    )


_GENERIC_FALLBACK_OPENING_FEEDBACK = (
    "Hi, this is Lexi from the {product} team. "
    "We noticed something unusual in recent activity and would like to learn what you experienced. "
    "Do you have about thirty seconds?"
)
_GENERIC_FALLBACK_OPENING_FIX = (
    "Hi, this is Lexi from the {product} team. "
    "We shipped a fix for an issue we were tracking and wanted to check in. "
    "Can you share what you saw on your side?"
)
_GENERIC_FALLBACK_QUESTIONS = [
    "What happened on your screen — did it keep loading or show an error?",
    "Have you tried again since?",
    "Is anything still not working for you?",
]
GENERIC_LISTEN_PROMPT = "After the tone, tell me what you saw on your side."


def _metric_from_investigation(inv: Any) -> str:
    scenario = str(getattr(inv, "scenario_id", None) or "")
    if scenario.startswith("t:") and scenario.count(":") >= 2:
        return scenario.split(":", 2)[2]
    title = str(getattr(inv, "title", None) or "")
    if ":" in title:
        return title.split(":", 1)[-1].strip()
    return title or str(getattr(inv, "id", "") or "")


def room_call_context(store: Any, room_id: str) -> dict[str, Any]:
    """Load investigation context for telephony at call time."""
    from loop.tenant import product_for_room

    room = store.get_room(room_id) if room_id else None
    if not room:
        return {}

    inv = store.get_investigation(room.investigation_id) if room.investigation_id else None
    product = product_for_room(store, room_id)
    metric = ""
    signal_title = str(getattr(room, "title", None) or "")
    hypothesis = ""
    voice_reason = ""
    failure = ""

    if inv:
        metric = _metric_from_investigation(inv)
        signal_title = str(getattr(inv, "title", None) or signal_title)
        hyps = store.list_hypotheses(inv.id)
        if hyps:
            hypothesis = str(hyps[0].statement or "")

    for msg in reversed(store.list_messages(room_id)):
        art = msg.artifact if isinstance(msg.artifact, dict) else {}
        if msg.artifact_type == "voice_context" and art:
            voice_reason = str(art.get("failure") or art.get("reason") or "")
            failure = voice_reason or failure
            if not hypothesis:
                hypothesis = str(art.get("hypothesis_hint") or "")
            break
        if msg.artifact_type in {"call_evidence", "call_feedback"} and isinstance(art.get("structured"), dict):
            voice_reason = str(art["structured"].get("reason") or "")
            if voice_reason:
                break

    if inv and not voice_reason:
        for ev in store.list_evidence(inv.id):
            if ev.source_type == "customer_voice":
                ref = str(ev.source_reference or "")
                m = re.search(r"reason=([\w_]+)", ref)
                if m:
                    voice_reason = m.group(1)
                    break

    return {
        "room_id": room_id,
        "metric": metric,
        "signal_title": signal_title,
        "hypothesis": hypothesis,
        "voice_reason": voice_reason,
        "failure": failure,
        "product": product,
    }


def sanitize_call_script(
    plan: dict[str, Any],
    ctx: dict[str, Any],
    *,
    purpose: str,
    fix_summary: str = "",
) -> dict[str, Any]:
    """Reject Gemini placeholders; ground opening in room evidence when present."""
    opening = prepare_spoken_line(str(plan.get("opening") or "")) or ""
    questions = []
    for q in plan.get("questions") or []:
        cleaned = prepare_spoken_line(str(q))
        if cleaned:
            questions.append(cleaned)
    listen = prepare_spoken_line(str(plan.get("listen_prompt") or "")) or GENERIC_LISTEN_PROMPT

    voice_reason = str(ctx.get("voice_reason") or "").strip()
    blob = f"{opening} {' '.join(questions)}"

    if (
        not opening
        or contains_spoken_placeholder(opening)
        or _VAGUE_FEEDBACK_PHRASE.search(opening)
    ):
        opening = _grounded_feedback_opening(ctx, purpose=purpose, fix_summary=fix_summary)
    elif voice_reason and not _reflects_voice_reason(blob, voice_reason):
        opening = _grounded_feedback_opening(ctx, purpose=purpose, fix_summary=fix_summary)

    if voice_reason and not _reflects_voice_reason(f"{opening} {' '.join(questions)}", voice_reason):
        phrase = _voice_reason_phrase(voice_reason)
        questions = [
            f"When you hit {phrase}, what did you see on screen?",
            *questions,
        ][:3]

    return {
        "opening": opening,
        "questions": questions or list(_GENERIC_FALLBACK_QUESTIONS),
        "listen_prompt": listen,
    }


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _generate_call_plan_with_gemini(ctx: dict[str, Any], purpose: str, fix_summary: str = "") -> dict[str, Any] | None:
    from loop.vertex_gemini import gemini_configured, generate_content

    if not gemini_configured():
        return None

    product = ctx.get("product") or "the product"
    metric = ctx.get("metric") or ctx.get("signal_title") or "unknown"
    voice_reason = ctx.get("voice_reason") or "not yet classified"
    hypothesis = ctx.get("hypothesis") or "under investigation"
    fix_line = f"- Fix summary: {fix_summary}\n" if fix_summary and purpose == "fix_notify" else ""

    voice_line = (
        f"- Customer Voice reason (cite this in the opening when present): {voice_reason}\n"
        if voice_reason and voice_reason != "not yet classified"
        else f"- Customer Voice reason: {voice_reason}\n"
    )
    prompt = (
        f"You are Lexi, a customer research agent for {product}.\n\n"
        "Investigation context (use ONLY this evidence — do not invent failure modes):\n"
        f"- Product: {product}\n"
        f"- Metric/signal: {metric}\n"
        f"{voice_line}"
        f"- Top hypothesis: {hypothesis}\n"
        f"- Call purpose: {purpose}  (feedback_ask = learn what happened; fix_notify = we fixed something, confirm)\n"
        f"{fix_line}\n"
        "Write a phone call plan as JSON with exactly these keys:\n"
        '- "opening": Lexi speaking, at most 2 short sentences, friendly, ask if they have about 30 seconds\n'
        '- "questions": array of 2-3 adaptive follow-up questions tailored to the evidence above\n'
        '- "listen_prompt": one short sentence inviting them to describe what they saw (generic, no invented failure mode)\n\n'
        "Rules:\n"
        "- NEVER use placeholder names like [Customer Name], {name}, or Customer Name — speak to the caller directly with no fake personalization\n"
        f"- Introduce yourself as Lexi from the {product} team (use the product name above)\n"
        "- Ground the opening in metric, Customer Voice reason, and/or hypothesis when any are present — do NOT say vague phrases like \"feedback you shared\"\n"
        "- When Customer Voice reason is present, reference it naturally in the opening (underscores may become spaces)\n"
        "- Never mention OTP, spinner, verification code, or other specifics UNLESS they appear in the context above\n"
        "- If evidence is thin, use open diagnostic questions without inventing specifics or placeholders\n"
        "- NEVER ask for passwords, OTP codes, credit cards, SSN, or credentials — diagnostic only\n"
        "- NEVER mention ML servers, Vertex, Gemini, API errors, or infrastructure to the caller\n"
        "- Output ONLY valid JSON, no markdown"
    )
    try:
        raw = generate_content(prompt, timeout=12.0)
        plan = json.loads(_strip_json_fence(raw))
        if isinstance(plan, dict) and plan.get("opening"):
            return plan
    except Exception:
        pass
    return None


def _generic_fallback_brief(ctx: dict[str, Any], purpose: str, fix_summary: str = "") -> dict[str, Any]:
    product = ctx.get("product") or "your product"
    opening = _grounded_feedback_opening(ctx, purpose=purpose, fix_summary=fix_summary)
    questions = list(_GENERIC_FALLBACK_QUESTIONS)
    voice_reason = str(ctx.get("voice_reason") or "").strip()
    if voice_reason and not _reflects_voice_reason(" ".join(questions), voice_reason):
        phrase = _voice_reason_phrase(voice_reason)
        questions = [f"When you hit {phrase}, what did you see on screen?", *questions][:3]
    return {
        "purpose": purpose,
        "product": product,
        "metric": ctx.get("metric", ""),
        "signal_title": ctx.get("signal_title", ""),
        "voice_reason": ctx.get("voice_reason", ""),
        "hypothesis": ctx.get("hypothesis", ""),
        "fix_summary": fix_summary,
        "opening": opening,
        "questions": list(_GENERIC_FALLBACK_QUESTIONS),
        "listen_prompt": GENERIC_LISTEN_PROMPT,
        "gemini_generated": False,
    }


def call_brief_for_outreach(
    row: dict[str, Any],
    *,
    fix_summary: str = "",
    store: Any | None = None,
    room_id: str = "",
) -> dict[str, Any]:
    """Build a context-aware call brief — Gemini when available, generic fallback otherwise."""
    purpose = str(row.get("call_purpose") or row.get("purpose") or "feedback_ask")
    if purpose == "fix_notify" or fix_summary:
        purpose = "fix_notify"

    ctx: dict[str, Any] = {}
    rid = room_id or str(row.get("room_id") or "")
    if store and rid:
        ctx = room_call_context(store, rid)
    if row.get("product"):
        ctx["product"] = str(row["product"])
    for key in ("metric", "hypothesis", "voice_reason", "signal_title"):
        if row.get(key):
            ctx[key] = str(row[key])

    summary = fix_summary or str(row.get("fix_summary") or "")
    plan = _generate_call_plan_with_gemini(ctx, purpose, summary)
    if plan:
        cleaned = sanitize_call_script(plan, ctx, purpose=purpose, fix_summary=summary)
        return {
            "purpose": purpose,
            "product": ctx.get("product") or str(row.get("product") or "your product"),
            "metric": ctx.get("metric", ""),
            "signal_title": ctx.get("signal_title", ""),
            "voice_reason": ctx.get("voice_reason", ""),
            "hypothesis": ctx.get("hypothesis", ""),
            "fix_summary": summary,
            "opening": cleaned["opening"],
            "questions": cleaned["questions"],
            "listen_prompt": cleaned["listen_prompt"],
            "gemini_generated": True,
        }
    fallback = _generic_fallback_brief(ctx, purpose, summary)
    cleaned = sanitize_call_script(fallback, ctx, purpose=purpose, fix_summary=summary)
    return {**fallback, **cleaned}


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
        from loop.tenant import product_for_room

        product_name = product_for_room(engine.store, room_id)
        brief = call_brief_for_outreach(
            {**row, "call_purpose": purpose, "product": product_name},
            fix_summary=fix_summary,
            store=engine.store,
            room_id=room_id,
        )
        from loop.abandon_research import call_system_prompt

        system_prompt = call_system_prompt(brief)
        report = voice_connector.place_call(
            tok,
            reason=str(row.get("pattern") or "follow_up"),
            to_number=phone,
            room_id=room_id,
            product=product_name,
            brief=brief,
            system_prompt=system_prompt,
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
