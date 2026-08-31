"""Admin authentication — protect control-plane mutations."""

from __future__ import annotations

import os

from fastapi import HTTPException


def admin_token() -> str:
    return (os.environ.get("LOOP_ADMIN_TOKEN") or "").strip()


def admin_required() -> bool:
    """When true, admin bearer is mandatory."""
    return bool(admin_token())


def eval_mode_open() -> bool:
    """Demo / fixture path — console approvals without admin bearer."""
    return os.environ.get("LOOP_EVAL", "1") == "1"


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return authorization.strip()


def require_admin(authorization: str | None, *, actor: str = "admin") -> str:
    """Return actor identity or raise 401."""
    expected = admin_token()
    if not admin_required():
        return actor or "dev"
    token = bearer_token(authorization)
    if not expected or token != expected:
        raise HTTPException(401, "admin bearer token required")
    return actor or "admin"


def require_approval(authorization: str | None, *, actor: str = "admin") -> str:
    """Console HITL — open in eval/demo; admin bearer when token set and eval off."""
    if not admin_required():
        return actor or "dev"
    if eval_mode_open():
        return actor or "console"
    return require_admin(authorization, actor=actor)


def require_admin_or_internal(authorization: str | None, *, internal_header: str | None = None) -> str:
    """Worker tick: admin bearer or matching X-Loop-Worker header."""
    expected = admin_token()
    if internal_header and expected and internal_header == expected:
        return "worker"
    return require_admin(authorization, actor="worker")
