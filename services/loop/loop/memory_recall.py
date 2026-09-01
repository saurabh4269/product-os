"""Shared token matching for Memory Bank recall (SQLite + Firestore)."""

from __future__ import annotations

import re
from typing import Any


def re_split_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t for t in re.split(r"[^a-z0-9]+", str(raw).lower()) if len(t) >= 3]


def recall_tokens(*needles: str) -> set[str]:
    tokens: set[str] = set()
    for n in needles:
        s = str(n).strip().lower()
        if not s:
            continue
        tokens.add(s)
        tokens.update(re_split_tokens(s))
    return {t for t in tokens if len(t) >= 3}


def blob_hits(blob: str, tokens: set[str]) -> bool:
    if not tokens:
        return False
    for t in tokens:
        if len(t) >= 5:
            if t in blob:
                return True
        elif re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", blob):
            return True
    return False


def recall_statements(
    records: list[dict[str, Any]],
    *needles: str,
    tenant_id: str | None = None,
) -> list[str]:
    tokens = recall_tokens(*needles)
    if not tokens:
        return []

    hits: list[str] = []
    seen: set[str] = set()
    for rec in records:
        if tenant_id and rec.get("tenant_id") and rec.get("tenant_id") != tenant_id:
            continue
        conditions = rec.get("applicable_conditions") or []
        if isinstance(conditions, str):
            conditions = [conditions]
        blob = " ".join(
            [
                str(rec.get("statement") or ""),
                str(rec.get("body") or ""),
                str(rec.get("title") or ""),
                str(rec.get("root_cause_family") or ""),
                " ".join(str(c) for c in conditions),
            ]
        ).lower()
        if not blob_hits(blob, tokens):
            continue
        stmt = str(rec.get("statement") or rec.get("title") or "").strip()
        if stmt and stmt not in seen:
            hits.append(stmt)
            seen.add(stmt)
    return hits
