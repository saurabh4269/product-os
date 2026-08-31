"""Tenant flags survive Cloud Run deploy (GCS backup, same bucket as OAuth)."""

from __future__ import annotations

from typing import Any

from loop import gcs_state

PERSIST_NAMES = frozenset(
    {
        "pay_sdk_4_3",
        "onboarding_copy_exp_b",
        "show_delivery_date_earlier",
        "pay_sdk",
        "world_seeded",
    }
)


def flags_gcs_uri() -> str:
    return gcs_state.gcs_uri("LOOP_FLAGS_GCS_URI", "tenant_flags.json")


def _should_persist(name: str) -> bool:
    if name in PERSIST_NAMES:
        return True
    if name.startswith("t:") and name.split(":")[-1] in PERSIST_NAMES:
        return True
    return False


def filter_persistable(flags: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in flags.items() if _should_persist(k)}


def hydrate_flags(store: Any) -> int:
    """Load flags from GCS into SQLite. Returns count restored."""
    blob = gcs_state.read_json(flags_gcs_uri())
    raw = blob.get("flags") if isinstance(blob.get("flags"), dict) else blob
    if not isinstance(raw, dict) or not raw:
        return 0
    cleaned = filter_persistable({str(k): str(v) for k, v in raw.items()})
    if not cleaned:
        return 0
    store.restore_flags(cleaned)
    return len(cleaned)


def persist_flags(store: Any) -> None:
    """Write durable tenant flags to GCS after local change."""
    if not flags_gcs_uri():
        return
    flags = filter_persistable(store.list_flags())
    if not flags:
        return
    gcs_state.write_json(flags_gcs_uri(), {"flags": flags, "version": 1})
