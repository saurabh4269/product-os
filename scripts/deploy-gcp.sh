#!/usr/bin/env bash
# Host LOOP on Cloud Run using a public Python image + GCS bundle (no Cloud Build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${LOOP_CLOUD_RUN_SERVICE:-loop}"
BUCKET="${LOOP_BUNDLE_BUCKET:-${PROJECT}-loop-host}"
OBJECT="loop-host.tgz"

echo "deploy-gcp: project=${PROJECT} region=${REGION} service=${SERVICE}"

if [[ ! -f "$ROOT/dist/loop-host.tgz" ]]; then
  bash "$ROOT/scripts/package-host.sh"
fi

gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" --project="$PROJECT"

gcloud storage cp "$ROOT/dist/loop-host.tgz" "gs://${BUCKET}/${OBJECT}" --project="$PROJECT"
# Public read so the Cloud Run container can curl without extra IAM.
gcloud storage objects update "gs://${BUCKET}/${OBJECT}" --add-acl-grant=entity=allUsers,role=READER --project="$PROJECT" \
  || gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member=allUsers --role=roles/storage.objectViewer --project="$PROJECT" \
  || true

BUNDLE_URL="https://storage.googleapis.com/${BUCKET}/${OBJECT}"
echo "deploy-gcp: bundle ${BUNDLE_URL}"

# python:3.12-slim is public; Cloud Build is not required.
if [[ -z "${LOOP_GITHUB_TOKEN:-}" ]] && command -v gh >/dev/null; then
  LOOP_GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
fi
COVE_URL="${LOOP_TENANT_DEPLOY_URL:-https://cove-5uy6fkd7bq-uc.a.run.app}"
ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},LOOP_CONSOLE_ORIGIN=https://productos.heisenbug.in,LOOP_PUBLIC_URL=https://productos.heisenbug.in,LOOP_OAUTH_GCS_URI=gs://${BUCKET}/workspace_oauth.json,LOOP_FLAGS_GCS_URI=gs://${BUCKET}/tenant_flags.json,LOOP_STATE_GCS_URI=gs://${BUCKET}/loop_state.db,LOOP_CODE_REQUIRE_TESTS=1,LOOP_PUBSUB_TOPIC=loop.signals,LOOP_TASKS_QUEUE=loop-jobs,LOOP_USE_VERTEX=1,LOOP_ANTIGRAVITY_VERTEX=1,LOOP_VERTEX_MODEL=gemini-2.5-flash,LOOP_BQ_DATASET=loop_raw,LOOP_BQ_METRICS_DATASET=loop_metrics,LOOP_TENANT_ID=acme,LOOP_TENANT_REPO=saurabh4269/cove,LOOP_TENANT_DEPLOY_URL=${COVE_URL},LOOP_TENANT_WAREHOUSE_MODE=bq_raw,LOOP_TENANT_BQ_PROJECT=${PROJECT},LOOP_TENANT_BQ_RAW_DATASET=loop_raw,LOOP_TENANT_BQ_METRICS_DATASET=loop_metrics,LOOP_TENANT_PRIMARY_METRIC=purchase_conversion,LOOP_FIRESTORE_MEMORY=1,LOOP_INLINE_WORKER=1,LOOP_AUTO_INVESTIGATE=1"
# Tenant bootstrap is optional — override LOOP_TENANT_* in env before deploy. Connect can refine per tenant.

# Preserve secrets from the live revision when not set in the shell (deploy --set-env-vars replaces all).
PRESERVE_KEYS=(LOOP_ADMIN_TOKEN LOOP_TENANT_BOOTSTRAP_TOKEN LOOP_GITHUB_TOKEN LOOP_GOOGLE_OAUTH_CLIENT_ID LOOP_GOOGLE_OAUTH_CLIENT_SECRET TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_FROM_NUMBER GOOGLE_API_KEY)
EXISTING_JSON="$(gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" --format=json 2>/dev/null || true)"
if [[ -n "${EXISTING_JSON}" ]]; then
  for key in "${PRESERVE_KEYS[@]}"; do
    if [[ -z "${!key:-}" ]]; then
      val="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); env=(d.get('spec') or {}).get('template',{}).get('spec',{}).get('containers',[{}])[0].get('env') or []; print(next((e.get('value') or '' for e in env if e.get('name')==sys.argv[2]), ''))" "${EXISTING_JSON}" "${key}" 2>/dev/null || true)"
      if [[ -n "${val}" ]]; then
        export "${key}=${val}"
        echo "deploy-gcp: preserved ${key} from revision"
      fi
    fi
  done
fi

# Cloud Tasks queue for durable background jobs (best-effort; inline fallback if missing).
if gcloud services list --enabled --project="$PROJECT" --filter="name:cloudtasks.googleapis.com" --format="value(name)" 2>/dev/null | grep -q cloudtasks; then
  gcloud tasks queues describe loop-jobs --location="$REGION" --project="$PROJECT" >/dev/null 2>&1 \
    || gcloud tasks queues create loop-jobs --location="$REGION" --project="$PROJECT" --max-dispatches-per-second=2 --max-concurrent-dispatches=1 \
    || ENV_VARS="${ENV_VARS},LOOP_TASKS_DISABLE=1"
