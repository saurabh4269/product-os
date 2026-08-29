from __future__ import annotations

from typing import Any

from ..engine import LoopEngine, log_verdict
from ..store import Store

CONTACT_CAP = 1
MAX_ROLLOUT_PCT = 25


def make_side_effect_tools(engine: LoopEngine) -> list:
    store: Store = engine.store

    def toggle_feature_flag(
        action_id: str,
        flag: str,
        value: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Flip a flag. Requires approval for HIGH-tier actions. Honours idempotency_key (A-7)."""
        action = store.get_action(action_id)
        if action is None or action.status != "approved":
            log_verdict(
                store,
                agent="loop-experiment",
                tool="toggle_feature_flag",
                args=flag,
                verdict="DENY",
                rationale="Hard limit: flag writes require a recorded HIGH-tier approval.",
            )
            return {"error": "APPROVAL_REQUIRED"}
        val, reused = store.set_flag(flag, value, idempotency_key)
        return {"flag": flag, "value": val, "reused": reused}

    def place_call(tokenized_user: str, investigation_id: str, idempotency_key: str) -> dict[str, Any]:
        """Diagnostic contact only. Frequency cap is enforced in this function (L-4, K-15)."""
        allowed = store.record_contact(tokenized_user, CONTACT_CAP)
        if not allowed:
            log_verdict(
                store,
                agent="loop-customer",
                tool="place_call",
                args=tokenized_user,
                verdict="DENY",
                rationale=f"Frequency cap {CONTACT_CAP} per user — blocked in tool code.",
            )
            return {"error": "FREQUENCY_CAP", "tokenized_user": tokenized_user}

        def _do() -> dict:
            return {"placed": True, "channel": "text_fallback", "tokenized_user": tokenized_user}

        result, reused = store.claim_idempotency(idempotency_key, "place_call", _do)
        return {**result, "reused": reused}

    def write_memory_bank(
        investigation_id: str,
        statement: str,
        confidence: float,
        provenance: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """TB-7 only. Raw events are rejected (I-4)."""
        if "event_name" in statement or "events_" in statement[:20]:
            return {"error": "RAW_EVENTS_FORBIDDEN"}

        def _do() -> dict:
            store.put_memory(
                idempotency_key,
                "organizational",
                {
                    "statement": statement,
                    "confidence": confidence,
                    "provenance": provenance,
                    "investigation_id": investigation_id,
                },
            )
            return {"written": True}

        result, reused = store.claim_idempotency(idempotency_key, "write_memory_bank", _do)
        return {**result, "reused": reused}

    def experiment_rollout(percent: int, guardrail_ok: bool, idempotency_key: str) -> dict[str, Any]:
        """Numeric ceiling in tool code — not delegated to SGP (L-4)."""
        if percent > MAX_ROLLOUT_PCT:
            return {"error": "ROLLOUT_CEILING", "max": MAX_ROLLOUT_PCT}
        if not guardrail_ok:
            return {"error": "GUARDRAIL_BREACH", "rolled_back": True}

        def _do() -> dict:
            return {"percent": percent}

        result, reused = store.claim_idempotency(idempotency_key, "experiment_rollout", _do)
        return {**result, "reused": reused}

    def send_gmail(*_a: Any, **_k: Any) -> dict[str, Any]:
        """Gmail MCP has no send tool (R-4). Preserve that property."""
        return {"error": "GMAIL_CANNOT_SEND"}

    toggle_feature_flag.__name__ = "toggle_feature_flag"
    place_call.__name__ = "place_call"
    write_memory_bank.__name__ = "write_memory_bank"
    experiment_rollout.__name__ = "experiment_rollout"
    send_gmail.__name__ = "send_gmail"
    return [toggle_feature_flag, place_call, write_memory_bank, experiment_rollout, send_gmail]
