"""Firestore mirror for Memory Bank — durable lessons across Cloud Run cold starts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from loop.memory_recall import recall_statements, recall_tokens
from loop.models import Lesson

_COLLECTION = os.environ.get("LOOP_FIRESTORE_COLLECTION", "loop_memory")
_client: Any | None = None
_client_tried = False
_last_error: str = ""


def enabled() -> bool:
    flag = os.environ.get("LOOP_FIRESTORE_MEMORY", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    return bool(os.environ.get("K_SERVICE"))


def status() -> dict[str, Any]:
    configured = enabled()
    operational = configured and _client is not None and not _last_error
    skipped_reason: str | None = None
    if not configured:
        skipped_reason = "LOOP_FIRESTORE_MEMORY off or no GCP project"
    elif _last_error:
        skipped_reason = _last_error[:240]
    elif configured and _client is None and _client_tried:
        skipped_reason = "Firestore client unavailable"
    return {
        "configured": configured,
        "enabled": operational,
        "operational": operational,
        "skipped": not operational,
        "skipped_reason": skipped_reason,
        "collection": _COLLECTION,
        "project": (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip() or None,
        "client": _client is not None,
        "last_error": _last_error or None,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _note_error(exc: Exception) -> None:
    global _last_error
    _last_error = str(exc)[:400]


def _get_client() -> Any | None:
    global _client, _client_tried
    if _client_tried:
        return _client
    _client_tried = True
    if not enabled():
        return None
    try:
        from google.cloud import firestore

        client = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
        # Probe once — fail closed when API is disabled (SERVICE_DISABLED).
        try:
            next(iter(client.collection(_COLLECTION).limit(1).stream()), None)
            global _last_error
            _last_error = ""
        except Exception as exc:
            _note_error(exc)
            _client = None
            return None
        _client = client
    except Exception as exc:
        _note_error(exc)
        _client = None
    return _client


def _index_tokens(*parts: str) -> list[str]:
    toks = sorted(recall_tokens(*parts))
    return toks[:30]


def upsert_from_lesson(lesson: Lesson) -> None:
    client = _get_client()
    if not client:
        return
    try:
        client.collection(_COLLECTION).document(lesson.id).set(
            {
                "id": lesson.id,
                "kind": "lesson",
                "statement": lesson.statement,
                "root_cause_family": lesson.root_cause_family,
                "applicable_conditions": lesson.applicable_conditions,
                "investigation_id": lesson.investigation_id,
                "confidence": lesson.confidence,
                "author_agent": lesson.author_agent,
                "tenant_id": lesson.tenant_id,
                "linked_playbook_skill": lesson.linked_playbook_skill,
                "recall_tokens": _index_tokens(
                    lesson.statement,
                    lesson.root_cause_family,
                    *lesson.applicable_conditions,
                ),
                "updated_at": _now(),
            },
            merge=True,
        )
        global _last_error
        _last_error = ""
    except Exception as exc:
        _note_error(exc)


def upsert_from_memory(id_: str, kind: str, payload: dict[str, Any]) -> None:
    client = _get_client()
    if not client:
        return
    body = dict(payload)
    try:
        client.collection(_COLLECTION).document(id_).set(
            {
                "id": id_,
                "kind": kind,
                "statement": body.get("statement") or body.get("title") or "",
                "body": body.get("body"),
                "title": body.get("title"),
                "root_cause_family": body.get("root_cause_family"),
                "applicable_conditions": body.get("applicable_conditions") or [],
                "tenant_id": body.get("tenant_id"),
                "payload": body,
                "recall_tokens": _index_tokens(
                    str(body.get("statement") or ""),
                    str(body.get("title") or ""),
                    str(body.get("root_cause_family") or ""),
                    *([str(c) for c in (body.get("applicable_conditions") or [])]),
                ),
                "updated_at": _now(),
            },
            merge=True,
        )
        global _last_error
        _last_error = ""
    except Exception as exc:
        _note_error(exc)


def _stream_records(*needles: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    client = _get_client()
    if not client:
        return []
    tokens = sorted(recall_tokens(*needles))[:10]
    try:
        if tokens:
            query = client.collection(_COLLECTION).where("recall_tokens", "array_contains_any", tokens)
            if tenant_id:
                query = query.where("tenant_id", "==", tenant_id)
            docs = list(query.stream())
            if docs:
                return [doc.to_dict() for doc in docs]
        return [doc.to_dict() for doc in client.collection(_COLLECTION).stream()]
    except Exception as exc:
        _note_error(exc)
        try:
            return [doc.to_dict() for doc in client.collection(_COLLECTION).stream()]
        except Exception as exc2:
            _note_error(exc2)
            return []


def recall(*needles: str, tenant_id: str | None = None) -> list[str]:
    if not enabled():
        return []
    return recall_statements(_stream_records(*needles, tenant_id=tenant_id), *needles, tenant_id=tenant_id)


def backfill_from_store(store: Any) -> int:
    """Hydrate Firestore from SQLite lessons on cold start."""
    if not enabled():
        return 0
    count = 0
    for lesson in store.list_lessons():
        upsert_from_lesson(lesson)
        count += 1
    for mem in store.list_memory():
        upsert_from_memory(str(mem.get("id") or ""), str(mem.get("kind") or "memory"), mem)
        count += 1
    return count
