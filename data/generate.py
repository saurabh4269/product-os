#!/usr/bin/env python3
"""Generate a seeded Northstar Pay warehouse: GA4-shaped events, logs, deploys, Ads.

Safari/iOS purchase conversion drops ~25% from 2026-08-20 after pay-sdk 4.3.0.
Recovery days (2026-08-29+) exist for post-approval verification only.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "var" / "warehouse"

START = date(2026, 8, 1)
REGRESSION = date(2026, 8, 20)
RECOVERY = date(2026, 8, 29)
END = date(2026, 9, 4)

BROWSERS = [
    ("Chrome", 0.48, 0.082),
    ("Safari", 0.27, 0.079),
    ("Firefox", 0.10, 0.077),
    ("Edge", 0.15, 0.080),
]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def day_seed(day: date, extra: int = 0) -> int:
    return 20260829 + day.toordinal() + extra


def conversion_rate(browser: str, day: date) -> float:
    base = {b: cr for b, _, cr in BROWSERS}[browser]
    dow = day.weekday()
    seasonal = 1.0 - 0.04 * (1 if dow >= 5 else 0)
    if day >= RECOVERY:
        return base * seasonal
    if day >= REGRESSION and browser == "Safari":
        return base * seasonal * 0.74
    return base * seasonal


def emit_day(day: date) -> list[dict]:
    rng = _rng(day_seed(day))
    sessions = 420 + (day.weekday() * 15)
    events: list[dict] = []
    ts_base = datetime(day.year, day.month, day.day, 8, 0, tzinfo=timezone.utc)
    for i in range(sessions):
        pick = rng.random()
        acc = 0.0
        browser = "Chrome"
        for name, s, _ in BROWSERS:
            acc += s
            if pick <= acc:
                browser = name
                break
        os = "iOS" if browser == "Safari" and rng.random() < 0.72 else "macOS" if browser == "Safari" else "Android" if rng.random() < 0.35 else "Windows"
        geo = rng.choice(["US", "US", "US", "GB", "CA"])
        channel = rng.choice(["cpc", "cpc", "organic", "direct"])
        user = f"tok_{rng.randrange(10**8):08d}"
        cr = conversion_rate(browser, day)
        # Funnel
        events.append(_ev(ts_base, i, 0, "page_view", user, browser, os, geo, channel, day))
        if rng.random() < 0.62:
            events.append(_ev(ts_base, i, 1, "view_item", user, browser, os, geo, channel, day))
        if rng.random() < 0.38:
            events.append(_ev(ts_base, i, 2, "begin_checkout", user, browser, os, geo, channel, day))
            if rng.random() < 0.91:
                events.append(_ev(ts_base, i, 3, "add_payment_info", user, browser, os, geo, channel, day))
            if rng.random() < cr / 0.38:
                events.append(_ev(ts_base, i, 4, "purchase", user, browser, os, geo, channel, day, value=42.0 + rng.random() * 80))
    return events


def _ev(ts_base, session, step, name, user, browser, os, geo, channel, day, value=None):
    ts = ts_base + timedelta(minutes=session * 2 + step)
    ev = {
        "event_date": day.strftime("%Y%m%d"),
        "event_timestamp": int(ts.timestamp() * 1_000_000),
        "event_name": name,
        "user_pseudo_id": user,
        "device": {
            "category": "mobile" if os in {"iOS", "Android"} else "desktop",
            "operating_system": os,
            "web_info": {"browser": browser},
        },
        "geo": {"country": geo},
        "traffic_source": {"source": channel, "medium": channel},
        "app_info": {"version": "4.3.0" if day >= REGRESSION else "4.2.1"},
    }
    if value is not None:
        ev["event_value"] = round(value, 2)
    return ev


def emit_logs() -> list[dict]:
    rows = []
    day = START
    while day <= END:
        base_safari = 4
        if REGRESSION <= day < RECOVERY:
            base_safari = 38
        elif day >= RECOVERY:
            base_safari = 5
        for browser, count in (("Safari", base_safari), ("Chrome", 3), ("Firefox", 1), ("Edge", 2)):
            for j in range(count):
                ts = datetime(day.year, day.month, day.day, 10, j, tzinfo=timezone.utc)
                rows.append(
                    {
                        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "severity": "ERROR",
                        "signature": "3DS_TIMEOUT" if browser == "Safari" and day >= REGRESSION and day < RECOVERY else "card_auth",
                        "message": (
                            "PaymentSDK 3DS_TIMEOUT waiting for challenge frame (WebKit)"
                            if browser == "Safari" and REGRESSION <= day < RECOVERY
                            else "card_auth declined (insufficient funds)"
                        ),
                        "browser": browser,
                        "app_version": "4.3.0" if day >= REGRESSION else "4.2.1",
                    }
                )
        day += timedelta(days=1)
    return rows


def emit_deploys() -> list[dict]:
    return [
        {
            "id": "dep_421",
            "sha": "a1b2c3d4e5f6",
            "version": "pay-sdk@4.2.1",
            "at": "2026-08-08T14:02:00Z",
            "note": "patch bump, green tests",
        },
        {
            "id": "dep_430",
            "sha": "9f8e7d6c5b4a",
            "version": "pay-sdk@4.3.0",
            "at": "2026-08-20T09:14:00Z",
            "note": "Payment SDK 4.3 — new 3DS challenge iframe",
        },
    ]


def emit_ads() -> list[dict]:
    rows = []
    day = START
    while day <= END:
        ds = day.isoformat()
        for cid, name, base, imps, clicks, conv in (
            ("c_northstar", "US-Search-Brand", 820.0, 14000, 620, 48),
            ("c_shop", "US-Shopping-Home", 310.0, 6200, 210, 19),
        ):
            cost = base + (day.weekday() * 8)
            rows.append(
                {
                    "_table": "ads_Campaign",
                    "_DATA_DATE": ds,
                    "campaign_id": cid,
                    "campaign_name": name,
                }
            )
            rows.append(
                {
                    "_table": "ads_CampaignStats",
                    "_DATA_DATE": ds,
                    "campaign_id": cid,
                    "impressions": imps,
                    "clicks": clicks,
                    "cost": cost,
                    "conversions": conv,
                }
            )
        day += timedelta(days=1)
    return rows


def main(out: Path = OUT) -> Path:
    events_dir = out / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    day = START
    totals = {"days": 0, "events": 0}
    while day <= END:
        evs = emit_day(day)
        path = events_dir / f"events_{day.strftime('%Y%m%d')}.jsonl"
        path.write_text("".join(json.dumps(e) + "\n" for e in evs))
        totals["days"] += 1
        totals["events"] += len(evs)
        day += timedelta(days=1)
    (out / "logs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in emit_logs()))
    (out / "deploys.json").write_text(json.dumps(emit_deploys(), indent=2))
    (out / "ads.json").write_text(json.dumps(emit_ads(), indent=2))
    (out / "meta.json").write_text(
        json.dumps(
            {
                "tenant": "Northstar",
                "seed": 20260829,
                "regression_start": REGRESSION.isoformat(),
                "recovery_start": RECOVERY.isoformat(),
                "defect": "Safari WebKit 3DS timeout after pay-sdk 4.3.0",
                **totals,
            },
            indent=2,
        )
    )
    print(f"wrote {totals} to {out}")
    return out


if __name__ == "__main__":
    main()
