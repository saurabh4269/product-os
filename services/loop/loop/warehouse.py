"""Read-only warehouse over synthetic daily tables. Evidence uses daily tables only (J-1, B-3)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REGRESSION_START = date(2026, 8, 20)
RECOVERY_START = date(2026, 8, 29)
SEED_END = date(2026, 9, 4)


class Warehouse:
    def __init__(self, root: Path):
        self.root = root
        self.events_dir = root / "events"
        self.logs_path = root / "logs.jsonl"
        self.deploys_path = root / "deploys.json"
        self.ads_path = root / "ads.json"
        self.meta_path = root / "meta.json"

    def meta(self) -> dict[str, Any]:
        return json.loads(self.meta_path.read_text()) if self.meta_path.exists() else {}

    def list_event_dates(self) -> list[date]:
        dates = []
        if not self.events_dir.exists():
            return dates
        for p in sorted(self.events_dir.glob("events_*.jsonl")):
            dates.append(datetime.strptime(p.stem.replace("events_", ""), "%Y%m%d").date())
        return dates

    def iter_events(self, day: date):
        path = self.events_dir / f"events_{day.strftime('%Y%m%d')}.jsonl"
        if not path.exists():
            return
        with path.open() as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    def conversion_by_browser(
        self, start: date, end: date, *, include_recovery: bool = False
    ) -> dict[str, dict[str, float]]:
        """Purchase / begin_checkout by browser on stable daily tables."""
        tallies: dict[str, dict[str, float]] = defaultdict(lambda: {"begin_checkout": 0, "purchase": 0})
        day = start
        while day <= end:
            if day >= RECOVERY_START and not include_recovery:
                day += timedelta(days=1)
                continue
            for ev in self.iter_events(day) or []:
                browser = ev.get("device", {}).get("web_info", {}).get("browser", "unknown")
                name = ev.get("event_name")
                if name in ("begin_checkout", "purchase"):
                    tallies[browser][name] += 1
            day += timedelta(days=1)
        out = {}
        for browser, c in tallies.items():
            den = c["begin_checkout"] or 1
            out[browser] = {
                "begin_checkout": c["begin_checkout"],
                "purchase": c["purchase"],
                "conversion": c["purchase"] / den,
            }
        return out

    def conversion_by_browser_geo(
        self, start: date, end: date
    ) -> dict[tuple[str, str], dict[str, float]]:
        tallies: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: {"begin_checkout": 0, "purchase": 0}
        )
        day = start
        while day <= end:
            if day >= RECOVERY_START:
                day += timedelta(days=1)
                continue
            for ev in self.iter_events(day) or []:
                browser = ev.get("device", {}).get("web_info", {}).get("browser", "unknown")
                geo = ev.get("geo", {}).get("country", "US")
                name = ev.get("event_name")
                if name in ("begin_checkout", "purchase"):
                    tallies[(browser, geo)][name] += 1
            day += timedelta(days=1)
        out = {}
        for key, c in tallies.items():
            den = c["begin_checkout"] or 1
            out[key] = {**c, "conversion": c["purchase"] / den}
        return out

    def load_logs(self) -> list[dict]:
        if not self.logs_path.exists():
            return []
        return [json.loads(line) for line in self.logs_path.read_text().splitlines() if line.strip()]

    def error_counts(self, start: datetime, end: datetime, signature: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for row in self.load_logs():
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if start <= ts <= end:
                if signature and signature not in row.get("message", ""):
                    continue
                key = f"{row.get('browser','?')}|{row.get('signature','error')}"
                counts[key] += 1
        return dict(counts)

    def deploys(self) -> list[dict]:
        if not self.deploys_path.exists():
            return []
        return json.loads(self.deploys_path.read_text())

    def ads_rows(self) -> list[dict]:
        if not self.ads_path.exists():
            return []
        return json.loads(self.ads_path.read_text())

    def ads_spend_by_date(self) -> dict[str, float]:
        """Join stats to campaign on _DATA_DATE on both sides (J-9)."""
        raw = self.ads_rows()
        stats = [r for r in raw if r.get("_table") == "ads_CampaignStats"]
        dims = [r for r in raw if r.get("_table") == "ads_Campaign"]
        spend: dict[str, float] = defaultdict(float)
        for s in stats:
            match = next(
                (
                    d
                    for d in dims
                    if d["campaign_id"] == s["campaign_id"] and d["_DATA_DATE"] == s["_DATA_DATE"]
                ),
                None,
            )
            if not match:
                continue
            spend[s["_DATA_DATE"]] += float(s["cost"])
        return dict(spend)


def utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
