#!/usr/bin/env bash
# Load the synthetic warehouse into cheap BigQuery datasets. Never prints credentials.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
export LOOP_ROOT="$ROOT"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
export GOOGLE_CLOUD_REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

if [[ ! -f "$ROOT/var/warehouse/meta.json" ]]; then
  python3 "$ROOT/data/generate.py"
fi

# shellcheck disable=SC1091
if [[ -f "$ROOT/services/loop/.venv/bin/activate" ]]; then
  source "$ROOT/services/loop/.venv/bin/activate"
fi

python3 - <<'PY'
import json, os, sys
from pathlib import Path

project = os.environ["GOOGLE_CLOUD_PROJECT"]
root = Path(os.environ["LOOP_ROOT"]) / "var" / "warehouse"

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("install extras: pip install -e services/loop[gcp]")

def _credentials():
    try:
        import google.auth
        creds, _ = google.auth.default()
        return creds
    except Exception:
        pass
    legacy = sorted(Path.home().glob(".config/gcloud/legacy_credentials/*/adc.json"))
    if legacy:
        from google.oauth2.credentials import Credentials
        raw = json.loads(legacy[-1].read_text())
        return Credentials.from_authorized_user_info(raw)
    sys.exit("no ADC — run: gcloud auth login && gcloud auth application-default login")

client = bigquery.Client(
    project=project,
    location=os.environ.get("GOOGLE_CLOUD_REGION", "us-central1"),
    credentials=_credentials(),
)

def load_jsonl(table_id: str, rows: list[dict], schema: list):
    job = client.load_table_from_json(
        rows,
        table_id,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    job.result()
    print(f"bq: loaded {len(rows)} rows into {table_id}", flush=True)

events = []
for p in sorted((root / "events").glob("events_*.jsonl")):
    day = p.stem.replace("events_", "")
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        events.append({
            "event_date": f"{day[0:4]}-{day[4:6]}-{day[6:8]}",
            "event_name": ev.get("event_name"),
            "browser": (ev.get("device") or {}).get("web_info", {}).get("browser"),
            "geo": (ev.get("geo") or {}).get("country", "US"),
        })
load_jsonl(
    f"{project}.loop_raw.events",
    events,
    [
        bigquery.SchemaField("event_date", "DATE"),
        bigquery.SchemaField("event_name", "STRING"),
        bigquery.SchemaField("browser", "STRING"),
        bigquery.SchemaField("geo", "STRING"),
    ],
)

logs = []
lp = root / "logs.jsonl"
if lp.exists():
    for line in lp.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        logs.append({
            "ts": row.get("timestamp") or row.get("ts"),
            "level": row.get("severity") or row.get("level", "ERROR"),
            "message": str(row.get("message") or "")[:2000],
            "service": row.get("signature") or row.get("service", "pay-sdk"),
        })
load_jsonl(
    f"{project}.loop_raw.logs",
    logs,
    [
        bigquery.SchemaField("ts", "STRING"),
        bigquery.SchemaField("level", "STRING"),
        bigquery.SchemaField("message", "STRING"),
        bigquery.SchemaField("service", "STRING"),
    ],
)

deploys = json.loads((root / "deploys.json").read_text()) if (root / "deploys.json").exists() else []
if isinstance(deploys, dict):
    deploys = deploys.get("deploys", [deploys])
load_jsonl(
    f"{project}.loop_raw.deploys",
    [{"payload": json.dumps(d)} for d in deploys],
    [bigquery.SchemaField("payload", "STRING")],
)

ads = json.loads((root / "ads.json").read_text()) if (root / "ads.json").exists() else []
load_jsonl(
    f"{project}.loop_raw.ads",
    [{"payload": json.dumps(d)} for d in ads],
    [bigquery.SchemaField("payload", "STRING")],
)

# metrics_daily — tenant-scoped rollup for verify + probes
metrics = []
for day_s in sorted({e["event_date"] for e in events}):
    day_events = [e for e in events if e["event_date"] == day_s]
    bc = sum(1 for e in day_events if e["event_name"] == "begin_checkout")
    pu = sum(1 for e in day_events if e["event_name"] == "purchase")
    conv = (pu / bc) if bc else 0.0
    for tid in ("acme", "default"):
        metrics.append(
            {
                "tenant_id": tid,
                "metric": "purchase_conversion",
                "day": day_s,
                "value": conv,
            }
        )
load_jsonl(
    f"{project}.loop_metrics.metrics_daily",
    metrics,
    [
        bigquery.SchemaField("tenant_id", "STRING"),
        bigquery.SchemaField("metric", "STRING"),
        bigquery.SchemaField("day", "DATE"),
        bigquery.SchemaField("value", "FLOAT64"),
    ],
)

# Optional Ads daily rollup for attribution probes
campaign_daily = []
for row in ads:
    if row.get("_table") != "ads_CampaignStats":
        continue
    match = next(
        (
            d
            for d in ads
            if d.get("_table") == "ads_Campaign"
            and d.get("campaign_id") == row.get("campaign_id")
            and d.get("_DATA_DATE") == row.get("_DATA_DATE")
        ),
        None,
    )
    if not match:
        continue
    campaign_daily.append(
        {
            "_DATA_DATE": row["_DATA_DATE"],
            "campaign_name": match.get("campaign_name", "Campaign X"),
            "channel": "Google Ads",
            "cost": float(row.get("cost") or 0),
        }
    )
if campaign_daily:
    load_jsonl(
        f"{project}.loop_raw.campaign_daily",
        campaign_daily,
        [
            bigquery.SchemaField("_DATA_DATE", "DATE"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("channel", "STRING"),
            bigquery.SchemaField("cost", "FLOAT64"),
        ],
    )

print("bq: warehouse load complete", flush=True)
PY
