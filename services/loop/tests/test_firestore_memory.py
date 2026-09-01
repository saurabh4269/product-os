"""Firestore Memory Bank mirror — recall and upsert hooks."""

from __future__ import annotations

from loop.firestore_memory import enabled
from loop.memory_recall import recall_statements, recall_tokens
from loop.models import Lesson


def test_recall_tokens_dedupes_short():
    toks = recall_tokens("purchase_conversion", "android", "sdk")
    assert "purchase" in toks or "purchase_conversion" in toks
    assert "android" in toks


def test_recall_statements_from_records():
    records = [
        {
            "statement": "SDK callback regressions after payment SDK upgrades need device tests.",
            "root_cause_family": "sdk-callback",
            "applicable_conditions": ["pay-sdk", "checkout"],
        }
    ]
    hits = recall_statements(records, "android", "pay-sdk", "sdk")
    assert any("SDK callback" in h for h in hits)


def test_firestore_recall_merges_with_sqlite(engine, monkeypatch):
    monkeypatch.setenv("LOOP_FIRESTORE_MEMORY", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    firestore_only = [
        {
            "statement": "Firestore-only SDK callback playbook for cold starts.",
            "root_cause_family": "sdk-callback",
            "applicable_conditions": ["pay-sdk"],
        }
    ]
    monkeypatch.setattr("loop.firestore_memory._stream_records", lambda *a, **k: firestore_only)
    monkeypatch.setattr("loop.firestore_memory._get_client", lambda: object())

    hits = engine.recall_lessons("pay-sdk", "android", "sdk")
    assert any("Firestore-only" in h for h in hits)


def test_firestore_mirror_on_put_lesson(engine, monkeypatch):
    monkeypatch.setenv("LOOP_FIRESTORE_MEMORY", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    upserts: list[str] = []

    def _capture(lesson: Lesson) -> None:
        upserts.append(lesson.id)

    monkeypatch.setattr("loop.firestore_memory._get_client", lambda: object())
    monkeypatch.setattr("loop.firestore_memory.upsert_from_lesson", _capture)

    engine.store.put_lesson(
        Lesson(
            id="les_mirror_test",
            investigation_id="inv_x",
            statement="Mirror me to Firestore",
            root_cause_family="test",
            applicable_conditions=[],
            confidence=0.9,
            author_agent="learning_agent",
        )
    )
    assert upserts == ["les_mirror_test"]


def test_firestore_disabled_by_default_locally(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("LOOP_FIRESTORE_MEMORY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    assert enabled() is False
