"""Recipe: checkout abandon — one ResearchEvent that uses customer_research infra.

Hardcoded demo numbers live only here as *example event dimensions*, not in the
pipeline. Other recipes should build a ResearchEvent the same way.
"""

from __future__ import annotations

from typing import Any

from loop.customer_research import ResearchEvent, run_customer_research
from loop.models import Lesson, LoopType, PathKind, RoomKind

RETURN_WINDOW_DAYS = 5
SCENARIO = "checkout_abandon"


def budget_return_lesson() -> Lesson:
    return Lesson(
        id="les_budget_return",
        investigation_id="inv_prior_org",
        statement=(
            f"When checkout abandon looks like budget hesitation, customers usually return "
            f"within {RETURN_WINDOW_DAYS} days. If they do not return, treat it as unresolved "
            f"technical friction and open a diagnostic call — not a discount offer."
        ),
        root_cause_family="checkout-abandon-return",
        applicable_conditions=[
            "funnel=checkout",
            "event=payment_started",
            "outcome=no_purchase",
            "family=abandon",
        ],
        linked_playbook_skill="playbooks/checkout-abandon",
        confidence=0.83,
        author_agent="learning_agent",
    )


def plant_abandon_memory(store: Any) -> None:
    lesson = budget_return_lesson()
    store.put_lesson(lesson)
    store.put_memory(
        lesson.id,
        "organizational",
        {
            "id": lesson.id,
            "kind": "organizational",
            "statement": lesson.statement,
            "root_cause_family": lesson.root_cause_family,
            "applicable_conditions": lesson.applicable_conditions,
            "provenance": "organizational memory — prior quarter abandon cohort",
            "confidence": lesson.confidence,
            "return_window_days": RETURN_WINDOW_DAYS,
        },
    )


def example_abandon_event(
    *,
    user_id: str = "8472",
    phone: str = "",
) -> ResearchEvent:
    """Example payload a real warehouse/ingest would emit — not pipeline logic."""
    return ResearchEvent(
        kind="checkout_abandon",
        user_id=user_id,
        phone=phone,
        title=f"Checkout abandon · user {user_id}",
        topic="Reached payment, left, did not return within the learned window.",
        metric="checkout_abandon_no_return",
        funnel_position="checkout",
        memory_conditions=[
            "funnel=checkout",
            "event=payment_started",
            "outcome=no_purchase",
            "family=abandon",
        ],
        loop_type=LoopType.TYPE_A,
        path=PathKind.BUG,
        room_kind=RoomKind.RESEARCH,
        dimensions={
            "acquisition": {"channel": "Google Ads", "campaign": "Campaign X"},
            "device": {"model": "Pixel 9", "os": "Android 15", "browser": "Chrome"},
            "app_version": "4.3.1",
            "pay_sdk": "4.3.0",
            "journey": ["Ad", "install", "onboarding", "checkout"],
            "ga4_events": ["session_start", "view_item", "begin_checkout", "add_payment_info"],
            "ga4_missing": ["purchase"],
            "ga4_claim": "session_start → view_item → begin_checkout → add_payment_info; no purchase",
            "ads_claim": "Acquisition = Google Ads / Campaign X (paid install)",
            "device_claim": "Pixel 9 · Android · Chrome WebView checkout",
            "app_version_claim": "App version 4.3.1 (pay SDK path 4.3.0)",
            "session_claim": "Ad → install → onboarding → checkout; payment attempt then idle",
            "payment_claim": "2 API retries · 1 payment timeout · no decline code",
            "support_claim": "No open tickets; 3 prior successful purchases",
            "observed": {
                "onboarding_completed": True,
                "product_viewed": True,
                "checkout_started": True,
                "payment_failed": True,
                "purchase": False,
            },
            "technical": {
                "crash": False,
                "api_retries": 2,
                "payment_timeout": 1,
                "decline_code": None,
            },
            "previous_behavior": {"successful_purchases": 3},
            "returned": False,
            "days_since_event": RETURN_WINDOW_DAYS + 2,
            "expect_return_within_days": RETURN_WINDOW_DAYS,
            "memory_implication": (
                f"Past budget cases return in {RETURN_WINDOW_DAYS} days — this user did not. "
                "Prefer technical diagnostic call over discount."
            ),
            "hypothesis": {
                "statement": "User experienced payment friction, not lack of purchase intent.",
                "confidence": 0.78,
            },
            "call_goal": "Confirm error vs loading; capture retries and willingness to retry.",
            "call_opening": (
                "Hi, this is Lexi from Cove. We noticed you almost finished checkout a few days ago "
                "and wanted to check what happened — do you have thirty seconds?"
            ),
            "call_questions": [
                "When you tried to complete your payment, did the payment screen show an error, or did it remain loading?",
                "Did you try again?",
                "Did you eventually complete the purchase?",
            ],
            "demo_replies": [
                "Sure, go ahead.",
                "It kept loading. My card was not being detected.",
                "Yes, twice.",
                "No, I gave up.",
            ],
        },
    )


def run_abandon_research(
    engine: Any,
    *,
    user_id: str = "8472",
    phone: str = "",
    place_real_call: bool = False,
) -> dict[str, Any]:
    plant_abandon_memory(engine.store)
    event = example_abandon_event(user_id=user_id, phone=phone)
    return run_customer_research(
        engine,
        event,
        place_real_call=place_real_call,
        scenario_id=SCENARIO,
    )


# Back-compat exports used by telephony / older tests
def build_customer_context_brief(user_id: str = "8472") -> dict[str, Any]:
    from loop.customer_research import build_brief, run_probes

    event = example_abandon_event(user_id=user_id)
    return build_brief(event, run_probes(event), []).model_dump(mode="json")


def extract_structured_evidence(transcript: list[dict[str, str]]) -> dict[str, Any]:
    from loop.customer_research import extract_structured_evidence as _ex

    return _ex(transcript).model_dump(mode="json")


def simulate_research_dialogue(brief: dict[str, Any]) -> list[dict[str, str]]:
    from loop.customer_research import CustomerContextBrief, simulate_research_dialogue as _sim

    return _sim(CustomerContextBrief.model_validate(brief) if "user_id" in brief else brief)


def call_system_prompt(brief: dict[str, Any]) -> str:
    from loop.customer_research import call_system_prompt as _csp

    return _csp(brief)


def investigation_sources(user_id: str = "8472") -> list[dict[str, Any]]:
    from loop.customer_research import run_probes

    return [s.model_dump() for s in run_probes(example_abandon_event(user_id=user_id))]
