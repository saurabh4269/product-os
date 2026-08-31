"""Production GCP onboarding — wire a Cloud Run Product Y to Product OS.

Assumes the client hosts Product Y on Cloud Run (same GCP project as LOOP, or
any project where LOOP's runtime SA can run.services.get/update). No token
copy-paste in the happy path: LOOP mints the token and pushes env vars.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.request
from typing import Any

from loop.tenant import Tenant, hash_token


def _project() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or os.environ.get("PROJECT_ID")
        or ""
    ).strip()


def _region() -> str:
    return (os.environ.get("LOOP_CLOUD_RUN_REGION") or os.environ.get("GOOGLE_CLOUD_REGION") or "us-central1").strip()


def _public_os_url() -> str:
    return (os.environ.get("LOOP_PUBLIC_URL") or "").rstrip("/")


def _access_token() -> str:
    try:
        import google.auth
        from google.auth.transport.requests import Request

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not creds.valid:
            creds.refresh(Request())
        return creds.token or ""
    except Exception:
        return ""


def _run_api(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    token = _access_token()
    if not token:
        return 401, {"error": "no ADC / service account credentials"}
    url = f"https://run.googleapis.com/v2/{path.lstrip('/')}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "product-os-loop",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:1200]
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"error": detail}
        return e.code, parsed
    except Exception as exc:
        return 500, {"error": str(exc)}


def _service_url(payload: dict) -> str:
    uri = payload.get("uri") or ""
    if uri:
        return str(uri)
    urls = payload.get("urls")
    if isinstance(urls, list) and urls:
        return str(urls[0])
    status = payload.get("status")
    if isinstance(status, dict) and status.get("url"):
        return str(status["url"])
    return ""


def list_cloud_run_services(*, project: str = "", region: str = "") -> dict[str, Any]:
    """List Cloud Run services for the Connect picker."""
    proj = project or _project()
    reg = region or _region()
    if not proj:
        return {
            "status": "skipped",
            "detail": "GOOGLE_CLOUD_PROJECT unset",
            "project": "",
            "region": reg,
            "services": [],
        }
    st, payload = _run_api("GET", f"projects/{proj}/locations/{reg}/services")
    if st != 200:
        return {
            "status": "skipped",
            "detail": f"Cloud Run list {st}: {payload}",
            "project": proj,
            "region": reg,
            "services": [],
        }
    services = []
    for row in payload.get("services") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        short = name.rsplit("/", 1)[-1] if name else ""
        if not short:
            continue
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        annotations: dict = {}
        template = row.get("template") if isinstance(row.get("template"), dict) else {}
        if isinstance(template.get("annotations"), dict):
            annotations = template["annotations"]
        services.append(
            {
                "id": short,
                "name": short,
                "full_name": name,
                "url": _service_url(row),
                "labels": labels,
                "repo_hint": labels.get("github-repo")
                or labels.get("repo")
                or annotations.get("product-os.dev/repo")
                or "",
            }
        )
    services.sort(key=lambda s: (0 if s["id"] not in {"loop", "loop-adk"} else 1, s["id"]))
    return {
        "status": "applied",
        "detail": f"{len(services)} services in {proj}/{reg}",
        "project": proj,
        "region": reg,
        "services": services,
    }


def describe_cloud_run_service(service: str, *, project: str = "", region: str = "") -> dict[str, Any]:
    proj = project or _project()
    reg = region or _region()
    st, payload = _run_api("GET", f"projects/{proj}/locations/{reg}/services/{service}")
    if st != 200 or not isinstance(payload, dict):
        return {"status": "skipped", "detail": f"describe {st}: {payload}", "service": service}
    env: dict[str, str] = {}
    try:
        containers = (payload.get("template") or {}).get("containers") or []
        if containers:
            for e in containers[0].get("env") or []:
                if e.get("name") and "value" in e:
                    env[str(e["name"])] = str(e.get("value") or "")
    except Exception:
        env = {}
    return {
        "status": "applied",
        "service": service,
        "url": _service_url(payload),
        "env": env,
        "raw_name": payload.get("name"),
        "payload": payload,
    }


def wire_cloud_run_env(
    service: str,
    *,
    env_updates: dict[str, str],
    project: str = "",
    region: str = "",
) -> dict[str, Any]:
    """Merge plain env vars onto the Cloud Run service (new revision)."""
    proj = project or _project()
    reg = region or _region()
    path = f"projects/{proj}/locations/{reg}/services/{service}"
    st, current = _run_api("GET", path)
    if st != 200 or not isinstance(current, dict):
        return {
            "status": "skipped",
            "connector": "cloudrun.wire",
            "detail": f"cannot read service {service}: {st} {current}",
            "hint": "Grant the Product OS runtime SA roles/run.developer on the project (or run.services.get/update on this service).",
        }

    template = dict(current.get("template") or {})
    containers = [dict(c) for c in (template.get("containers") or [])]
    if not containers:
        return {
            "status": "skipped",
            "connector": "cloudrun.wire",
            "detail": "service has no containers",
        }

    existing_rows = list(containers[0].get("env") or [])
    by_name: dict[str, dict] = {}
    for row in existing_rows:
        n = row.get("name")
        if n:
            by_name[str(n)] = dict(row)

    already = True
    for key, val in env_updates.items():
        if not key:
            continue
        prev = by_name.get(key) or {}
        if prev.get("valueSource") or prev.get("secretKeyRef"):
            # Do not overwrite secret-backed vars
            continue
        if str(prev.get("value") or "") != str(val):
            already = False
        by_name[key] = {"name": key, "value": str(val)}

    if already and all(k in by_name for k in env_updates if k):
        return {
            "status": "reused",
            "connector": "cloudrun.wire",
            "detail": f"{service} already has matching LOOP_* env",
            "url": _service_url(current),
            "service": service,
        }

    containers[0]["env"] = list(by_name.values())
    template["containers"] = containers
    body = {**current, "template": template}
    st2, updated = _run_api("PATCH", f"{path}?updateMask=template", body)
    if st2 not in {200, 201} or not isinstance(updated, dict):
        return {
            "status": "skipped",
            "connector": "cloudrun.wire",
            "detail": f"update {st2}: {updated}",
            "url": _service_url(current),
            "hint": "Grant roles/run.developer (or run.services.update) to the Product OS service account.",
            "manual": (
                f"gcloud run services update {service} --region={reg} --project={proj} "
                f"--update-env-vars=LOOP_OS_URL={env_updates.get('LOOP_OS_URL','')},"
                f"LOOP_TENANT_ID={env_updates.get('LOOP_TENANT_ID','')},"
                f"LOOP_TENANT_TOKEN=…"
            ),
        }
    return {
        "status": "applied",
        "connector": "cloudrun.wire",
        "detail": f"Wired env on {service} (new revision)",
        "url": _service_url(updated) or _service_url(current),
        "service": service,
    }


def mint_tenant_token() -> str:
    return secrets.token_urlsafe(32)


def _slug_tenant_id(service: str, explicit: str = "") -> str:
    if explicit.strip():
        return re.sub(r"[^a-z0-9\-]", "-", explicit.strip().lower())[:64].strip("-") or "tenant"
    base = re.sub(r"[^a-z0-9\-]", "-", (service or "tenant").strip().lower().replace("_", "-"))
    return (base[:64].strip("-") or "tenant")


def _merge_tenant(prev: Tenant | None, *, tid: str, name: str, product: str, repo: str, deploy_url: str, token_hash: str) -> Tenant:
    return Tenant(
        id=tid,
        name=name,
        product=product,
        repo=repo,
        deploy_url=deploy_url,
        token_hash=token_hash,
        connected=True,
        last_pr_url=prev.last_pr_url if prev else "",
        last_ingest_at=prev.last_ingest_at if prev else "",
        last_connector="onboard.wire",
        metric_catalog=prev.metric_catalog if prev else [],
        flag_names=prev.flag_names if prev else ["pay_sdk_4_3", "pay_sdk"],
        code_paths=prev.code_paths if prev else [],
        flag_file_path=prev.flag_file_path if prev else "config/flags.json",
        stack=prev.stack if prev else "",
        test_command=prev.test_command if prev else "",
        default_surface=prev.default_surface if prev else "product",
        bq_project=prev.bq_project if prev else _project(),
        bq_raw_dataset=prev.bq_raw_dataset if prev else "",
        bq_metrics_dataset=prev.bq_metrics_dataset if prev else "",
        ga4_property_id=prev.ga4_property_id if prev else "",
        ga4_dataset=prev.ga4_dataset if prev else "",
        ads_dataset=prev.ads_dataset if prev else "",
        ads_customer_id=prev.ads_customer_id if prev else "",
        warehouse_mode=prev.warehouse_mode if prev else "auto",
        primary_metric=prev.primary_metric if prev else "purchase_conversion",
        funnel_events=list(prev.funnel_events) if prev and prev.funnel_events else [],
    )


def onboard_tenant(
    store: Any,
    *,
    cloud_run_service: str = "",
    repo: str,
    region: str = "",
    project: str = "",
    tenant_id: str = "",
    name: str = "",
    product: str = "",
    deploy_url: str = "",
    wire: bool = True,
) -> dict[str, Any]:
    """Create/update tenant, mint token, optionally push env to Cloud Run."""
    service = cloud_run_service.strip()
    if not service and not deploy_url.strip():
        return {"status": "skipped", "detail": "cloud_run_service or deploy_url required"}
    if not repo.strip():
        return {"status": "skipped", "detail": "repo required (org/name)"}

    tid = _slug_tenant_id(service or tenant_id or "product", tenant_id)
    prev = store.get_tenant(tid)
    desc: dict[str, Any] = {"status": "skipped", "detail": "no Cloud Run service"}
    url = deploy_url.strip()
    if service:
        desc = describe_cloud_run_service(service, project=project, region=region)
        if desc.get("status") == "applied" and not url:
            url = str(desc.get("url") or "")

    os_url = _public_os_url()
    raw_token = mint_tenant_token()
    display_name = name.strip() or (prev.name if prev else (service or tid).replace("-", " ").title())
    product_name = product.strip() or (prev.product if prev else display_name)

    tenant = _merge_tenant(
        prev,
        tid=tid,
        name=display_name,
        product=product_name,
        repo=repo.strip(),
        deploy_url=url or (prev.deploy_url if prev else ""),
        token_hash=hash_token(raw_token),
    )
    store.put_tenant(tenant)

    wire_report: dict[str, Any] = {"status": "skipped", "detail": "wire not requested"}
    if wire and service:
        if not os_url:
            wire_report = {
                "status": "skipped",
                "connector": "cloudrun.wire",
                "detail": "LOOP_PUBLIC_URL unset — Product Y cannot call Product OS",
            }
        else:
            wire_report = wire_cloud_run_env(
                service,
                project=project,
                region=region,
                env_updates={
                    "LOOP_OS_URL": os_url,
                    "LOOP_TENANT_ID": tid,
                    "LOOP_TENANT_TOKEN": raw_token,
                },
            )
            if wire_report.get("url") and not tenant.deploy_url:
                tenant.deploy_url = str(wire_report["url"])
                store.put_tenant(tenant)
            if wire_report.get("status") in {"applied", "reused"}:
                tenant.last_connector = f"cloudrun.wire {wire_report['status']}"
                store.put_tenant(tenant)
    elif wire and not service:
        wire_report = {
            "status": "skipped",
            "connector": "cloudrun.wire",
            "detail": "No Cloud Run service — tenant registered; set LOOP_* on Product Y yourself",
            "env": {
                "LOOP_OS_URL": os_url or "",
                "LOOP_TENANT_ID": tid,
                "LOOP_TENANT_TOKEN": "(shown once below)",
            },
        }

    wired = wire_report.get("status") in {"applied", "reused"}
    overall = "applied" if (wired or not wire or not service) and tenant.repo else "partial"

    return {
        "status": overall,
        "tenant_id": tid,
        "tenant": {k: v for k, v in tenant.model_dump().items() if k != "token_hash"}
        | {"has_token": True},
        "token": raw_token,
        "token_once": True,
        "os_url": os_url or None,
        "cloud_run": {k: v for k, v in desc.items() if k != "payload"},
        "wire": wire_report,
        "next": [
            "Run verify",
            "Optional: Authorize Google Workspace",
            "Send product traffic or feedback to open rooms",
        ],
    }


def _tenant_flags(store: Any, tenant_id: str) -> dict[str, str]:
    raw = store.list_flags()
    return {k.split(":", 2)[-1]: v for k, v in raw.items() if k.startswith(f"t:{tenant_id}:")}


def verify_tenant(engine: Any, tenant_id: str) -> dict[str, Any]:
    """Checklist: tenant record, product flags proxy, ingest smoke, GitHub readiness."""
    t = engine.store.get_tenant(tenant_id)
    if not t:
        return {"status": "skipped", "detail": "tenant not found", "checks": []}

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "tenant_record",
            "ok": bool(t.repo and t.connected),
            "label": "Tenant registered",
            "detail": f"repo={t.repo or '(none)'} deploy={t.deploy_url or '(none)'}",
        }
    )
    checks.append(
        {
            "id": "token",
            "ok": bool(t.token_hash),
            "label": "Tenant token hashed",
            "detail": "Token is stored hashed only",
        }
    )

    flags = _tenant_flags(engine.store, tenant_id)
    checks.append(
        {
            "id": "flags_os",
            "ok": True,
            "label": "Flags available on Product OS",
            "detail": f"{len(flags)} flags",
            "flags": flags,
        }
    )

    product_flags_ok = False
    product_detail = "no deploy_url"
    if t.deploy_url:
        try:
            req = urllib.request.Request(
                f"{t.deploy_url.rstrip('/')}/api/loop/flags",
                headers={"User-Agent": "product-os-loop"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode() or "{}"
                body = json.loads(raw)
                product_flags_ok = resp.status == 200 and isinstance(body, dict)
                product_detail = f"HTTP {resp.status} from product /api/loop/flags"
        except Exception as exc:
            product_detail = str(exc)[:200]
    checks.append(
        {
            "id": "flags_product",
            "ok": product_flags_ok,
            "label": "Product app can read flags",
            "detail": product_detail,
        }
    )

    room_id = None
    try:
        from loop.world import ingest_tenant_signal

        out = ingest_tenant_signal(
            engine,
            t,
            metric="onboard_verify",
            magnitude=-0.01,
            baseline=0.5,
            note="Onboard verify ping",
            source="onboard.verify",
        )
        room_id = out.get("room_id")
        checks.append(
            {
                "id": "ingest",
                "ok": bool(room_id),
                "label": "Signal ingest opens a room",
                "detail": f"room={room_id}" if room_id else "no room",
                "room_id": room_id,
            }
        )
    except Exception as exc:
        checks.append(
            {
                "id": "ingest",
                "ok": False,
                "label": "Signal ingest opens a room",
                "detail": str(exc)[:200],
            }
        )

    github_ok = bool(os.environ.get("LOOP_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    checks.append(
        {
            "id": "github",
            "ok": github_ok and bool(t.repo),
            "label": "GitHub ready for PR on approve",
            "detail": "LOOP_GITHUB_TOKEN set" if github_ok else "No GitHub token on Product OS",
        }
    )

    ok_count = sum(1 for c in checks if c.get("ok"))
    # Core path: tenant + token + ingest; product flags is strongly preferred
    ready = bool(t.repo and t.token_hash and room_id)
    return {
        "status": "applied" if ready else "partial",
        "tenant_id": tenant_id,
        "checks": checks,
        "ok": ok_count,
        "total": len(checks),
        "room_id": room_id,
        "ready_for_demo": ready,
        "ready": ready,
    }
