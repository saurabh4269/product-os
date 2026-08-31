"""Trust surfaces — real connector payloads rendered in the UI (not fake iframes).

GitHub / BigQuery / GA4 consoles block embedding. We show the same data the agents
read, shaped like those tools, with deep links to open the real console.

When a tenant has BQ/GA4 datasets configured, panels prefer live connectors.
File warehouse is only used when warehouse_mode=file or no live config exists.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Any

from loop.tenant import Tenant


def _console_bq_url(project: str, dataset: str = "", table: str = "") -> str:
    base = f"https://console.cloud.google.com/bigquery?project={project}"
    if dataset and table:
        return f"{base}&ws=!1m5!1m4!4m3!1s{project}!2s{dataset}!3s{table}"
    if dataset:
        return f"{base}&ws=!1m4!1m3!3m2!1s{project}!2s{dataset}"
    return base


def _console_ga4_url(property_id: str) -> str:
    pid = (property_id or "").strip()
    if not pid:
        return "https://analytics.google.com/"
    return f"https://analytics.google.com/analytics/web/#/p{pid}/reports/intelligenthome"


def _live_window(*, days: int = 7) -> tuple[date, date]:
    """Rolling window for trust panels — not the Safari fixture RECOVERY clamp."""
    end = date.today()
    start = end - timedelta(days=max(1, days))
    return start, end


def _browser_rows(conv: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for browser, vals in sorted(conv.items(), key=lambda kv: -float(kv[1].get("purchase") or 0)):
        rows.append(
            {
                "browser": browser,
                "begin_checkout": int(vals.get("begin_checkout") or 0),
                "purchase": int(vals.get("purchase") or 0),
                "conversion": round(float(vals.get("conversion") or 0), 4),
            }
        )
    return rows


def _file_warehouse_rows(engine: Any, start: date, end: date) -> list[dict[str, Any]]:
    wh = getattr(engine, "wh", None)
    if not wh or not hasattr(wh, "conversion_by_browser"):
        return []
    try:
        conv = wh.conversion_by_browser(start, end) or {}
        return _browser_rows(conv)
    except Exception:
        return []


def warehouse_proof(
    engine: Any,
    tenant: Tenant | None,
    *,
    metric: str = "purchase_conversion",
    baseline: float | None = None,
    prefer: str = "",
    days: int = 7,
) -> dict[str, Any]:
    """Live table the UI can render like a BQ / GA4 results pane."""
    from loop.connectors.bigquery import (
        conversion_probe,
        has_bq,
        metrics_daily_rows,
        read_metric_window,
        resolve_bq_config,
    )
    from loop.warehouse import RECOVERY_START

    if not tenant:
        return {
            "kind": "warehouse",
            "status": "skipped",
            "title": "Warehouse",
            "detail": "No tenant bound",
            "rows": [],
            "columns": [],
        }

    cfg = resolve_bq_config(tenant)
    reading = read_metric_window(engine, tenant, metric, baseline=baseline)
    start, end = _live_window(days=days)

    rows: list[dict[str, Any]] = []
    sql = ""
    source = "file_warehouse"
    project = ""
    dataset = ""
    table = ""
    console_url = ""
    columns = ["browser", "begin_checkout", "purchase", "conversion"]
    connector_error: str | None = None
    used_live = False

    if cfg and has_bq(tenant):
        project = cfg.project
        probe = conversion_probe(tenant, start, end, include_recovery=True, prefer=prefer)
        conv = probe.get("rows") or {}
        if conv:
            used_live = True
            source = str(probe.get("source") or "bigquery")
            dataset = str(probe.get("dataset") or "")
            table = str(probe.get("table") or "")
            rows = _browser_rows(conv)
        else:
            connector_error = probe.get("error")
            # Prefer metrics_daily when browser aggregate is empty but BQ is configured
            metric_rows = metrics_daily_rows(tenant, metric, limit=14)
            if metric_rows:
                used_live = True
                source = "bigquery.metrics_daily"
                dataset = cfg.metrics_dataset
                table = "metrics_daily"
                columns = ["day", "value"]
                rows = [
                    {
                        "day": str(r.get("day") or ""),
                        "value": round(float(r.get("value") or 0), 6),
                    }
                    for r in metric_rows
                ]
            else:
                # Keep live identity even when empty — do not silently switch to file
                source = str(probe.get("source") or ("ga4_export" if cfg.ga4_dataset and (prefer == "ga4" or cfg.warehouse_mode in {"auto", "ga4"}) else "bigquery"))
                dataset = str(probe.get("dataset") or cfg.ga4_dataset or cfg.raw_dataset or cfg.metrics_dataset)
                table = str(probe.get("table") or ("events_*" if "ga4" in source else "events"))
                used_live = True

        if source == "ga4_export":
            sql = (
                f"SELECT device.web_info.browser AS browser,\n"
                f"  COUNTIF(event_name = 'begin_checkout') AS begin_checkout,\n"
                f"  COUNTIF(event_name = 'purchase') AS purchase\n"
                f"FROM `{project}.{dataset or cfg.ga4_dataset}.events_*`\n"
                f"WHERE _TABLE_SUFFIX BETWEEN '{start.strftime('%Y%m%d')}' "
                f"AND '{end.strftime('%Y%m%d')}'\n"
                f"GROUP BY browser"
            )
            console_url = (
                _console_ga4_url(tenant.ga4_property_id)
                if tenant.ga4_property_id
                else _console_bq_url(project, dataset or cfg.ga4_dataset)
            )
        elif source == "bigquery.metrics_daily":
            sql = (
                f"SELECT day, value FROM `{project}.{dataset}.metrics_daily`\n"
                f"WHERE tenant_id = '{tenant.id}' AND metric = '{metric}'\n"
                f"ORDER BY day DESC LIMIT 14"
            )
            console_url = _console_bq_url(project, dataset, table)
        else:
            sql = (
                f"SELECT browser,\n"
                f"  SUM(IF(event_name='begin_checkout',1,0)) AS begin_checkout,\n"
                f"  SUM(IF(event_name='purchase',1,0)) AS purchase\n"
                f"FROM `{project}.{dataset or cfg.raw_dataset}.events`\n"
                f"WHERE event_date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'\n"
                f"GROUP BY browser"
            )
            console_url = _console_bq_url(project, dataset or cfg.raw_dataset, table or "events")

    # File warehouse only when the tenant is not on live BQ/GA4
    if not used_live:
        source = "file_warehouse"
        # Fixture tables use the regression window so demo numbers stay non-empty
        f_end = end
        if f_end >= RECOVERY_START:
            f_end = RECOVERY_START - timedelta(days=1)
        f_start = f_end - timedelta(days=2)
        start, end = f_start, f_end
        sql = "-- file warehouse (events_daily) · same tables the detect loop reads"
        rows = _file_warehouse_rows(engine, start, end)
        columns = ["browser", "begin_checkout", "purchase", "conversion"]

    title = {
        "ga4_export": "GA4 → BigQuery export",
        "bigquery": "BigQuery",
        "bigquery.metrics_daily": "BigQuery metrics_daily",
        "file_warehouse": "Warehouse (demo tables)",
    }.get(source, "Warehouse")

    claim = (reading or {}).get("claim") if reading else None
    detail = claim or (f"{len(rows)} rows" if rows else (connector_error or "No rows in window"))
    # Prefer honest connector detail over a metrics claim when the table is empty
    if used_live and not rows and connector_error:
        detail = connector_error

    return {
        "kind": "ga4" if source == "ga4_export" else "warehouse",
        "status": "applied" if rows else ("empty" if used_live else "empty"),
        "title": title,
        "subtitle": f"{metric} · {start.isoformat()} → {end.isoformat()}",
        "detail": detail,
        "source": source,
        "live": used_live,
        "project": project or (os.environ.get("GOOGLE_CLOUD_PROJECT") or ""),
        "dataset": dataset,
        "table": table,
        "sql": sql,
        "columns": columns,
        "rows": rows[:14],
        "reading": reading,
        "console_url": console_url
        or (
            _console_ga4_url(tenant.ga4_property_id)
            if tenant.ga4_property_id
            else (_console_bq_url(project) if project else "")
        ),
        "metric": metric,
        "baseline": baseline,
        "error": connector_error,
    }


def ga4_proof(
    engine: Any,
    tenant: Tenant | None,
    *,
    metric: str = "purchase_conversion",
) -> dict[str, Any] | None:
    """Dedicated GA4 panel when property/dataset is configured."""
    if not tenant:
        return None
    if not (tenant.ga4_property_id or tenant.ga4_dataset):
        return None
    # Force GA4 path when dataset exists; property-only still gets a deep link shell
    if tenant.ga4_dataset:
        out = warehouse_proof(engine, tenant, metric=metric, prefer="ga4")
    else:
        out = {
            "kind": "ga4",
            "status": "skipped",
            "title": "GA4",
            "detail": "Property linked — set ga4_dataset for export rows",
            "rows": [],
            "columns": [],
            "source": "ga4",
            "live": False,
            "property_id": tenant.ga4_property_id,
            "console_url": _console_ga4_url(tenant.ga4_property_id),
        }
    out = {
        **out,
        "kind": "ga4",
        "title": out.get("title") if out.get("source") == "ga4_export" else "Google Analytics",
        "console_url": _console_ga4_url(tenant.ga4_property_id or "") or out.get("console_url"),
        "property_id": tenant.ga4_property_id or "",
    }
    return out


def github_pr_proof(pr_url: str, *, tenant: Tenant | None = None) -> dict[str, Any]:
    """Fetch live PR metadata for an inline GitHub-style card."""
    from loop.connectors.github import _request, token_for_tenant

    url = (pr_url or "").strip()
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        return {
            "kind": "github",
            "status": "skipped",
            "title": "GitHub",
            "detail": "Not a pull request URL",
            "url": url or None,
        }
    owner, repo, number = m.group(1), m.group(2), m.group(3)
    full = f"{owner}/{repo}"
    token = token_for_tenant(tenant)
    if not token:
        return {
            "kind": "github",
            "status": "skipped",
            "title": f"PR #{number}",
            "subtitle": f"{full}#{number}",
            "detail": "No GitHub token — open the PR on GitHub",
            "url": url,
            "console_url": url,
            "repo": full,
            "number": int(number),
            "state": "open",
            "live": False,
        }
    st, pr = _request("GET", f"https://api.github.com/repos/{full}/pulls/{number}", token)
    if st != 200:
        return {
            "kind": "github",
            "status": "skipped",
            "title": f"PR #{number}",
            "detail": f"GitHub API {st}",
            "url": url,
            "repo": full,
            "number": int(number),
            "live": False,
        }
    files: list[dict[str, Any]] = []
    st_f, file_rows = _request("GET", f"https://api.github.com/repos/{full}/pulls/{number}/files", token)
    if st_f == 200 and isinstance(file_rows, list):
        for f in file_rows[:8]:
            files.append(
                {
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                }
            )
    return {
        "kind": "github",
        "status": "applied",
        "title": pr.get("title") or f"PR #{number}",
        "subtitle": f"{full}#{number} · {pr.get('user', {}).get('login') or ''}",
        "detail": (pr.get("body") or "")[:280],
        "url": pr.get("html_url") or url,
        "repo": full,
        "number": int(number),
        "state": pr.get("state"),
        "draft": bool(pr.get("draft")),
        "merged": bool(pr.get("merged")),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "changed_files": pr.get("changed_files"),
        "head": (pr.get("head") or {}).get("ref"),
        "base": (pr.get("base") or {}).get("ref"),
        "files": files,
        "console_url": pr.get("html_url") or url,
        "live": True,
        "source": "github.api",
    }


def mail_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    rep = artifact.get("report") if isinstance(artifact.get("report"), dict) else {}
    return {
        "kind": "gmail",
        "status": rep.get("status") or artifact.get("channel") or "skipped",
        "title": artifact.get("subject") or "Mail",
        "subtitle": artifact.get("to") or "",
        "detail": rep.get("detail") or artifact.get("channel") or "",
        "url": artifact.get("gmail_url") or rep.get("url"),
        "console_url": artifact.get("gmail_url") or rep.get("url"),
        "to": artifact.get("to"),
        "channel": artifact.get("channel"),
    }


def enrich_card_proof(store: Any, card: dict[str, Any], engine: Any | None = None) -> dict[str, Any]:
    """Attach a proof block to a live-work card when we can resolve one."""
    if card.get("proof"):
        return card
    art_type = (card.get("artifact_type") or "").lower()
    pr_url = card.get("pr_url")
    if pr_url or art_type in {"pr", "code"}:
        if pr_url:
            room = store.get_room(card.get("room_id") or "")
            tenant = store.get_tenant(room.tenant_id) if room and room.tenant_id else None
            card["proof"] = github_pr_proof(str(pr_url), tenant=tenant)
            return card
    if art_type in {"warehouse", "bq", "analytics", "metric", "ga4"} and engine is not None:
        room = store.get_room(card.get("room_id") or "")
        tenant = store.get_tenant(room.tenant_id) if room and room.tenant_id else None
        if not tenant:
            tenants = store.list_tenants()
            tenant = next((t for t in tenants if t.repo), tenants[0] if tenants else None)
        metric = str(card.get("metric") or "purchase_conversion")
        prefer = "ga4" if art_type == "ga4" else ""
        card["proof"] = warehouse_proof(engine, tenant, metric=metric, prefer=prefer)
        return card
    if art_type in {"mail", "gmail"}:
        return card
    return card


def _find_pr_url(engine: Any, tenant: Tenant | None) -> str | None:
    if tenant and tenant.last_pr_url:
        return tenant.last_pr_url
    # Approvals / actions with execution.pr_url
    try:
        for action in engine.store.list_actions() if hasattr(engine.store, "list_actions") else []:
            arts = action.artifacts or {}
            exe = arts.get("execution") if isinstance(arts.get("execution"), dict) else {}
            url = exe.get("pr_url") or arts.get("pr_url")
            if isinstance(url, str) and "/pull/" in url:
                return url
    except Exception:
        pass
    for room in engine.store.list_rooms():
        for msg in reversed(engine.store.list_messages(room.id)):
            art = msg.artifact if isinstance(msg.artifact, dict) else {}
            url = art.get("pr_url") or art.get("url")
            if isinstance(url, str) and "github.com" in url and "/pull/" in url:
                return url
    return None


def logs_proof(tenant: Tenant | None) -> dict[str, Any]:
    """Error concentration from loop_raw.logs (or honest empty)."""
    from loop.connectors.bigquery import error_summary, resolve_bq_config

    if not tenant:
        return {
            "kind": "logs",
            "status": "skipped",
            "title": "Logs",
            "detail": "No tenant",
            "rows": [],
            "columns": [],
        }
    cfg = resolve_bq_config(tenant)
    project = (cfg.project if cfg else "") or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
    dataset = (cfg.raw_dataset if cfg else "") or ""
    summary = error_summary(tenant) if cfg else {}
    counts = summary.get("counts") or {}
    rows = [{"service": k, "errors": v} for k, v in list(counts.items())[:8]]
    return {
        "kind": "logs",
        "status": "applied" if rows else ("empty" if cfg else "skipped"),
        "title": "Error logs",
        "subtitle": summary.get("claim") or (f"{project}.{dataset}.logs" if dataset else "loop_raw.logs"),
        "detail": summary.get("claim") or ("No ERROR rows in window" if cfg else "Configure BQ raw dataset"),
        "source": summary.get("source") or ("bigquery.logs" if cfg else "none"),
        "live": bool(rows),
        "project": project,
        "dataset": dataset,
        "table": "logs",
        "sql": (
            f"SELECT service, COUNT(*) AS errors\nFROM `{project}.{dataset}.logs`\n"
            f"WHERE level IN ('ERROR','error')\nGROUP BY service ORDER BY errors DESC"
            if project and dataset
            else ""
        ),
        "columns": ["service", "errors"],
        "rows": rows,
        "console_url": _console_bq_url(project, dataset, "logs") if project and dataset else "",
    }


def deploys_proof(tenant: Tenant | None) -> dict[str, Any]:
    from loop.connectors.bigquery import recent_deploy, resolve_bq_config

    if not tenant:
        return {"kind": "deploys", "status": "skipped", "title": "Deploys", "rows": [], "columns": []}
    cfg = resolve_bq_config(tenant)
    project = (cfg.project if cfg else "") or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""
    dataset = (cfg.raw_dataset if cfg else "") or ""
    dep = recent_deploy(tenant) if cfg else {}
    rows = []
    if dep:
        rows.append(
            {
                "service": dep.get("service") or "app",
                "version": dep.get("version") or "?",
                "deployed_at": str(dep.get("deployed_at") or "")[:19],
            }
        )
    return {
        "kind": "deploys",
        "status": "applied" if rows else ("empty" if cfg else "skipped"),
        "title": "Recent deploy",
        "subtitle": dep.get("claim") or "Release correlation",
        "detail": dep.get("claim") or ("No deploys table rows" if cfg else "Configure BQ raw dataset"),
        "source": "bigquery.deploys" if rows else "none",
        "live": bool(rows),
        "project": project,
        "dataset": dataset,
        "table": "deploys",
        "columns": ["service", "version", "deployed_at"],
        "rows": rows,
        "console_url": _console_bq_url(project, dataset, "deploys") if project and dataset else "",
    }


def ads_proof(tenant: Tenant | None) -> dict[str, Any]:
    from loop.connectors.bigquery import ads_attribution, resolve_bq_config

    if not tenant:
        return {"kind": "ads", "status": "skipped", "title": "Ads", "rows": [], "columns": []}
    cfg = resolve_bq_config(tenant)
    project = (cfg.project if cfg else "") or ""
    dataset = ((cfg.ads_dataset or cfg.raw_dataset) if cfg else "") or ""
    ads = ads_attribution(tenant) if cfg else {}
    rows = []
    for r in ads.get("rows") or []:
        rows.append(
            {
                "campaign": r.get("campaign_name") or r.get("campaign") or "—",
                "channel": r.get("channel") or "—",
                "spend": round(float(r.get("spend") or r.get("cost") or 0), 2),
            }
        )
    if not rows and ads.get("campaign"):
        rows.append(
            {
                "campaign": ads.get("campaign"),
                "channel": ads.get("channel") or "—",
                "spend": round(float(ads.get("spend") or 0), 2),
            }
        )
    return {
        "kind": "ads",
        "status": "applied" if rows else ("empty" if cfg else "skipped"),
        "title": "Ads attribution",
        "subtitle": ads.get("claim") or "Acquisition spend",
        "detail": ads.get("claim") or ("No campaign_daily rows" if cfg else "Configure ads/raw dataset"),
        "source": ads.get("source") or "none",
        "live": bool(rows),
        "project": project,
        "dataset": dataset,
        "columns": ["campaign", "channel", "spend"],
        "rows": rows[:8],
        "console_url": _console_bq_url(project, dataset) if project and dataset else "",
    }


def contacts_proof(engine: Any, *, room_id: str = "") -> dict[str, Any]:
    """Callback phone lookup — the search customer voice runs before dialing."""
    from loop.customer_contact import resolve_callback_phone

    store = engine.store
    rid = room_id
    if not rid:
        for room in store.list_rooms():
            status = room.status.value if hasattr(room.status, "value") else str(room.status)
            if status != "open":
                continue
            hit = resolve_callback_phone(store, room.id)
            if hit.get("found"):
                rid = room.id
                break
    lookup = resolve_callback_phone(store, rid or "")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for payload in reversed(store.list_memory(kind="customer")):
        phone = ""
        for key in ("phone", "callback_phone", "to_number", "mobile"):
            raw = payload.get(key)
            if isinstance(raw, str) and raw.strip():
                phone = raw.strip()
                break
        if not phone or phone in seen:
            continue
        seen.add(phone)
        rows.append({"phone": phone, "source": "memory", "note": str(payload.get("text") or "")[:80]})
        if len(rows) >= 6:
            break
    if lookup.get("found") and lookup.get("phone"):
        rows = [
            {
                "phone": lookup["phone"],
                "source": lookup.get("source") or "room",
                "note": (lookup.get("feedback") or lookup.get("detail") or "")[:80],
            }
        ] + [r for r in rows if r.get("phone") != lookup.get("phone")]
    return {
        "kind": "contacts",
        "status": "applied" if rows else "empty",
        "title": "Callback lookup",
        "subtitle": lookup.get("detail") or "Cove feedback → memory",
        "detail": lookup.get("detail") or "No callback numbers on file",
        "source": "customer_contact",
        "live": bool(rows),
        "columns": ["phone", "source", "note"],
        "rows": rows[:8],
        "phone": lookup.get("phone"),
        "found": bool(lookup.get("found")),
        "console_url": "/connect",
    }


def memory_proof(engine: Any) -> dict[str, Any]:
    rows = []
    for lesson in list(engine.store.list_lessons())[-8:]:
        d = lesson.model_dump(mode="json") if hasattr(lesson, "model_dump") else {}
        cond = d.get("applicable_conditions") or []
        rows.append(
            {
                "lesson": str(d.get("statement") or "Lesson")[:72],
                "when": str(d.get("root_cause_family") or (cond[0] if cond else ""))[:24],
            }
        )
    return {
        "kind": "memory",
        "status": "applied" if rows else "empty",
        "title": "Organizational memory",
        "subtitle": f"{len(rows)} recent lessons",
        "detail": "Lessons the learning agent writes after verify",
        "source": "store.lessons",
        "live": bool(rows),
        "columns": ["lesson", "when"],
        "rows": list(reversed(rows))[:8],
        "console_url": "/memory",
    }


def flags_proof(engine: Any, tenant: Tenant | None) -> dict[str, Any]:
    tid = tenant.id if tenant else ""
    raw = engine.store.list_flags()
    rows = []
    for k, v in sorted(raw.items()):
        if tid and k.startswith(f"t:{tid}:"):
            rows.append({"flag": k.split(":", 2)[-1], "value": v})
        elif not tid and not k.startswith("t:"):
            rows.append({"flag": k, "value": v})
    if not rows and tid:
        for k, v in sorted(raw.items()):
            if not k.startswith("t:"):
                rows.append({"flag": k, "value": v})
    return {
        "kind": "flags",
        "status": "applied" if rows else "empty",
        "title": "Feature flags",
        "subtitle": tenant.product if tenant else "OS flags",
        "detail": f"{len(rows)} flags" if rows else "No flags set",
        "source": "store.flags",
        "live": bool(rows),
        "columns": ["flag", "value"],
        "rows": rows[:12],
        "console_url": "/connect",
    }


def workspace_proof() -> dict[str, Any]:
    try:
        from loop.connectors import google_oauth

        st = google_oauth.status()
    except Exception:
        st = {"connected": False, "configured": False}
    connected = bool(st.get("connected"))
    return {
        "kind": "workspace",
        "status": "applied" if connected else "skipped",
        "title": "Google Workspace",
        "subtitle": st.get("email") or ("Connected" if connected else "Not authorized"),
        "detail": "Calendar holds + Gmail self-send when authorized"
        if connected
        else "Authorize on Connect for mail/calendar",
        "source": "google_oauth",
        "live": connected,
        "email": st.get("email"),
        "console_url": "/connect",
        "columns": ["capability", "status"],
        "rows": [
            {"capability": "Gmail draft/self", "status": "yes" if connected else "no"},
            {"capability": "Calendar hold", "status": "yes" if connected else "no"},
        ],
    }


def gateway_proof(engine: Any) -> dict[str, Any]:
    rows = []
    try:
        for v in list(engine.store.list_verdicts())[-8:]:
            d = v.model_dump(mode="json") if hasattr(v, "model_dump") else {}
            rows.append(
                {
                    "decision": str(d.get("verdict") or d.get("decision") or "—")[:40],
                    "agent": str(d.get("agent_identity") or d.get("agent_id") or "")[:24],
                    "detail": str(d.get("rationale") or d.get("tool") or "")[:60],
                }
            )
    except Exception:
        pass
    return {
        "kind": "gateway",
        "status": "applied" if rows else "empty",
        "title": "Gateway / policy",
        "subtitle": "Identity DENY · fail_open=false",
        "detail": f"{len(rows)} recent verdicts" if rows else "No verdicts yet — exfil path stays DENY",
        "source": "store.verdicts",
        "live": bool(rows),
        "columns": ["decision", "agent", "detail"],
        "rows": list(reversed(rows))[:8],
        "console_url": "/governance",
    }


def _primary_tenant(engine: Any) -> Tenant | None:
    tenants = engine.store.list_tenants()
    return next((t for t in tenants if t.connected or t.repo), tenants[0] if tenants else None)


def all_resource_cards(engine: Any) -> list[dict[str, Any]]:
    tenant = _primary_tenant(engine)
    warehouse = warehouse_proof(engine, tenant, prefer="raw")
    ga4 = ga4_proof(engine, tenant)
    github = None
    pr = _find_pr_url(engine, tenant)
    if pr:
        github = github_pr_proof(pr, tenant=tenant)
    cards = [
        ga4,
        warehouse,
        logs_proof(tenant),
        deploys_proof(tenant),
        ads_proof(tenant),
        contacts_proof(engine),
        github,
        flags_proof(engine, tenant),
        memory_proof(engine),
        workspace_proof(),
        gateway_proof(engine),
    ]
    out = []
    for c in cards:
        if not c:
            continue
        if c.get("live") or c.get("rows") or c.get("kind") in {
            "ga4",
            "warehouse",
            "github",
            "contacts",
            "workspace",
            "logs",
            "deploys",
            "ads",
            "flags",
            "memory",
            "gateway",
        }:
            out.append(c)
    return out


_AGENT_RESOURCE_KEYS: dict[str, list[str]] = {
    "signal_agent": ["ga4", "warehouse", "ads", "contacts"],
    "analytics_agent": ["ga4", "warehouse", "ads"],
    "database_agent": ["warehouse", "ga4"],
    "logs_agent": ["logs", "deploys"],
    "deployment_agent": ["deploys", "github"],
    "investigator_agent": ["ga4", "warehouse", "logs", "deploys", "contacts"],
    "evidence_agent": ["warehouse", "logs", "ga4"],
    "customer_voice_agent": ["contacts", "workspace"],
    "feedback_agent": ["contacts", "warehouse", "memory"],
    "consent_agent": ["contacts", "gateway"],
    "code_agent": ["github", "flags"],
    "test_agent": ["github"],
    "product_agent": ["github", "warehouse", "workspace"],
    "experiment_agent": ["flags", "warehouse", "ga4"],
    "learning_agent": ["warehouse", "memory", "ga4"],
    "coordination_agent": ["workspace"],
    "product_intelligence_agent": ["workspace", "memory"],
    "security_policy_agent": ["gateway", "flags"],
    "risk_agent": ["gateway", "flags"],
    "root_cause_agent": ["warehouse", "logs", "memory"],
    "decision_agent": ["memory", "gateway"],
    "orchestrator": ["warehouse", "github", "contacts", "gateway"],
}


def _catalog_for_engine(engine: Any) -> dict[str, dict[str, Any] | None]:
    tenant = _primary_tenant(engine)
    pr = _find_pr_url(engine, tenant)
    return {
        "warehouse": warehouse_proof(engine, tenant, prefer="raw"),
        "ga4": ga4_proof(engine, tenant),
        "github": github_pr_proof(pr, tenant=tenant)
        if pr
        else {
            "kind": "github",
            "status": "empty",
            "title": "GitHub PR",
            "detail": "No PR yet — approve a HIGH action to open one",
            "live": False,
            "console_url": f"https://github.com/{tenant.repo}" if tenant and tenant.repo else "",
            "rows": [],
            "columns": [],
        },
        "logs": logs_proof(tenant),
        "deploys": deploys_proof(tenant),
        "ads": ads_proof(tenant),
        "contacts": contacts_proof(engine),
        "flags": flags_proof(engine, tenant),
        "memory": memory_proof(engine),
        "workspace": workspace_proof(),
        "gateway": gateway_proof(engine),
    }


def agent_resources(engine: Any, agent_id: str) -> list[dict[str, Any]]:
    from loop.office import canonical_agent

    aid = canonical_agent(agent_id)
    keys = _AGENT_RESOURCE_KEYS.get(aid) or ["warehouse", "memory"]
    catalog = _catalog_for_engine(engine)
    return [{**catalog[k], "agent_id": aid, "resource_key": k} for k in keys if catalog.get(k)]


def signal_source_resources(engine: Any, side: str) -> list[dict[str, Any]]:
    catalog = _catalog_for_engine(engine)
    keys = ["contacts", "warehouse", "flags"] if side == "push" else ["ga4", "warehouse", "ads", "logs", "deploys"]
    return [{**catalog[k], "resource_key": k} for k in keys if catalog.get(k)]


def fanout_arm_resources(engine: Any, arm: str) -> list[dict[str, Any]]:
    mapping = {
        "Analytics": "analytics_agent",
        "Logs": "logs_agent",
        "Deploy": "deployment_agent",
        "Database": "database_agent",
        "Customer": "customer_voice_agent",
        "Code": "code_agent",
    }
    aid = mapping.get(arm)
    return agent_resources(engine, aid) if aid else []


def homepage_proofs(engine: Any) -> dict[str, Any]:
    """Bundle proofs for the homepage trust strip."""
    tenant = _primary_tenant(engine)
    warehouse = warehouse_proof(engine, tenant, prefer="")
    ga4 = ga4_proof(engine, tenant) if tenant else None
    if ga4 and warehouse.get("source") == "ga4_export" and ga4.get("source") == "ga4_export":
        raw = warehouse_proof(engine, tenant, prefer="raw")
        if raw.get("live") and raw.get("rows"):
            warehouse = raw
        elif not warehouse.get("rows") and raw.get("live"):
            warehouse = raw

    github = None
    pr_url = _find_pr_url(engine, tenant)
    if pr_url:
        github = github_pr_proof(pr_url, tenant=tenant)

    return {
        "warehouse": warehouse,
        "github": github,
        "ga4": ga4,
        "logs": logs_proof(tenant),
        "deploys": deploys_proof(tenant),
        "ads": ads_proof(tenant),
        "contacts": contacts_proof(engine),
        "flags": flags_proof(engine, tenant),
        "memory": memory_proof(engine),
        "workspace": workspace_proof(),
        "gateway": gateway_proof(engine),
        "cards": all_resource_cards(engine),
        "tenant_id": tenant.id if tenant else None,
        "tenant_product": tenant.product if tenant else None,
    }
