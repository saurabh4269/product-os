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
