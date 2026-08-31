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
    last_pr_url: str = ""
    last_ingest_at: str = ""
    last_connector: str = ""
    metric_catalog: list[str] = Field(default_factory=list)
    flag_names: list[str] = Field(default_factory=list)
    code_paths: list[str] = Field(default_factory=list)
    flag_file_path: str = "config/flags.json"
    stack: str = ""
    test_command: str = ""
    default_surface: str = "product"
    # Warehouse / analytics plane (GA4 → BQ, Ads transfer)
    bq_project: str = ""
    bq_raw_dataset: str = ""
    bq_metrics_dataset: str = ""
    ga4_property_id: str = ""
    ga4_dataset: str = ""
    ads_dataset: str = ""
    ads_customer_id: str = ""
    warehouse_mode: str = "auto"  # auto | file | bq_raw | ga4
    primary_metric: str = "purchase_conversion"
    funnel_events: list[str] = Field(
        default_factory=lambda: [
            "page_view",
            "view_item",
            "begin_checkout",
            "add_payment_info",
            "purchase",
        ]
    )


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


def tenant_id_from_scenario(scenario_id: str | None) -> str | None:
    if not scenario_id or not scenario_id.startswith("t:"):
        return None
    parts = scenario_id.split(":", 2)
    return parts[1] if len(parts) >= 2 and parts[1] else None


def is_tenant_scenario(scenario_id: str | None) -> bool:
    return tenant_id_from_scenario(scenario_id) is not None


def resolve_tenant(
    store: Any,
    *,
    tenant_id: str | None = None,
    investigation: Any | None = None,
    room: Any | None = None,
    scenario_id: str | None = None,
) -> Tenant | None:
    """Resolve the tenant that owns this work — never pick an arbitrary first row."""
    tid = tenant_id
    if not tid and investigation is not None:
        tid = getattr(investigation, "tenant_id", None) or tenant_id_from_scenario(getattr(investigation, "scenario_id", None))
    if not tid and room is not None:
        tid = getattr(room, "tenant_id", None) or tenant_id_from_scenario(getattr(room, "scenario_id", None))
    if not tid and scenario_id:
        tid = tenant_id_from_scenario(scenario_id)
    if not tid:
        return None
    return store.get_tenant(tid)


def product_for_room(store: Any, room_id: str, *, fallback: str = "your product") -> str:
    room = store.get_room(room_id) if room_id else None
    if not room:
        return fallback
    tenant = resolve_tenant(store, room=room)
    if tenant and tenant.product:
        return tenant.product
    return fallback

def seed_placeholder(store: Any) -> Tenant:
    tid = (os.environ.get("LOOP_TENANT_ID") or "acme").strip() or "acme"
    existing = store.get_tenant(tid)
    if existing:
        return existing
    token = os.environ.get("LOOP_TENANT_BOOTSTRAP_TOKEN", "")
    repo = os.environ.get("LOOP_TENANT_REPO", "")
    name = (os.environ.get("LOOP_TENANT_NAME") or os.environ.get("LOOP_TENANT_PRODUCT") or tid).strip()
    product = (os.environ.get("LOOP_TENANT_PRODUCT") or name).strip()
    stack = (os.environ.get("LOOP_TENANT_STACK") or ("nextjs" if repo else "")).strip()
    flag_names_raw = (os.environ.get("LOOP_TENANT_FLAG_NAMES") or "").strip()
    flag_names = [x.strip() for x in flag_names_raw.split(",") if x.strip()] if flag_names_raw else (["pay_sdk_4_3"] if repo and stack == "nextjs" else [])
    code_paths_raw = (os.environ.get("LOOP_TENANT_CODE_PATHS") or "").strip()
    if code_paths_raw:
        code_paths = [x.strip() for x in code_paths_raw.split(",") if x.strip()]
    elif repo and stack == "nextjs":
        code_paths = ["src/app/(store)/checkout/page.tsx", "src/lib/loop.ts"]
    else:
        code_paths = []
    bq_raw = (os.environ.get("LOOP_TENANT_BQ_RAW_DATASET") or os.environ.get("LOOP_BQ_DATASET") or "").strip()
    bq_metrics = (os.environ.get("LOOP_TENANT_BQ_METRICS_DATASET") or "loop_metrics").strip()
    funnel_raw = (os.environ.get("LOOP_TENANT_FUNNEL_EVENTS") or "").strip()
    funnel_events = (
        [x.strip() for x in funnel_raw.split(",") if x.strip()]
        if funnel_raw
        else ["page_view", "view_item", "begin_checkout", "add_payment_info", "purchase"]
    )
    t = Tenant(
        id=tid,
        name=name,
        product=product,
        repo=repo,
        deploy_url=os.environ.get("LOOP_TENANT_DEPLOY_URL", ""),
        token_hash=hash_token(token) if token else "",
        connected=bool(repo and token),
        flag_names=flag_names,
        code_paths=code_paths,
        stack=stack,
        test_command=(os.environ.get("LOOP_TENANT_TEST_COMMAND") or "").strip(),
        flag_file_path=(os.environ.get("LOOP_TENANT_FLAG_FILE") or "config/flags.json").strip(),
        default_surface=(os.environ.get("LOOP_TENANT_DEFAULT_SURFACE") or "product").strip(),
        bq_project=(os.environ.get("LOOP_TENANT_BQ_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip(),
        bq_raw_dataset=bq_raw,
        bq_metrics_dataset=bq_metrics,
        ga4_property_id=(os.environ.get("LOOP_TENANT_GA4_PROPERTY_ID") or "").strip(),
        ga4_dataset=(os.environ.get("LOOP_TENANT_GA4_DATASET") or "").strip(),
        ads_dataset=(os.environ.get("LOOP_TENANT_ADS_DATASET") or "").strip(),
        ads_customer_id=(os.environ.get("LOOP_TENANT_ADS_CUSTOMER_ID") or "").strip(),
        warehouse_mode=(os.environ.get("LOOP_TENANT_WAREHOUSE_MODE") or ("bq_raw" if bq_raw else "auto")).strip(),
        primary_metric=(os.environ.get("LOOP_TENANT_PRIMARY_METRIC") or "purchase_conversion").strip(),
        funnel_events=funnel_events,
    )
    store.put_tenant(t)
    return t


def bind_fixture_tenants(store: Any) -> None:
    """Link eval fixtures to the bootstrap tenant row when it exists (gate + PR labels)."""
    demo_id = (os.environ.get("LOOP_TENANT_ID") or "acme").strip() or "acme"
    demo = store.get_tenant(demo_id)
    if not demo:
        return
    for inv in store.list_investigations():
        if inv.scenario_id == "safari_3ds" and not inv.tenant_id:
            inv.tenant_id = demo.id
            store.put_investigation(inv)
    for room in store.list_rooms():
        if room.scenario_id == "safari_3ds" and not room.tenant_id:
            room.tenant_id = demo.id
            store.put_room(room)
