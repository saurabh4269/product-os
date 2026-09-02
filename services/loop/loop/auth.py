"""Admin authentication — protect control-plane mutations."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException


def admin_token() -> str:
    return (os.environ.get("LOOP_ADMIN_TOKEN") or "").strip()


def is_hosted() -> bool:
    return bool(os.environ.get("K_SERVICE"))


def dev_open() -> bool:
    """Explicit escape hatch for local/demo — never default on Cloud Run."""
    return os.environ.get("LOOP_DEV_OPEN", "0") == "1"


def admin_required() -> bool:
    """When true, admin bearer is mandatory for mutations."""
    if admin_token():
        return True
    if is_hosted() and not dev_open():
        return True
    return False


def eval_mode_open() -> bool:
    """Demo / fixture path — console approvals without admin bearer."""
    from .runtime_mode import is_eval_mode

    return is_eval_mode()


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
        raise HTTPException(
            401,
            "admin bearer token required — set LOOP_ADMIN_TOKEN on the service and authorize in Connect",
        )
    return actor or "admin"


def require_admin_unless_eval(authorization: str | None, *, actor: str = "admin") -> str:
    """Hosted production reads — open in eval/demo; admin bearer when eval off."""
    from .runtime_mode import is_eval_mode

    if is_eval_mode():
        return actor or "eval"
    return require_admin(authorization, actor=actor)


def admin_unless_eval_dep(
    authorization: str | None = Header(default=None),
) -> str:
    """FastAPI dependency — runs before request body validation."""
    return require_admin_unless_eval(authorization)


AdminUnlessEval = Annotated[str, Depends(admin_unless_eval_dep)]


def cors_allowlist() -> tuple[list[str], bool]:
    """Return (origins, allow_credentials). Never wildcard on Cloud Run."""
    from .config import settings

    origin = (settings().console_origin or "").strip()
    public = (os.environ.get("LOOP_PUBLIC_URL") or "").strip().rstrip("/")
    local = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3010", "http://127.0.0.1:3010"]
    if origin == "*":
        if is_hosted():
            hosted = public or "https://productos.heisenbug.in"
            return [hosted, *local], True
        return ["*"], False
    origins = [origin, *local]
    if public and public not in origins:
        origins.append(public)
    # Legacy run.app URL for smoke tests during domain cutover
    run_app = (os.environ.get("LOOP_RUN_APP_URL") or "").strip().rstrip("/")
    if run_app and run_app not in origins:
        origins.append(run_app)
    return list(dict.fromkeys(o for o in origins if o)), True


def require_admin_or_tenant(
    authorization: str | None,
    *,
    tenant_id: str,
    store: Any,
    actor: str = "tenant",
) -> str:
    """Admin bearer or matching tenant token for read-scoped tenant detail."""
    from .tenant import token_ok

    expected = admin_token()
    token = bearer_token(authorization)
    if expected and token == expected:
        return actor or "admin"
    if not admin_required():
        return actor or "dev"
    t = store.get_tenant(tenant_id)
    if t and token_ok(t, token):
        return f"tenant:{tenant_id}"
    raise HTTPException(401, "admin bearer or tenant token required")


def require_approval(authorization: str | None, *, actor: str = "admin") -> str:
    """Console HITL — open in eval/demo; admin bearer when token set and eval off."""
    if not admin_required():
        return actor or "dev"
    if eval_mode_open():
        return actor or "console"
    return require_admin(authorization, actor=actor)


def worker_secret() -> str:
    return (os.environ.get("LOOP_WORKER_SECRET") or admin_token() or "").strip()


def verify_internal_oidc(token: str) -> bool:
    """Cloud Scheduler / Cloud Tasks OIDC (Authorization: Bearer <jwt>)."""
    if not is_hosted() or not token or token.count(".") != 2:
        return False
    audience = (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")
    if not audience:
        return False
    try:
        from google.auth.transport import requests as grequests
        from google.oauth2 import id_token

        id_token.verify_oauth2_token(token, grequests.Request(), audience=audience)
        return True
    except Exception:
        return False


def require_admin_or_internal(authorization: str | None, *, internal_header: str | None = None) -> str:
    """Worker tick: admin bearer, X-Loop-Worker secret, or GCP OIDC."""
    expected = admin_token()
    secret = worker_secret()
    if internal_header and secret and internal_header == secret:
        return "worker"
    token = bearer_token(authorization)
    if token and expected and token == expected:
        return "worker"
    if token and verify_internal_oidc(token):
        return "worker"
    if not admin_required():
        return "worker"
    raise HTTPException(401, "worker auth required — admin bearer, X-Loop-Worker, or OIDC")
