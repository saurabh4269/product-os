"""Customer Voice structured evidence on the live investigation path (not seed-only)."""

from __future__ import annotations

from typing import Any

from .investigation import AnomalyEvent, InvestigatorClaim, build_voice_context

CUSTOMER_VOICE_FIELDS = frozenset(
    {
        "reason",
        "severity",
        "purchase_intent",
        "friction",
        "competitor_mentioned",
        "feature_request",
        "willing_to_retry",
        "confidence",
    }
)


def _structured_for_inv(engine: Any, inv_id: str) -> dict[str, Any] | None:
    mem_id = f"voice_{inv_id}"
    for mem in engine.store.list_memory(kind="customer"):
        if mem.get("id") == mem_id or mem.get("provenance") == inv_id:
            block = mem.get("structured")
            if isinstance(block, dict):
                return block
    return None


def maybe_emit_live_customer_voice(
    engine: Any,
    *,
    room: Any,
    inv: Any,
    event: AnomalyEvent,
    claims: list[InvestigatorClaim],
    pack: Any | None = None,
) -> bool:
    """Diagnostic conversation + structured JSON when customer arm is active."""
    dims = event.dimensions if isinstance(event.dimensions, dict) else {}
    has_customer = any(c.agent == "customer_voice_agent" for c in claims)
    if not has_customer and not dims.get("needs_call"):
        return False

    from .world import post

    voice_ctx = None
    if pack is not None:
        hyp_hint = str((event.dimensions.get("hypothesis") or {}).get("statement") or pack.correlation_summary)
        voice_ctx = build_voice_context(event, pack, hyp_hint)
        post(
            engine,
            room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="artifact",
            text=f"Diagnostic context ready · {voice_ctx.failure or event.metric}",
            artifact_type="voice_context",
            artifact={**voice_ctx.model_dump(), "voice_subject": dict(dims.get("voice_subject") or {})},
        )

    transcript: list[dict[str, str]] = []
    structured: dict[str, Any] | None = None
    try:
        from .customer_research import extract_structured_evidence, simulate_research_dialogue

        voice_sub = dict(dims.get("voice_subject") or {})
        brief = {
            "title": f"Diagnostic · {event.metric}",
            "user_id": str(dims.get("tenant_id") or "customer"),
            "event_kind": event.kind,
            "observed": {"metric": event.metric, "magnitude": event.magnitude},
            "device": dict(dims.get("segments") or {}),
            "hypothesis": {"statement": voice_ctx.hypothesis_hint if voice_ctx else event.metric},
            "journey": [event.funnel_position],
            "raw": {"dimensions": {"voice_subject": voice_sub, **voice_sub}},
        }
        if voice_ctx:
            brief.update(
                {
                    "device": {"label": voice_ctx.device or brief.get("device")},
                    "observed": {
                        **brief["observed"],
                        "failure": voice_ctx.failure,
                        "attempt_summary": voice_ctx.attempt_summary,
                    },
                    "call_plan": {
                        "opening": voice_ctx.opening,
                        "questions": list(voice_ctx.adaptive_questions),
                        "adaptive_questions": list(voice_ctx.adaptive_questions),
                    },
                }
            )
        transcript = simulate_research_dialogue(brief)
        metric = str((brief.get("observed") or {}).get("metric") or "")
        ev = extract_structured_evidence(transcript, metric=metric)
        structured = ev.model_dump(mode="json")
    except Exception:
        engine._collect_customer_voice(inv)
        structured = _structured_for_inv(engine, inv.id)

    if transcript:
        post(
            engine,
            room.id,
            author="customer_voice_agent",
            author_kind="agent",
            kind="chat",
            text="Starting adaptive diagnostic — not a survey.",
        )
        for turn in transcript:
            post(
                engine,
                room.id,
                author="customer_voice_agent" if turn["role"] == "agent" else "customer",
                author_kind="agent" if turn["role"] == "agent" else "human",
                kind="chat",
                text=turn["message"],
            )

    if not structured:
        return False

    engine.store.put_memory(
        f"voice_{inv.id}",
        "customer",
        {"structured": structured, "provenance": inv.id, "kind": "customer"},
        tenant_id=inv.tenant_id,
    )
    engine._evidence(
        inv,
        source_type="customer_voice",
        source_reference=f"live-diagnostic:{inv.id} reason={structured.get('reason')}",
        claim=(
            f"Diagnostic conversation: reason={structured.get('reason')} "
            f"severity={structured.get('severity')} friction={structured.get('friction')} "
            f"confidence={structured.get('confidence')}"
        ),
        independence_group="customer_voice",
        collected_by="customer_voice_agent",
        confidence=float(structured.get("confidence") or 0.9),
    )

    reason = structured.get("reason") or structured.get("friction") or "customer_friction"
    post(
        engine,
        room.id,
        author="customer_voice_agent",
        author_kind="agent",
        kind="artifact",
        text=(
            f"Structured evidence · reason={reason} severity={structured.get('severity')} "
            f"confidence={structured.get('confidence')}"
        ),
        artifact_type="call_evidence",
        artifact={
            "structured": structured,
            "transcript": transcript,
            "provenance": inv.id,
            "kind": "customer",
        },
    )
    return True
