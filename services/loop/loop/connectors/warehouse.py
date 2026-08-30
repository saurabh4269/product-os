"""Warehouse / Pub/Sub. File path stays the default; BQ/Pub/Sub only when entitled."""

from __future__ import annotations

import os

from loop.tenant import ConnectorReport


def publish_signal(payload: dict) -> ConnectorReport:
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
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
    _ = pubsub_v1, payload
    return ConnectorReport(
        status="skipped",
        connector="warehouse.pubsub",
        detail="best-effort publish not wired; file warehouse remains source of truth",
    )