else
  ENV_VARS="${ENV_VARS},LOOP_TASKS_DISABLE=1"
fi

# Wire ADK worker when loop-adk is already deployed (optional second service).
ADK_URL="$(gcloud run services describe loop-adk --project="$PROJECT" --region="$REGION" --format='value(status.url)' 2>/dev/null || true)"
if [[ -n "$ADK_URL" ]]; then
  ENV_VARS="${ENV_VARS},LOOP_ADK_WORKER_URL=${ADK_URL}"
  echo "deploy-gcp: ADK worker ${ADK_URL}"
fi
for key in LOOP_GITHUB_TOKEN LOOP_TENANT_REPO LOOP_TENANT_DEPLOY_URL LOOP_TENANT_BOOTSTRAP_TOKEN LOOP_TENANT_ID LOOP_TENANT_NAME LOOP_TENANT_PRODUCT LOOP_TENANT_BQ_PROJECT LOOP_TENANT_BQ_RAW_DATASET LOOP_TENANT_BQ_METRICS_DATASET LOOP_TENANT_GA4_PROPERTY_ID LOOP_TENANT_GA4_DATASET LOOP_TENANT_ADS_DATASET LOOP_TENANT_WAREHOUSE_MODE LOOP_TENANT_PRIMARY_METRIC LOOP_TENANT_FUNNEL_EVENTS LOOP_GOOGLE_OAUTH_CLIENT_ID LOOP_GOOGLE_OAUTH_CLIENT_SECRET TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_FROM_NUMBER GOOGLE_API_KEY LOOP_ADMIN_TOKEN LOOP_ADK_WORKER_URL; do
  val="${!key:-}"
  if [[ -n "$val" ]]; then
    ENV_VARS="${ENV_VARS},${key}=${val}"
  fi
done

# Production profile: close eval approvals and defer verify when admin token is set.
if [[ -n "${LOOP_ADMIN_TOKEN:-}" ]]; then
  ENV_VARS="${ENV_VARS},LOOP_EVAL=0,LOOP_VERIFY_DEFER=1,LOOP_WORKER_SECRET=${LOOP_ADMIN_TOKEN}"
fi

# Persist live sqlite when the service is healthy so this deploy cannot restore a stale GCS DB.
PUBLIC_URL="${LOOP_PUBLIC_URL:-https://productos.heisenbug.in}"
if [[ -n "${LOOP_ADMIN_TOKEN:-}" ]]; then
  cfg_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "${PUBLIC_URL}/api/config" || true)"
  echo "deploy-gcp: live /api/config ${cfg_code}"
  if [[ "${cfg_code}" == "200" ]]; then
    persist_code="$(curl -sS -o /tmp/loop-persist.json -w '%{http_code}' --max-time 45 \
      -X POST -H "Authorization: Bearer ${LOOP_ADMIN_TOKEN}" \
      "${PUBLIC_URL}/api/internal/state/persist" || true)"
    echo "deploy-gcp: persist HTTP ${persist_code}"
  elif [[ "${cfg_code}" == "503" ]]; then
    echo "deploy-gcp: live 503 — skip persist so a good GCS snapshot is not overwritten"
  fi
fi

# ^|^ so gcloud does not split urlretrieve(url, path) on the comma.
# One-arg urlretrieve writes a random NamedTemporaryFile — always pass /tmp/loop.tgz.
set +e
gcloud run deploy "${SERVICE}" \
  --image python:3.12-slim \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 2 \
  --timeout 300 \
  --cpu-boost \
  --command bash \
  --args="^|^-c|python -c 'import urllib.request as u; u.urlretrieve(\"${BUNDLE_URL}\", \"/tmp/loop.tgz\")' && mkdir -p /app && tar -xzf /tmp/loop.tgz -C /app && export PYTHONPATH=/app/vendor:/app/services/loop LOOP_STATIC_DIR=/app/static LOOP_DATA_DIR=/app/var LOOP_CONSOLE_ORIGIN=https://productos.heisenbug.in PYTHONUNBUFFERED=1 && mkdir -p /app/var && python -m uvicorn loop.api:app --host 0.0.0.0 --port \${PORT}" \
  --set-env-vars "${ENV_VARS}" \
  --quiet
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  cat <<'EOF' >&2

Cloud Run deploy failed. If this is IAM, as project owner run docs/DEPLOY.md grants
then re-run ./scripts/deploy-gcp.sh
EOF
  exit $STATUS
fi

gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" --format='value(status.url)'
echo "deploy-gcp: optional Cloud Scheduler → POST /api/internal/worker/tick (Bearer LOOP_ADMIN_TOKEN) for BQ detect + job drain"
