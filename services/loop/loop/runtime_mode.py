"""Production vs eval/fixture runtime — single source of truth."""

from __future__ import annotations

import os

FIXTURE_SCENARIOS = (
    "safari_3ds",
    "android_sdk",
    "onboarding_activation",
    "apple_pay",
    "shipping_ux",
    "security_exfil",
)


def is_eval_mode() -> bool:
    """Fixture demos, synthetic pipeline, and open approvals (local default on)."""
    if os.environ.get("K_SERVICE"):
        return os.environ.get("LOOP_EVAL", "0") == "1"
    return os.environ.get("LOOP_EVAL", "1") == "1"


def use_file_warehouse() -> bool:
    """Synthetic file warehouse — eval/CI and explicit LOOP_WAREHOUSE_MODE=file."""
    mode = (os.environ.get("LOOP_WAREHOUSE_MODE") or "").strip().lower()
    if mode in ("bq", "bigquery", "tenant"):
        return False
    if mode == "file":
        return True
    return is_eval_mode()


def inject_fixture_evidence() -> bool:
    """Poisoned GitHub / prompt-injection cards — eval and security fixture only."""
    return is_eval_mode()


def require_eval(feature: str = "fixture") -> None:
    from fastapi import HTTPException

    if not is_eval_mode():
        raise HTTPException(403, f"{feature} disabled outside eval mode (set LOOP_EVAL=1)")
