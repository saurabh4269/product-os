#!/usr/bin/env bash
# Decode runtime secret GCP_SA_KEY and activate ADC. Never echo the key or JSON.
set -euo pipefail

KEY_FILE="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/loop-sa.json}"
mkdir -p "$(dirname "$KEY_FILE")"

if [[ -f "$KEY_FILE" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"
else
  if [[ -z "${GCP_SA_KEY:-}" ]]; then
    echo "gcp-activate: GCP_SA_KEY unset; skipping ADC (local demo still works)" >&2
    exit 0
  fi
  python3 - <<'PY'
import base64, os, pathlib
raw = os.environ["GCP_SA_KEY"].strip()
try:
    data = base64.b64decode(raw, validate=True)
except Exception:
    data = raw.encode()
dest = pathlib.Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
                    pathlib.Path.home() / ".config/gcloud/loop-sa.json")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_bytes(data)
os.chmod(dest, 0o600)
print(f"gcp-activate: wrote ADC file ({dest.stat().st_size} bytes)", flush=True)
PY
  export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/loop-sa.json}"
fi

if command -v gcloud >/dev/null 2>&1; then
  gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" --quiet >/dev/null
  gcloud config set project "${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}" --quiet >/dev/null
  echo "gcp-activate: gcloud account active for ${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
fi
