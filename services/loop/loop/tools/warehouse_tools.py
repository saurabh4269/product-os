from __future__ import annotations

from datetime import date
from typing import Any

from ..engine import LoopEngine
from ..warehouse import RECOVERY_START


def make_analysis_tools(engine: LoopEngine) -> list:
    def detect_signals(as_of: str | None = None, tenant_id: str = "") -> dict[str, Any]:
        """Scan daily warehouse tables for baseline-relative segment anomalies."""
        day = date.fromisoformat(as_of) if as_of else None
        if tenant_id:
            tenant = engine.store.get_tenant(tenant_id)
            if tenant:
                from loop.connectors.bigquery import detect_anomalies_for_tenant, has_bq

                if has_bq(tenant):
                    found = detect_anomalies_for_tenant(engine, tenant, as_of=day)
                    return {"signals": [s.model_dump(mode="json") for s in found]}
        signals = engine.detect_all_signals(day)
        return {"signals": [s.model_dump(mode="json") for s in signals]}

    def query_conversion(start: str, end: str, table_kind: str = "daily", tenant_id: str = "") -> dict[str, Any]:
        """Query purchase conversion. Evidence must use daily tables, not intraday (B-3)."""
        if table_kind != "daily":
            return {"error": "EVIDENCE_REQUIRES_DAILY_TABLES", "provisional": True}
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        include = start_d >= RECOVERY_START
        tenant = engine.store.get_tenant(tenant_id) if tenant_id else None
        if tenant:
            from loop.connectors.bigquery import conversion_by_browser, has_bq

            if has_bq(tenant):
                return conversion_by_browser(tenant, start_d, end_d, include_recovery=include)
        return engine.wh.conversion_by_browser(start_d, end_d, include_recovery=include)

    def query_logs(start: str, end: str, signature: str = "3DS", tenant_id: str = "") -> dict[str, Any]:
        from datetime import datetime, timezone

        tenant = engine.store.get_tenant(tenant_id) if tenant_id else None
        if tenant:
            from loop.connectors.bigquery import error_summary, has_bq

            if has_bq(tenant):
                return error_summary(tenant)
        start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        return engine.wh.error_counts(start_dt, end_dt, signature)

    def query_deploys(tenant_id: str = "") -> dict[str, Any]:
        tenant = engine.store.get_tenant(tenant_id) if tenant_id else None
        if tenant:
            from loop.connectors.bigquery import has_bq, recent_deploy

            if has_bq(tenant):
                dep = recent_deploy(tenant)
                if dep:
                    return {"deploys": [dep]}
        return {"deploys": engine.wh.deploys()}

    def ads_spend(tenant_id: str = "") -> dict[str, Any]:
        """Ads spend by date. Joins constrain _DATA_DATE on both sides (J-9)."""
        tenant = engine.store.get_tenant(tenant_id) if tenant_id else None
        if tenant:
            from loop.connectors.bigquery import ads_attribution, has_bq

            if has_bq(tenant):
                row = ads_attribution(tenant)
                if row:
                    return {"attribution": row}
        return engine.wh.ads_spend_by_date()

    detect_signals.__name__ = "detect_signals"
    query_conversion.__name__ = "query_conversion"
    query_logs.__name__ = "query_logs"
    query_deploys.__name__ = "query_deploys"
    ads_spend.__name__ = "ads_spend"
    return [detect_signals, query_conversion, query_logs, query_deploys, ads_spend]
