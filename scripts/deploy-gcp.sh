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
ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT},LOOP_CONSOLE_ORIGIN=*"
for key in LOOP_GITHUB_TOKEN LOOP_TENANT_REPO LOOP_TENANT_DEPLOY_URL LOOP_TENANT_BOOTSTRAP_TOKEN; do
  val="${!key:-}"
  if [[ -n "$val" ]]; then
    ENV_VARS="${ENV_VARS},${key}=${val}"
  fi
done

set +e
gcloud run deploy "${SERVICE}" \
  --image python:3.12-slim \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 2 \
  --timeout 300 \
  --cpu-boost \
  --command bash \
  --args="-c,apt-get update -qq && apt-get install -y -qq curl ca-certificates python3-pip && curl -fsSL ${BUNDLE_URL} -o /tmp/loop.tgz && mkdir -p /app && tar -xzf /tmp/loop.tgz -C /app && export PYTHONPATH=/app/vendor:/app/services/loop LOOP_STATIC_DIR=/app/static LOOP_DATA_DIR=/app/var LOOP_CONSOLE_ORIGIN=* PYTHONUNBUFFERED=1 && mkdir -p /app/var && python -m uvicorn loop.api:app --host 0.0.0.0 --port \${PORT}" \
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
