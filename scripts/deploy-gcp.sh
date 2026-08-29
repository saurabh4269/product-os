#!/usr/bin/env bash
# Deploy LOOP API to Cloud Run (cheap). Fails with exact IAM grants if the SA cannot deploy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${LOOP_CLOUD_RUN_SERVICE:-loop-api}"

echo "deploy-gcp: project=${PROJECT} region=${REGION} service=${SERVICE}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud not on PATH. Run ./scripts/install-gcloud.sh" >&2
  exit 1
fi

set +e
gcloud run deploy "${SERVICE}" \
  --source "${ROOT}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},LOOP_CONSOLE_ORIGIN=*" \
  --quiet
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  cat <<'EOF' >&2

Cloud Run deploy was denied for this service account (expected if you have not
granted Cloud Build / Artifact Registry / Cloud Run Admin).

As project owner, run once:

  PROJECT=mystical-timing-442601-q8
  SA=loop-cloud-agent@${PROJECT}.iam.gserviceaccount.com

  gcloud services enable \
    run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
    --project=$PROJECT

  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/run.admin
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/artifactregistry.admin
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/cloudbuild.builds.editor
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/iam.serviceAccountUser
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/storage.admin

Then re-run: ./scripts/deploy-gcp.sh

Do not apply infra/terraform/gated (Agent Gateway / SGP / telephony).
EOF
  exit $STATUS
fi

gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" --format='value(status.url)'
