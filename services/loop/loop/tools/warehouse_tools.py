from __future__ import annotations

from datetime import date
from typing import Any

from ..engine import LoopEngine
from ..warehouse import RECOVERY_START


def make_analysis_tools(engine: LoopEngine) -> list:
    def detect_signals(as_of: str | None = None) -> dict[str, Any]:
        """Scan daily warehouse tables for baseline-relative segment anomalies."""
        day = date.fromisoformat(as_of) if as_of else None
        signals = engine.detect_signals(day)
        return {"signals": [s.model_dump(mode="json") for s in signals]}

    def query_conversion(start: str, end: str, table_kind: str = "daily") -> dict[str, Any]:
        """Query purchase conversion. Evidence must use daily tables, not intraday (B-3)."""
        if table_kind != "daily":
            return {"error": "EVIDENCE_REQUIRES_DAILY_TABLES", "provisional": True}
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        include = start_d >= RECOVERY_START
        return engine.wh.conversion_by_browser(start_d, end_d, include_recovery=include)

    def query_logs(start: str, end: str, signature: str = "3DS") -> dict[str, Any]:
        from datetime import datetime, timezone

        start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        return engine.wh.error_counts(start_dt, end_dt, signature)

    def query_deploys() -> dict[str, Any]:
        return {"deploys": engine.wh.deploys()}

    def ads_spend() -> dict[str, Any]:
        """Ads spend by date. Joins constrain _DATA_DATE on both sides (J-9)."""
        return engine.wh.ads_spend_by_date()

    detect_signals.__name__ = "detect_signals"
    query_conversion.__name__ = "query_conversion"
    query_logs.__name__ = "query_logs"
    query_deploys.__name__ = "query_deploys"
    ads_spend.__name__ = "ads_spend"
    return [detect_signals, query_conversion, query_logs, query_deploys, ads_spend]
