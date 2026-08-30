"""A Company X record. Product Y lives in their repo — not on this origin."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    id: str
    name: str
    product: str
    repo: str = ""
    deploy_url: str = ""
    token_hash: str = ""
    connected: bool = False


class ConnectorReport(BaseModel):
    status: str
    connector: str
    detail: str
    url: str | None = None


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def token_ok(tenant: Tenant, raw: str | None) -> bool:
    if not raw or not tenant.token_hash:
        return False
    return hash_token(raw) == tenant.token_hash


def flag_key(tenant_id: str, name: str) -> str:
    return f"t:{tenant_id}:{name}"


def seed_placeholder(store: Any) -> Tenant:
    existing = store.get_tenant("acme")
    if existing:
        return existing
    token = os.environ.get("LOOP_TENANT_BOOTSTRAP_TOKEN", "")
    repo = os.environ.get("LOOP_TENANT_REPO", "")
    t = Tenant(
        id="acme",
        name="Acme",
        product="Product Y",
        repo=repo,
        deploy_url=os.environ.get("LOOP_TENANT_DEPLOY_URL", ""),
        token_hash=hash_token(token) if token else "",
        connected=bool(repo and token),
    )
    store.put_tenant(t)
    return t
