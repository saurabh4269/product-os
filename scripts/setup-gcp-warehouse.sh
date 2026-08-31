#!/usr/bin/env bash
# One-shot GCP setup: BQ warehouse, Loop env, tenant warehouse config, scheduler, GA4 (when ADC has analytics scope).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
LOOP_URL="${LOOP_PUBLIC_URL:-https://loop-5uy6fkd7bq-uc.a.run.app}"
COVE_URL="${COVE_DEPLOY_URL:-https://cove-5uy6fkd7bq-uc.a.run.app}"
TENANT_ID="${LOOP_TENANT_ID:-acme}"
TENANT_REPO="${LOOP_TENANT_REPO:-saurabh4269/cove}"
SCHEDULER_JOB="${LOOP_SCHEDULER_JOB:-loop-worker-tick}"
SCHEDULE="${LOOP_SCHEDULER_CRON:-*/15 * * * *}"

echo "setup-gcp-warehouse: project=${PROJECT} region=${REGION}"

# Prefer gcloud user ADC when application_default_credentials.json is missing.
if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]] && [[ ! -f "${HOME}/.config/gcloud/application_default_credentials.json" ]]; then
  LEGACY_ADC="$(find "${HOME}/.config/gcloud/legacy_credentials" -name adc.json 2>/dev/null | head -1 || true)"
  if [[ -n "${LEGACY_ADC}" ]]; then
    export GOOGLE_APPLICATION_CREDENTIALS="${LEGACY_ADC}"
    echo "setup-gcp-warehouse: using ${LEGACY_ADC}"
  fi
fi

gcloud services enable \
  bigquery.googleapis.com \
  bigquerydatatransfer.googleapis.com \
  analyticsadmin.googleapis.com \
  cloudscheduler.googleapis.com \
  run.googleapis.com \
  --project="${PROJECT}" --quiet

echo "setup-gcp-warehouse: loading synthetic warehouse → loop_raw + loop_metrics"
bash "${ROOT}/scripts/load-bq.sh"

echo "setup-gcp-warehouse: updating Cloud Run loop warehouse env"
gcloud run services update loop \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --update-env-vars="LOOP_BQ_DATASET=loop_raw,LOOP_BQ_METRICS_DATASET=loop_metrics,LOOP_TENANT_ID=${TENANT_ID},LOOP_TENANT_WAREHOUSE_MODE=bq_raw,LOOP_TENANT_BQ_RAW_DATASET=loop_raw,LOOP_TENANT_BQ_METRICS_DATASET=loop_metrics,LOOP_TENANT_BQ_PROJECT=${PROJECT},LOOP_TENANT_REPO=${TENANT_REPO},LOOP_TENANT_DEPLOY_URL=${COVE_URL}" \
  --quiet

ADMIN_TOKEN="${LOOP_ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  ADMIN_TOKEN="$(gcloud run services describe loop --project="${PROJECT}" --region="${REGION}" \
    --format=json 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); env=d['spec']['template']['spec']['containers'][0]['env']; print(next((e.get('value','') for e in env if e.get('name')=='LOOP_ADMIN_TOKEN'), ''))" 2>/dev/null || true)"
fi

if [[ -n "${ADMIN_TOKEN}" ]]; then
  echo "setup-gcp-warehouse: upserting tenant warehouse config on Loop"
  curl -fsS -X POST "${LOOP_URL}/api/tenants" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(python3 - <<PY
import json
print(json.dumps({
  "id": "${TENANT_ID}",
  "name": "Cove",
  "product": "Cove",
  "repo": "${TENANT_REPO}",
  "deploy_url": "${COVE_URL}",
  "warehouse_mode": "bq_raw",
  "bq_project": "${PROJECT}",
  "bq_raw_dataset": "loop_raw",
  "bq_metrics_dataset": "loop_metrics",
  "primary_metric": "purchase_conversion",
  "funnel_events": ["page_view", "view_item", "begin_checkout", "add_payment_info", "purchase"],
}))
PY
)" >/dev/null
  echo "setup-gcp-warehouse: tenant ${TENANT_ID} warehouse config saved"
else
  echo "setup-gcp-warehouse: skip tenant API (LOOP_ADMIN_TOKEN not found)" >&2
fi

