#!/usr/bin/env bash
# Create or update LOOP orchestrator on GEAP Agent Runtime (Reasoning Engine).
# Does NOT apply Agent Gateway terraform — identity on create is enough for hackathon.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
BUCKET="${LOOP_GEAP_STAGING_BUCKET:-gs://${PROJECT}-loop-host/agent_engine/}"
DISPLAY_NAME="${LOOP_GEAP_DISPLAY_NAME:-loop-incident-orchestrator}"

echo "deploy-geap-agent: project=${PROJECT} region=${REGION} bucket=${BUCKET}"

if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  export GOOGLE_CLOUD_PROJECT="${PROJECT}"
fi
export GOOGLE_CLOUD_REGION="${REGION}"
export LOOP_GEAP_ENABLED=1
export LOOP_GEAP_STAGING_BUCKET="${BUCKET}"

VENV="${ROOT}/.geap-venv"
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install -q --upgrade pip
pip install -q -r "${ROOT}/services/loop/requirements-geap.txt" -r "${ROOT}/services/loop/requirements-host.txt"

export PYTHONPATH="${ROOT}/services/loop:${ROOT}/data:${PYTHONPATH:-}"
export LOOP_DATA_DIR="${ROOT}/var/geap-deploy"
mkdir -p "${LOOP_DATA_DIR}"

python -m loop.geap_deploy --create --display-name "${DISPLAY_NAME}" --json | tee /tmp/loop-geap-engine.json

RESOURCE_NAME="$(python3 - <<'PY'
import json
print(json.load(open("/tmp/loop-geap-engine.json"))["resource_name"])
PY
)"

echo ""
echo "deploy-geap-agent: created ${RESOURCE_NAME}"
echo "Next steps:"
echo "  1. gcloud run services update loop --region=${REGION} --project=${PROJECT} \\"
echo "       --update-env-vars LOOP_GEAP_ENABLED=1,LOOP_GEAP_AGENT_ENGINE_ID=${RESOURCE_NAME},LOOP_GEAP_STAGING_BUCKET=${BUCKET}"
echo "  2. IAM: deployer needs roles/aiplatform.user and storage access on ${BUCKET}"
echo "  3. Agent Gateway (infra/terraform/gated/) stays plan-only until entitlements"
