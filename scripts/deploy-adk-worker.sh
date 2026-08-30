#!/usr/bin/env bash
# Deploy LOOP ADK worker (google-adk + Antigravity) as a second Cloud Run service.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${LOOP_ADK_CLOUD_RUN_SERVICE:-loop-adk}"
BUCKET="${LOOP_BUNDLE_BUCKET:-${PROJECT}-loop-host}"
OBJECT="loop-adk-worker.tgz"

echo "deploy-adk-worker: project=${PROJECT} region=${REGION} service=${SERVICE}"

if [[ ! -f "$ROOT/dist/loop-adk-worker.tgz" ]]; then
  bash "$ROOT/scripts/package-adk-worker.sh"
fi

gcloud storage cp "$ROOT/dist/loop-adk-worker.tgz" "gs://${BUCKET}/${OBJECT}" --project="$PROJECT"
gcloud storage objects update "gs://${BUCKET}/${OBJECT}" --add-acl-grant=entity=allUsers,role=READER --project="$PROJECT" \
  || true

BUNDLE_URL="https://storage.googleapis.com/${BUCKET}/${OBJECT}"

ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},LOOP_ADK_ENABLED=1,LOOP_ADK_LLM=1,LOOP_DATA_DIR=/app/var,LOOP_STATE_GCS_URI=gs://${BUCKET}/loop_state.db,LOOP_CODE_BACKEND=auto,LOOP_USE_VERTEX=1,LOOP_ANTIGRAVITY_VERTEX=1,LOOP_VERTEX_MODEL=gemini-2.5-flash"
for key in GOOGLE_API_KEY LOOP_ADMIN_TOKEN LOOP_GITHUB_TOKEN; do
  val="${!key:-}"
  if [[ -n "$val" ]]; then
    ENV_VARS="${ENV_VARS},${key}=${val}"
  fi
done

gcloud run deploy "${SERVICE}" \
  --image python:3.12-slim \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300 \
  --cpu-boost \
  --command bash \
  --args="-c,apt-get update -qq && apt-get install -y -qq curl ca-certificates git nodejs npm && curl -fsSL ${BUNDLE_URL} -o /tmp/loop-adk.tgz && mkdir -p /app && tar -xzf /tmp/loop-adk.tgz -C /app && export PYTHONPATH=/app/vendor:/app/services/loop LOOP_DATA_DIR=/app/var PYTHONUNBUFFERED=1 && mkdir -p /app/var && python -m uvicorn loop.adk_api:app --host 0.0.0.0 --port \${PORT}" \
  --set-env-vars "${ENV_VARS}" \
  --quiet

ADK_URL="$(gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" --format='value(status.url)')"
echo "deploy-adk-worker: ${ADK_URL}"
echo "Point main loop at: LOOP_ADK_WORKER_URL=${ADK_URL}"
