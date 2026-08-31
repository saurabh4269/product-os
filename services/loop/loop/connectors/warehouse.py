"""Warehouse / Pub/Sub. File path stays the default; BQ/Pub/Sub only when entitled."""

from __future__ import annotations

import json
import os
from typing import Any

from loop.tenant import ConnectorReport, Tenant


def publish_signal(payload: dict) -> ConnectorReport:
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
        return ConnectorReport(
            status="skipped",
            connector="warehouse.pubsub",
            detail=str(exc)[:200],
        )


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
    if out.get("warehouse_source") == "bigquery":
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
    # Logs — needle from metric
    needle = "3DS" if any(x in (metric or "").lower() for x in ("purchase", "checkout", "payment", "conversion")) else "ERROR"
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
    base_start_dt = datetime.combine(baseline_start, datetime.min.time(), tzinfo=timezone.utc)
    base_end_dt = datetime.combine(baseline_end, datetime.max.time(), tzinfo=timezone.utc)
    try:
        now_counts = wh.error_counts(start_dt, end_dt, needle)
        then_counts = wh.error_counts(base_start_dt, base_end_dt, needle)
        now_n = sum(now_counts.values())
        then_n = sum(then_counts.values())
        if now_n or then_n:
            out.setdefault(
                "logs_claim",
                f"{needle} errors rose from {then_n} (baseline) to {now_n} (detection) in file warehouse.",
            )
            out.setdefault("logs", {"signature": needle, "now": now_n, "then": then_n, "counts": now_counts})
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
