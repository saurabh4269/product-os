#!/usr/bin/env bash
# Wire productos.heisenbug.in → Cloud Run service loop (us-central1).
# Prerequisites: CNAME productos → ghs.googlehosted.com (Cloudflare DNS only / grey cloud).
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${LOOP_SERVICE:-loop}"
DOMAIN="${LOOP_CUSTOM_DOMAIN:-productos.heisenbug.in}"
BASE_DOMAIN="${LOOP_BASE_DOMAIN:-heisenbug.in}"

echo "Project: $PROJECT  Region: $REGION  Service: $SERVICE"
echo "Custom domain: $DOMAIN"

echo "→ Updating LOOP_PUBLIC_URL on Cloud Run…"
gcloud run services update "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --update-env-vars="LOOP_PUBLIC_URL=https://${DOMAIN}" >/dev/null

echo "→ Ensuring domain mapping exists…"
if ! gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud beta run domain-mappings create \
    --service="$SERVICE" \
    --domain="$DOMAIN" \
    --region="$REGION" \
    --project="$PROJECT"
fi

echo "→ Domain mapping status:"
gcloud beta run domain-mappings describe \
  --domain="$DOMAIN" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="yaml(status.conditions,status.resourceRecords)"

if gcloud domains list-user-verified --project="$PROJECT" 2>/dev/null | grep -q "$BASE_DOMAIN"; then
  echo "✓ $BASE_DOMAIN is verified for this Google account."
else
  echo ""
  echo "Verify $BASE_DOMAIN once (covers all subdomains like $DOMAIN):"
  echo "  gcloud domains verify $BASE_DOMAIN"
  echo "  → Search Console → Domain property → DNS TXT record at Cloudflare"
  echo "  https://search.google.com/search-console/welcome?new_domain_name=${BASE_DOMAIN}"
  echo ""
  echo "After TXT propagates, re-run this script."
  exit 1
fi

echo ""
echo "Waiting for certificate (up to ~15 min)…"
for _ in $(seq 1 30); do
  ready=$(gcloud beta run domain-mappings describe --domain="$DOMAIN" --region="$REGION" --project="$PROJECT" \
    --format="value(status.conditions[?type='Ready'].status)" 2>/dev/null || true)
  if [[ "$ready" == "True" ]]; then
    echo "✓ https://${DOMAIN} is ready"
    curl -sSI "https://${DOMAIN}/api/status" | head -5 || true
    exit 0
  fi
  sleep 30
done

echo "Still provisioning — check:"
echo "  gcloud beta run domain-mappings describe --domain=$DOMAIN --region=$REGION --project=$PROJECT"
exit 2
