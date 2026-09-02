"""Warehouse / Pub/Sub. File path stays the default; BQ/Pub/Sub only when entitled."""

from __future__ import annotations

import json
import os
from typing import Any

from loop.tenant import ConnectorReport, Tenant


def _log_needle_candidates(metric: str) -> list[str]:
    m = (metric or "").lower()
    if "checkout" in m or "payment" in m or "conversion" in m:
        return ["TIMEOUT", "CLIENT_ERROR", "ERROR"]
    if "activat" in m or "onboard" in m:
        return ["ACTIVATION", "ERROR"]
    if "ship" in m or "deliver" in m:
        return ["SHIPPING", "ERROR"]
    if "auth" in m or "login" in m:
        return ["AUTH", "ERROR"]
    toks = [t for t in m.replace("-", "_").split("_") if t]
    primary = toks[0].upper() if toks else "ERROR"
    return [primary, "ERROR"]


def _log_needle_from_metric(metric: str) -> str:
    return _log_needle_candidates(metric)[0]


def publish_signal(payload: dict, *, store: Any | None = None) -> ConnectorReport:
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    topic = (os.environ.get("LOOP_PUBSUB_TOPIC") or "loop.signals").strip()
    if not project:
        return ConnectorReport(
            status="skipped",
            connector="warehouse.pubsub",
            detail="no GOOGLE_CLOUD_PROJECT",
        )
    try:
        from google.cloud import pubsub_v1  # type: ignore
    except ImportError:
        return ConnectorReport(
            status="skipped",
            connector="warehouse.pubsub",
            detail="pubsub client not installed — file warehouse still used",
        )
    try:
        publisher = pubsub_v1.PublisherClient()
        path = publisher.topic_path(project, topic)
        data = json.dumps(payload, default=str).encode("utf-8")
        future = publisher.publish(path, data, source="loop.ingest")
        msg_id = future.result(timeout=10)
        return ConnectorReport(
            status="applied",
            connector="warehouse.pubsub",
            detail=f"published {msg_id}",
        )
    except Exception as exc:
        report = ConnectorReport(
            status="skipped",
            connector="warehouse.pubsub",
            detail=str(exc)[:200],
        )
        if store is not None:
            try:
                from loop.audit import record

                record(
                    store,
                    actor="warehouse",
                    action="pubsub.publish_failed",
                    resource=str(payload.get("signal_id") or payload.get("tenant_id") or "signal"),
                    detail={"error": str(exc)[:200]},
                )
            except Exception:
                pass
        return report


def read_metric_window(
    engine: Any,
    tenant: Tenant | None,
    metric: str,
    *,
    baseline: float | None = None,
) -> dict[str, Any] | None:
    """Honest metric re-read for verify / probes. BQ when configured; else file warehouse; else None."""
    from loop.connectors.bigquery import read_metric_window as bq_read

    return bq_read(engine, tenant, metric, baseline=baseline)


def enrich_file_dimensions(engine: Any, dims: dict[str, Any], *, metric: str = "") -> dict[str, Any]:
    """Fill investigation arms from the local/file warehouse — same facts gather_evidence uses."""
    from datetime import date, datetime, timedelta, timezone

    from loop.warehouse import RECOVERY_START, REGRESSION_START

    out = dict(dims)
    if out.get("skip_fixture_enrichment") or out.get("tenant_id"):
        return out
    # BQ may be configured but return no rows — still fill missing arms from file warehouse.
    if out.get("warehouse_source") == "bigquery" and out.get("logs_claim") and out.get("deploy_claim"):
        return out
    wh = getattr(engine, "wh", None)
    if wh is None:
        return out
    end = date.today()
    if end >= RECOVERY_START:
        end = RECOVERY_START - timedelta(days=1)
    start = end - timedelta(days=2)
    baseline_end = REGRESSION_START - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=13)
    try:
        cur = wh.conversion_by_browser(start, end)
        base = wh.conversion_by_browser(baseline_start, baseline_end)
    except Exception:
        return out
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
        claim += " (file warehouse)."
        out.setdefault("analytics_claim", claim)
        out.setdefault("segments", {**(segs or {}), "browser": focus})
    # Logs — pick the first needle with rows; claim stays generic (no fixture 3DS copy).
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
    base_start_dt = datetime.combine(baseline_start, datetime.min.time(), tzinfo=timezone.utc)
    base_end_dt = datetime.combine(baseline_end, datetime.max.time(), tzinfo=timezone.utc)
    needle = ""
    now_counts: dict[str, int] = {}
    then_counts: dict[str, int] = {}
    try:
        for candidate in _log_needle_candidates(metric):
            now_counts = wh.error_counts(start_dt, end_dt, candidate)
            then_counts = wh.error_counts(base_start_dt, base_end_dt, candidate)
            if sum(now_counts.values()) or sum(then_counts.values()):
                needle = candidate
                break
        if not needle:
            needle = _log_needle_from_metric(metric)
            now_counts = wh.error_counts(start_dt, end_dt, needle)
            then_counts = wh.error_counts(base_start_dt, base_end_dt, needle)
        now_n = sum(now_counts.values())
        then_n = sum(then_counts.values())
        if now_n or then_n:
            label = "timeout" if needle == "TIMEOUT" else needle.lower().replace("_", " ")
            out.setdefault(
                "logs_claim",
                f"{label.title()} errors rose from {then_n} (baseline) to {now_n} (detection) in file warehouse.",
            )
            out.setdefault(
                "logs",
                {"signature": needle, "now": now_n, "then": then_n, "counts": now_counts},
            )
    except Exception:
        pass
    try:
        all_deploys = list(wh.deploys())
        window_deploys = [
            d for d in all_deploys if str(start) <= str(d.get("at") or "")[:10] <= str(end)
        ]
        desc = window_deploys[0] if window_deploys else (all_deploys[0] if all_deploys else None)
        if desc:
            out.setdefault(
                "deploy",
                {
                    "service": desc.get("service") or desc.get("id") or "app",
                    "version": desc.get("version") or desc.get("sha") or "unknown",
                    "at": desc.get("at"),
                },
            )
            out.setdefault(
                "deploy_claim",
                f"Deploy {out['deploy']['service']} {out['deploy']['version']} near detection window (file warehouse).",
            )
    except Exception:
        pass
    out.setdefault("warehouse_source", "file")
    return out
