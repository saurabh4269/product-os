#!/usr/bin/env bash
# Grant Analytics Admin scope via Loop's registered OAuth redirect (no localhost mismatch).
# Opens browser once; writes ~/.config/gcloud/application_default_credentials.json
set -euo pipefail
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
BUCKET="${LOOP_BUNDLE_BUCKET:-${PROJECT}-loop-host}"
LOOP_URL="${LOOP_PUBLIC_URL:-https://loop-5uy6fkd7bq-uc.a.run.app}"
ADC="${HOME}/.config/gcloud/application_default_credentials.json"

START_URL="${LOOP_URL}/api/oauth/ga4/start"
echo "setup-ga4-auth: consent via Loop OAuth (registered redirect URI)"
echo "  ${START_URL}"
echo ""
echo "Opening browser… Approve Google Analytics access for ${PROJECT}."
if command -v xdg-open >/dev/null; then
  xdg-open "${START_URL}" >/dev/null 2>&1 || true
elif command -v open >/dev/null; then
  open "${START_URL}" || true
fi
echo "If no browser opened, visit the URL above manually."

mkdir -p "${HOME}/.config/gcloud"
for _ in $(seq 1 90); do
  if curl -fsS "${LOOP_URL}/api/oauth/ga4/status" 2>/dev/null | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
    gcloud storage cat "gs://${BUCKET}/ga4_adc.json" > "${ADC}"
    echo "Wrote ${ADC}"
    echo "Done. Run: ./scripts/setup-gcp-warehouse.sh"
    exit 0
  fi
  sleep 2
done

echo "setup-ga4-auth: timed out waiting for consent." >&2
echo "Complete auth at ${START_URL} then run:" >&2
echo "  gcloud storage cat gs://${BUCKET}/ga4_adc.json > ${ADC}" >&2
exit 1
