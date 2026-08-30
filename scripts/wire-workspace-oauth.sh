#!/usr/bin/env bash
# Wire Workspace OAuth client into hosted Product OS (Cloud Run + Connect API).
#
# Google does NOT allow creating a Gmail/Calendar Web OAuth client via gcloud
# (gcloud iam oauth-clients only accepts cloud-platform / openid / email / groups).
# Create the Web client once in Auth Platform, then run this script.
#
# Usage:
#   export LOOP_GOOGLE_OAUTH_CLIENT_ID='....apps.googleusercontent.com'
#   export LOOP_GOOGLE_OAUTH_CLIENT_SECRET='...'
#   ./scripts/wire-workspace-oauth.sh
#
# Never commit the secret. Prefer: gcloud run services update ... --update-secrets=
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE="${LOOP_SERVICE:-loop}"
BASE="${LOOP_PUBLIC_URL:-https://loop-5uy6fkd7bq-uc.a.run.app}"
REDIRECT="${BASE}/api/oauth/google/callback"

CID="${LOOP_GOOGLE_OAUTH_CLIENT_ID:-}"
CSEC="${LOOP_GOOGLE_OAUTH_CLIENT_SECRET:-}"

# Strip common paste mistakes (http:// prefix, trailing slash, quotes)
CID="${CID#http://}"
CID="${CID#https://}"
CID="${CID%/}"
CID="${CID%\"}"
CID="${CID#\"}"
CID="${CID%\'}"
CID="${CID#\'}"
CSEC="${CSEC%\"}"
CSEC="${CSEC#\"}"
CSEC="${CSEC%\'}"
CSEC="${CSEC#\'}"
CSEC="$(printf '%s' "$CSEC" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
export LOOP_GOOGLE_OAUTH_CLIENT_ID="$CID"
export LOOP_GOOGLE_OAUTH_CLIENT_SECRET="$CSEC"

if [[ -z "$CID" || -z "$CSEC" ]]; then
  cat <<EOF
Missing LOOP_GOOGLE_OAUTH_CLIENT_ID / LOOP_GOOGLE_OAUTH_CLIENT_SECRET.

Create a Web client in the Console (gcloud cannot mint Workspace scopes):
  1. https://console.cloud.google.com/auth/overview?project=${PROJECT}
     App name: Product OS · External · Testing
  2. https://console.cloud.google.com/auth/audience?project=${PROJECT}
     Add your Google account as a test user
  3. Enable APIs (already done via gcloud if this script's prerequisites ran):
     gmail.googleapis.com · calendar-json.googleapis.com
  4. https://console.cloud.google.com/auth/clients/create?project=${PROJECT}
     Type: Web application
     Redirect URI (exact): ${REDIRECT}
  5. export LOOP_GOOGLE_OAUTH_CLIENT_ID='123456789-xxxx.apps.googleusercontent.com'
     export LOOP_GOOGLE_OAUTH_CLIENT_SECRET='GOCSPX-...'
     # Do NOT prefix client id with http:// or add a trailing /
     ./scripts/wire-workspace-oauth.sh
EOF
  exit 1
fi

if [[ "$CID" == http* ]] || [[ "$CID" == */ ]] || [[ "$CID" != *.apps.googleusercontent.com ]]; then
  echo "Client ID still looks wrong after cleanup: expected ….apps.googleusercontent.com" >&2
  echo "Got length=${#CID}" >&2
  exit 1
fi

echo "Enabling Gmail + Calendar APIs on ${PROJECT}..."
gcloud services enable gmail.googleapis.com calendar-json.googleapis.com --project="$PROJECT" >/dev/null

echo "Setting client env on Cloud Run ${SERVICE} (secret not printed)..."
gcloud run services update "$SERVICE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --update-env-vars="LOOP_GOOGLE_OAUTH_CLIENT_ID=${CID},LOOP_GOOGLE_OAUTH_CLIENT_SECRET=${CSEC},LOOP_PUBLIC_URL=${BASE},LOOP_TENANT_REPO=saurabh4269/cove,LOOP_TENANT_DEPLOY_URL=https://cove-5uy6fkd7bq-uc.a.run.app" \
  --quiet

echo "Posting client to ${BASE}/api/oauth/google/client ..."
curl -sS -X POST "${BASE}/api/oauth/google/client" \
  -H 'content-type: application/json' \
  -d "$(python3 - <<PY
import json, os
print(json.dumps({
  "client_id": os.environ["LOOP_GOOGLE_OAUTH_CLIENT_ID"],
  "client_secret": os.environ["LOOP_GOOGLE_OAUTH_CLIENT_SECRET"],
}))
PY
)" | python3 -m json.tool

echo
echo "Status:"
curl -sS "${BASE}/api/oauth/google" | python3 -m json.tool
echo
echo "Next (browser, once): open"
echo "  ${BASE}/connect"
echo "and click Authorize Gmail and Calendar (test user only)."
echo "Or open: ${BASE}/api/oauth/google/start"
