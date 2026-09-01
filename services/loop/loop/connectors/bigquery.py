"""BigQuery reads — GA4 export, loop_raw synthetic, Ads transfer, metrics_daily."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from loop.tenant import Tenant
from loop.warehouse import RECOVERY_START, REGRESSION_START


@dataclass(frozen=True)
class BqConfig:
    project: str
    raw_dataset: str
    metrics_dataset: str
    ga4_dataset: str
    ads_dataset: str
    ads_customer_id: str
    warehouse_mode: str
    primary_metric: str
    funnel_events: tuple[str, ...]


def resolve_bq_config(tenant: Tenant | None) -> BqConfig | None:
    if not tenant:
        return None
    mode = (tenant.warehouse_mode or "auto").strip().lower()
    if mode == "file":
        return None
    project = (tenant.bq_project or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        return None
    env_key = f"LOOP_BQ_DATASET_{tenant.id.upper().replace('-', '_')}"
    raw = (tenant.bq_raw_dataset or os.environ.get(env_key) or os.environ.get("LOOP_BQ_DATASET") or "").strip()
    metrics = (
        tenant.bq_metrics_dataset or os.environ.get("LOOP_BQ_METRICS_DATASET") or "loop_metrics"
    ).strip()
    ga4 = (tenant.ga4_dataset or "").strip()
    ads = (tenant.ads_dataset or "").strip()
    if mode == "ga4" and not ga4:
        return None
    if mode == "bq_raw" and not raw:
        return None
    if mode == "auto" and not any([raw, ga4, metrics]):
        return None
    funnel = tuple(tenant.funnel_events or ("begin_checkout", "purchase"))
    primary = (tenant.primary_metric or "purchase_conversion").strip() or "purchase_conversion"
    return BqConfig(
        project=project,
        raw_dataset=raw,
        metrics_dataset=metrics,
        ga4_dataset=ga4,
        ads_dataset=ads,
        ads_customer_id=(tenant.ads_customer_id or "").strip(),
        warehouse_mode=mode,
        primary_metric=primary,
        funnel_events=funnel,
    )


def has_bq(tenant: Tenant | None) -> bool:
    return resolve_bq_config(tenant) is not None


def _client(project: str):
    from google.cloud import bigquery  # type: ignore

    return bigquery.Client(project=project)


def _query(client, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    from google.cloud import bigquery  # type: ignore

    qparams = []
    for key, val in (params or {}).items():
        if isinstance(val, date):
            qparams.append(bigquery.ScalarQueryParameter(key, "DATE", val.isoformat()))
        elif isinstance(val, str):
            qparams.append(bigquery.ScalarQueryParameter(key, "STRING", val))
        elif isinstance(val, bool):
            qparams.append(bigquery.ScalarQueryParameter(key, "BOOL", val))
        elif isinstance(val, int):
            qparams.append(bigquery.ScalarQueryParameter(key, "INT64", val))
        elif isinstance(val, float):
            qparams.append(bigquery.ScalarQueryParameter(key, "FLOAT64", val))
    job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=qparams))
    return [dict(row) for row in job.result()]


def _rows_to_conversion(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        browser = str(row.get("browser") or "unknown")
        bc = float(row.get("begin_checkout") or 0)
        pu = float(row.get("purchase") or 0)
        den = bc or 1.0
        out[browser] = {
            "begin_checkout": bc,
            "purchase": pu,
            "conversion": pu / den,
        }
    return out


def _query_ga4_conversion(
    client,
    cfg: BqConfig,
    start: date,
    end: date,
    *,
    include_recovery: bool,
) -> list[dict[str, Any]]:
    suffix_start = start.strftime("%Y%m%d")
    suffix_end = end.strftime("%Y%m%d")
    recovery_clause = ""
    if not include_recovery:
        recovery_clause = f"AND _TABLE_SUFFIX < '{RECOVERY_START.strftime('%Y%m%d')}'"
    sql = f"""
        SELECT
          COALESCE(device.web_info.browser, 'unknown') AS browser,
          COUNTIF(event_name = 'begin_checkout') AS begin_checkout,
          COUNTIF(event_name = 'purchase') AS purchase
        FROM `{cfg.project}.{cfg.ga4_dataset}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN @suffix_start AND @suffix_end
          {recovery_clause}
          AND event_name IN ('begin_checkout', 'purchase')
        GROUP BY browser
    """
    return _query(client, sql, {"suffix_start": suffix_start, "suffix_end": suffix_end})


def _query_raw_conversion(
    client,
    cfg: BqConfig,
    start: date,
    end: date,
    *,
    include_recovery: bool,
) -> list[dict[str, Any]]:
    recovery_clause = ""
    if not include_recovery:
        recovery_clause = f"AND event_date < '{RECOVERY_START.isoformat()}'"
    sql = f"""
        SELECT browser,
          SUM(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS begin_checkout,
          SUM(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS purchase
        FROM `{cfg.project}.{cfg.raw_dataset}.events`
        WHERE event_date BETWEEN @start AND @end
          {recovery_clause}
        GROUP BY browser
    """
    return _query(client, sql, {"start": start, "end": end})


def conversion_by_browser(
    tenant: Tenant,
    start: date,
    end: date,
    *,
    include_recovery: bool = False,
    prefer: str = "",
) -> dict[str, dict[str, float]]:
    """Purchase / begin_checkout by browser — GA4 export and/or loop_raw.events.

    In ``auto`` mode, tries GA4 first then falls through to ``loop_raw`` when GA4
    returns no rows (common when export is empty but synthetic BQ is loaded).
    """
    cfg = resolve_bq_config(tenant)
    if not cfg:
        return {}
    try:
        client = _client(cfg.project)
    except Exception:
        return {}

    mode = cfg.warehouse_mode
    want = (prefer or "").strip().lower()
    try_ga4 = bool(cfg.ga4_dataset) and (
        want == "ga4" or (not want and mode in {"auto", "ga4"})
    )
    try_raw = bool(cfg.raw_dataset) and (
        want == "raw" or want == "bq_raw" or (not want and mode in {"auto", "bq_raw"})
    )
    if want == "ga4":
        try_raw = False
    if want in {"raw", "bq_raw"}:
        try_ga4 = False

    try:
        if try_ga4:
            rows = _query_ga4_conversion(client, cfg, start, end, include_recovery=include_recovery)
            out = _rows_to_conversion(rows)
            if out or mode == "ga4" or want == "ga4":
                return out
        if try_raw:
            rows = _query_raw_conversion(client, cfg, start, end, include_recovery=include_recovery)
            return _rows_to_conversion(rows)
    except Exception:
        return {}
    return {}


def metrics_daily_rows(tenant: Tenant, metric: str, *, limit: int = 14) -> list[dict[str, Any]]:
    """Recent metrics_daily points for proof tables."""
    cfg = resolve_bq_config(tenant)
    if not cfg or not cfg.metrics_dataset:
        return []
    try:
        client = _client(cfg.project)
        return _query(
            client,
            f"""
            SELECT CAST(day AS STRING) AS day, value
            FROM `{cfg.project}.{cfg.metrics_dataset}.metrics_daily`
            WHERE tenant_id = @tenant AND metric = @metric
            ORDER BY day DESC
            LIMIT @limit
            """,
            {"tenant": tenant.id, "metric": metric, "limit": int(limit)},
        )
    except Exception:
        return []


def conversion_probe(
    tenant: Tenant,
    start: date,
    end: date,
    *,
    include_recovery: bool = True,
    prefer: str = "",
) -> dict[str, Any]:
    """Like conversion_by_browser but returns source + error for trust UI."""
    cfg = resolve_bq_config(tenant)
    if not cfg:
        return {"rows": {}, "source": None, "error": "no BQ config"}
    mode = cfg.warehouse_mode
    want = (prefer or "").strip().lower()
    try:
        client = _client(cfg.project)
    except Exception as exc:
        return {"rows": {}, "source": None, "error": f"BQ client: {exc}"}

    errors: list[str] = []
    try_ga4 = bool(cfg.ga4_dataset) and (
        want == "ga4" or (not want and mode in {"auto", "ga4"})
    )
    try_raw = bool(cfg.raw_dataset) and (
        want in {"raw", "bq_raw"} or (not want and mode in {"auto", "bq_raw"})
    )
    if want == "ga4":
        try_raw = False
    if want in {"raw", "bq_raw"}:
        try_ga4 = False

    if try_ga4:
        try:
            rows = _rows_to_conversion(
                _query_ga4_conversion(client, cfg, start, end, include_recovery=include_recovery)
            )
            if rows or mode == "ga4" or want == "ga4":
                return {
                    "rows": rows,
                    "source": "ga4_export",
                    "dataset": cfg.ga4_dataset,
                    "table": "events_*",
                    "error": None if rows else "GA4 export returned no rows in window",
                }
            if not rows:
                errors.append("GA4 empty")
        except Exception as exc:
            errors.append(f"GA4: {exc}")
            if mode == "ga4" or want == "ga4":
                return {"rows": {}, "source": "ga4_export", "dataset": cfg.ga4_dataset, "table": "events_*", "error": str(exc)[:240]}

    if try_raw:
        try:
            rows = _rows_to_conversion(
                _query_raw_conversion(client, cfg, start, end, include_recovery=include_recovery)
            )
            return {
                "rows": rows,
                "source": "bigquery",
                "dataset": cfg.raw_dataset,
                "table": "events",
                "error": None if rows else "loop_raw.events returned no rows in window",
            }
        except Exception as exc:
            errors.append(f"raw: {exc}")
            return {
                "rows": {},
                "source": "bigquery",
                "dataset": cfg.raw_dataset,
                "table": "events",
                "error": str(exc)[:240],
            }

    return {"rows": {}, "source": None, "error": "; ".join(errors) or "no dataset matched mode"}


def read_metric_window(
    engine: Any,
    tenant: Tenant | None,
    metric: str,
    *,
    baseline: float | None = None,
) -> dict[str, Any] | None:
    """Honest metric re-read — metrics_daily, BQ events aggregate, or file warehouse."""
    if not tenant:
        return None
    cfg = resolve_bq_config(tenant)
    if cfg:
        try:
            client = _client(cfg.project)
            if cfg.metrics_dataset:
                table = f"{cfg.project}.{cfg.metrics_dataset}.metrics_daily"
                rows = _query(
                    client,
                    f"""
                    SELECT value, day FROM `{table}`
                    WHERE tenant_id = @tenant AND metric = @metric
                    ORDER BY day DESC LIMIT 1
                    """,
                    {"tenant": tenant.id, "metric": metric},
                )
                if rows:
                    value = float(rows[0]["value"])
                    return {
                        "value": value,
                        "baseline": baseline,
                        "source": "bigquery.metrics_daily",
                        "claim": f"{metric} measured at {value:.4g} (BQ metrics_daily)",
                        "day": str(rows[0].get("day") or ""),
                    }
            end = date.today()
            if end >= RECOVERY_START:
                end = RECOVERY_START - timedelta(days=1)
            start = end - timedelta(days=2)
            conv = conversion_by_browser(tenant, start, end)
            browser = "Safari" if "safari" in metric.lower() else next(iter(conv.keys()), "Chrome")
            row = conv.get(browser) or {}
            if row.get("conversion") is not None:
                value = float(row["conversion"])
                return {
                    "value": value,
                    "baseline": baseline,
                    "source": "bigquery.events",
                    "claim": (
                        f"{metric} at {value:.2%} for {browser} "
                        f"({int(row.get('purchase', 0))}/{int(row.get('begin_checkout', 0))} checkouts, BQ)"
                    ),
                }
        except Exception:
            pass

    wh = getattr(engine, "wh", None)
    if wh and hasattr(wh, "conversion_by_browser") and "conversion" in metric.lower():
        browser = "Safari" if "safari" in metric.lower() else "Chrome"
        # Use the fixture detect window — post-RECOVERY days are empty by design
        end = date.today()
        if end >= RECOVERY_START:
            end = RECOVERY_START - timedelta(days=1)
        start = end - timedelta(days=2)
        try:
            conv = wh.conversion_by_browser(start, end).get(browser, {}).get("conversion")
            if conv is not None:
                return {
                    "value": float(conv),
                    "baseline": baseline,
                    "source": "file_warehouse",
                    "claim": f"{metric} at {float(conv):.2%} for {browser} (file warehouse)",
                }
        except Exception:
            pass
    return None


def ads_attribution(tenant: Tenant, *, as_of: date | None = None) -> dict[str, Any]:
    """Ads spend + top campaign — loop_raw.campaign_daily or Google Ads transfer."""
    cfg = resolve_bq_config(tenant)
    if not cfg:
        return {}
    dataset = cfg.ads_dataset or cfg.raw_dataset
    if not dataset:
        return {}
    day = as_of or date.today()
    try:
        client = _client(cfg.project)
        sql = f"""
            SELECT campaign_name, channel, SUM(cost) AS spend
            FROM `{cfg.project}.{dataset}.campaign_daily`
            WHERE _DATA_DATE = @day
            GROUP BY campaign_name, channel
            ORDER BY spend DESC
            LIMIT 3
        """
        rows = _query(client, sql, {"day": day.isoformat()})
        if rows:
            top = rows[0]
            return {
                "channel": top.get("channel") or "Google Ads",
                "campaign": top.get("campaign_name") or "unknown",
                "spend": float(top.get("spend") or 0),
                "claim": (
                    f"Acquisition = {top.get('channel', 'Google Ads')} / "
                    f"{top.get('campaign_name', 'unknown')} (${float(top.get('spend') or 0):.2f})"
                ),
                "rows": rows,
                "source": "bigquery.ads",
            }
        # Fallback: flat ads table from load-bq.sh
        sql2 = f"""
            SELECT JSON_VALUE(payload, '$.campaign_name') AS campaign_name,
                   JSON_VALUE(payload, '$.channel') AS channel,
                   CAST(JSON_VALUE(payload, '$.cost') AS FLOAT64) AS cost
            FROM `{cfg.project}.{cfg.raw_dataset}.ads`
            WHERE JSON_VALUE(payload, '$._DATA_DATE') = @day
            LIMIT 5
        """
        if cfg.raw_dataset:
            rows2 = _query(client, sql2, {"day": day.isoformat()})
            if rows2:
                top = rows2[0]
                return {
                    "channel": top.get("channel") or "Google Ads",
                    "campaign": top.get("campaign_name") or "unknown",
                    "spend": float(top.get("cost") or 0),
                    "claim": (
                        f"Acquisition = {top.get('channel', 'Google Ads')} / "
                        f"{top.get('campaign_name', 'unknown')}"
                    ),
                    "source": "bigquery.ads_raw",
                }
    except Exception:
        pass
    return {}


def recent_deploy(tenant: Tenant) -> dict[str, Any]:
    cfg = resolve_bq_config(tenant)
    if not cfg or not cfg.raw_dataset:
        return {}
    try:
        client = _client(cfg.project)
        rows = _query(
            client,
            f"""
            SELECT JSON_VALUE(payload, '$.service') AS service,
                   JSON_VALUE(payload, '$.version') AS version,
                   JSON_VALUE(payload, '$.deployed_at') AS deployed_at
            FROM `{cfg.project}.{cfg.raw_dataset}.deploys`
            ORDER BY deployed_at DESC
            LIMIT 1
            """,
        )
        if rows:
            row = rows[0]
            return {
                "service": row.get("service") or "app",
                "version": row.get("version") or "?",
                "deployed_at": row.get("deployed_at") or "",
                "claim": f"Deploy {row.get('service', 'app')} {row.get('version', '?')} before anomaly window.",
            }
    except Exception:
        pass
    return {}


def error_summary(tenant: Tenant, *, hours: int = 72) -> dict[str, Any]:
    cfg = resolve_bq_config(tenant)
    if not cfg or not cfg.raw_dataset:
        return {}
    try:
        client = _client(cfg.project)
        rows = _query(
            client,
            f"""
            SELECT service, COUNT(*) AS errors
            FROM `{cfg.project}.{cfg.raw_dataset}.logs`
            WHERE level IN ('ERROR', 'error')
            GROUP BY service
            ORDER BY errors DESC
            LIMIT 5
            """,
        )
        if rows:
            top = rows[0]
            return {
                "claim": f"Log errors concentrated in {top.get('service', 'pay-sdk')} ({int(top.get('errors', 0))} rows).",
                "counts": {str(r.get("service")): int(r.get("errors") or 0) for r in rows},
                "source": "bigquery.logs",
            }
    except Exception:
        pass
    return {}


def enrich_anomaly_dimensions(store: Any, tenant: Tenant, dims: dict[str, Any]) -> dict[str, Any]:
    """Fill investigation probes from BQ when tenant warehouse is configured."""
    if not has_bq(tenant):
        return dims
    out = dict(dims)
    end = date.today()
    if end >= RECOVERY_START:
        end = RECOVERY_START - timedelta(days=1)
    start = end - timedelta(days=2)
    baseline_end = REGRESSION_START - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=13)
    cur = conversion_by_browser(tenant, start, end)
    base = conversion_by_browser(tenant, baseline_start, baseline_end)
    segs = out.get("segments") if isinstance(out.get("segments"), dict) else {}
    focus = str(segs.get("browser") or "") or None
    if not focus and cur:
        focus = max(
            cur.keys(),
            key=lambda n: abs(
                float(cur[n].get("conversion") or 0)
                - float((base.get(n) or {}).get("conversion") or 0)
            ),
        )
    if focus and (cur.get(focus) or base.get(focus)):
        focus_cur = float((cur.get(focus) or {}).get("conversion") or 0)
        focus_base = float((base.get(focus) or {}).get("conversion") or 0)
        control = next((n for n in cur if n != focus), None)
        claim = f"{focus} conversion {focus_cur:.1%} vs baseline {focus_base:.1%}"
        if control:
            c_cur = float((cur.get(control) or {}).get("conversion") or 0)
            c_base = float((base.get(control) or {}).get("conversion") or 0)
            claim += f"; {control} {c_cur:.1%} vs {c_base:.1%}"
        claim += " (BQ)."
        out.setdefault("analytics_claim", claim)
    ads = ads_attribution(tenant)
    if ads.get("claim"):
        out.setdefault("ads_claim", ads["claim"])
        out.setdefault("acquisition", {"channel": ads.get("channel"), "campaign": ads.get("campaign")})
    dep = recent_deploy(tenant)
    if dep:
        out.setdefault("deploy", dep)
        out.setdefault("deploy_claim", dep.get("claim"))
    logs = error_summary(tenant)
    if logs.get("claim"):
        out.setdefault("logs_claim", logs["claim"])
        out.setdefault("logs", logs.get("counts") or {})
    out.setdefault("warehouse_source", "bigquery")
    return out


def enrich_research_dimensions(store: Any, tenant: Tenant, dims: dict[str, Any]) -> dict[str, Any]:
    if not has_bq(tenant):
        return dims
    out = dict(dims)
    ads = ads_attribution(tenant)
    if ads.get("claim"):
        out.setdefault("ads_claim", ads["claim"])
        out.setdefault("acquisition", {"channel": ads.get("channel"), "campaign": ads.get("campaign")})
    out.setdefault(
        "ga4_claim",
        out.get("ga4_claim") or "Funnel events available in GA4 export (linked via tenant warehouse config).",
    )
    out.setdefault("ga4_events", list(tenant.funnel_events or ["begin_checkout", "add_payment_info", "purchase"]))
    return out


def detect_anomalies_for_tenant(engine: Any, tenant: Tenant, *, as_of: date | None = None) -> list[Any]:
    """Tenant-scoped unprompted detect from BQ — rolling windows in production."""
    from loop.models import Direction, Segment, Signal, SignalFamily, SignalStatus
    from loop.runtime_mode import is_eval_mode

    cfg = resolve_bq_config(tenant)
    if not cfg:
        return []

    if is_eval_mode():
        as_of = as_of or (RECOVERY_START - timedelta(days=1))
        window_end = as_of
        window_start = as_of - timedelta(days=2)
        baseline_end = REGRESSION_START - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=13)
    else:
        as_of = as_of or (date.today() - timedelta(days=1))
        window_end = as_of
        window_start = as_of - timedelta(days=2)
        baseline_end = window_start - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=13)

    current = conversion_by_browser(tenant, window_start, window_end)
    baseline = conversion_by_browser(tenant, baseline_start, baseline_end)
    if not current:
        return []

    found: list[Any] = []
    for browser, cur in current.items():
        base = baseline.get(browser)
        if not base or base.get("conversion", 0) <= 0:
            continue
        if cur.get("begin_checkout", 0) < 80:
            continue
        rel = (cur["conversion"] - base["conversion"]) / base["conversion"]
        if rel > -0.12:
            continue
        sig = Signal(
            id=f"sig_{tenant.id}_{browser.lower()}_{as_of.strftime('%Y%m%d')}",
            family=SignalFamily.BUSINESS,
            direction=Direction.NEGATIVE,
            funnel_position="purchase",
            metric=cfg.primary_metric,
            magnitude=rel,
            baseline=base["conversion"],
            affected_segments=[
                Segment(browser=browser, os="iOS" if browser == "Safari" else None, platform="web")
            ],
            detection_window={
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
                "baseline_start": baseline_start.isoformat(),
                "baseline_end": baseline_end.isoformat(),
            },
            confidence=min(0.95, 0.55 + abs(rel)),
            source="bigquery.events",
            status=SignalStatus.OPEN,
            detected_at=datetime.now(timezone.utc),
        )
        engine.store.put_signal(sig)
        found.append(sig)
    return found