if [[ -n "${ADMIN_TOKEN}" ]]; then
  echo "setup-gcp-warehouse: Cloud Scheduler → ${LOOP_URL}/api/internal/worker/tick"
  gcloud scheduler jobs delete "${SCHEDULER_JOB}" --project="${PROJECT}" --location="${REGION}" --quiet 2>/dev/null || true
  gcloud scheduler jobs create http "${SCHEDULER_JOB}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --schedule="${SCHEDULE}" \
    --uri="${LOOP_URL}/api/internal/worker/tick?limit=3" \
    --http-method=POST \
    --headers="Authorization=Bearer ${ADMIN_TOKEN}" \
    --attempt-deadline=180s \
    --quiet
  echo "setup-gcp-warehouse: scheduler ${SCHEDULER_JOB} (${SCHEDULE})"
fi

if [[ -n "${GOOGLE_ADS_CUSTOMER_ID:-}" ]]; then
  echo "setup-gcp-warehouse: Google Ads → BigQuery transfer (customer ${GOOGLE_ADS_CUSTOMER_ID})"
  bq mk --dataset --location="${REGION}" "${PROJECT}:loop_ads" 2>/dev/null || true
  EXISTING="$(bq ls --transfer_config --project_id="${PROJECT}" --format=json 2>/dev/null \
    | python3 -c "import json,sys; cf=json.load(sys.stdin) or []; print(next((c['name'] for c in cf if 'google_ads' in c.get('dataSourceId','')), ''))" 2>/dev/null || true)"
  if [[ -z "${EXISTING}" ]]; then
    echo "setup-gcp-warehouse: Ads transfer needs one browser OAuth step (BigQuery Data Transfer)"
    bq mk --transfer_config \
      --project_id="${PROJECT}" \
      --location="${REGION}" \
      --data_source=google_ads \
      --target_dataset=loop_ads \
      --display_name="Loop Google Ads" \
      -p="{\"customer_id\":\"${GOOGLE_ADS_CUSTOMER_ID}\"}" \
      || echo "setup-gcp-warehouse: complete Ads OAuth in the URL printed above, then re-run" >&2
  fi
  if [[ -n "${ADMIN_TOKEN}" ]]; then
    curl -fsS -X POST "${LOOP_URL}/api/tenants" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"id\":\"${TENANT_ID}\",\"name\":\"Cove\",\"product\":\"Cove\",\"repo\":\"${TENANT_REPO}\",\"deploy_url\":\"${COVE_URL}\",\"ads_dataset\":\"loop_ads\",\"ads_customer_id\":\"${GOOGLE_ADS_CUSTOMER_ID}\"}" >/dev/null || true
  fi
else
  echo "setup-gcp-warehouse: loop_ads demo dataset (set GOOGLE_ADS_CUSTOMER_ID for live Ads transfer)"
  bq mk --dataset --location="${REGION}" "${PROJECT}:loop_ads" 2>/dev/null || true
  bq query --use_legacy_sql=false --project_id="${PROJECT}" --location="${REGION}" \
    "CREATE OR REPLACE TABLE \`${PROJECT}.loop_ads.campaign_daily\` AS SELECT * FROM \`${PROJECT}.loop_raw.campaign_daily\`" \
    >/dev/null 2>&1 || true
  if [[ -n "${ADMIN_TOKEN}" ]]; then
    curl -fsS -X POST "${LOOP_URL}/api/tenants" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"id\":\"${TENANT_ID}\",\"name\":\"Cove\",\"product\":\"Cove\",\"repo\":\"${TENANT_REPO}\",\"deploy_url\":\"${COVE_URL}\",\"ads_dataset\":\"loop_ads\"}" >/dev/null || true
  fi
fi

echo "setup-gcp-warehouse: GA4 property + BigQuery link (Analytics Admin API)"
if curl -fsS "${LOOP_URL}/api/oauth/ga4/status" 2>/dev/null | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
  mkdir -p "${HOME}/.config/gcloud"
  gcloud storage cat "gs://${PROJECT}-loop-host/ga4_adc.json" > "${HOME}/.config/gcloud/ga4_adc.json" 2>/dev/null || true
fi
env -u GOOGLE_APPLICATION_CREDENTIALS python3 "${ROOT}/scripts/setup-ga4-cove.py" \
  --project "${PROJECT}" \
  --cove-url "${COVE_URL}" \
  --tenant-id "${TENANT_ID}" \
  --loop-url "${LOOP_URL}" \
  ${ADMIN_TOKEN:+--admin-token "${ADMIN_TOKEN}"} \
  || echo "setup-gcp-warehouse: GA4 step skipped — run scripts/setup-ga4-auth.sh once, then re-run this script" >&2

echo "setup-gcp-warehouse: done"
