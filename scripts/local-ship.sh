#!/usr/bin/env bash
# Ship Product OS (LOOP) to Cloud Run — local laptop path.
# User URL: https://productos.heisenbug.in
# Never use: gcloud run deploy --source
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${GOOGLE_CLOUD_PROJECT:-mystical-timing-442601-q8}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${LOOP_CLOUD_RUN_SERVICE:-loop}"
PUBLIC_URL="${LOOP_PUBLIC_URL:-https://productos.heisenbug.in}"
HANG_ROOM="${LOOP_HANG_ROOM_ID:-room_f627763ea9}"

echo "==> Product OS local ship"
echo "    project=$PROJECT region=$REGION service=$SERVICE"
echo "    url=$PUBLIC_URL hang=$HANG_ROOM"

# --- auth checks ---
command -v gcloud >/dev/null || { echo "missing gcloud"; exit 1; }
command -v docker >/dev/null || { echo "missing docker (needed for package-host vendor wheels)"; exit 1; }
command -v node >/dev/null || { echo "missing node"; exit 1; }
command -v npm >/dev/null || { echo "missing npm"; exit 1; }
command -v python3 >/dev/null || { echo "missing python3"; exit 1; }

gcloud config set project "$PROJECT" >/dev/null
ACTIVE="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1 || true)"
[[ -n "$ACTIVE" ]] || { echo "run: gcloud auth login"; exit 1; }
echo "    gcloud account: $ACTIVE"

# --- latest main ---
git fetch origin main
git checkout main
git pull --ff-only origin main
echo "    git tip: $(git log -1 --oneline)"

# --- LOOP_ADMIN_TOKEN (for persist + post-checks) ---
if [[ -z "${LOOP_ADMIN_TOKEN:-}" ]]; then
  LOOP_ADMIN_TOKEN="$(python3 - <<'PY'
import json, subprocess
raw = subprocess.check_output([
  "gcloud","run","services","describe","loop",
  "--project", "mystical-timing-442601-q8",
  "--region", "us-central1", "--format=json",
], text=True)
env = (json.loads(raw).get("spec") or {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("env") or []
print(next((e.get("value") or "" for e in env if e.get("name") == "LOOP_ADMIN_TOKEN"), ""))
PY
)"
  export LOOP_ADMIN_TOKEN
fi
[[ -n "${LOOP_ADMIN_TOKEN:-}" ]] || { echo "LOOP_ADMIN_TOKEN not on live revision and not in env"; exit 1; }
echo "    LOOP_ADMIN_TOKEN: present (not printed)"

# --- preflight: do NOT deploy over a bad snapshot ---
CFG_CODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 "${PUBLIC_URL}/api/config" || true)"
echo "    preflight /api/config: ${CFG_CODE:-fail}"
if [[ "$CFG_CODE" == "503" ]]; then
  echo "ABORT: live is 503/OOM — fix instance first; do not overwrite GCS snapshot"
  exit 1
fi

HANG_CODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 90 \
  -H "Authorization: Bearer ${LOOP_ADMIN_TOKEN}" \
  "${PUBLIC_URL}/api/rooms/${HANG_ROOM}" || true)"
echo "    preflight hang GET: ${HANG_CODE:-fail}"
if [[ "$HANG_CODE" != "200" ]]; then
  echo "WARN: hang room not 200 — deploy may still proceed, but demo room may be stale"
  if [[ "${LOOP_SHIP_FORCE:-}" == "1" ]]; then
    echo "    LOOP_SHIP_FORCE=1 — continuing"
  elif [[ -t 0 ]]; then
    read -r -p "Continue anyway? [y/N] " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 1
  else
    echo "ABORT: non-interactive and hang room not 200 (set LOOP_SHIP_FORCE=1 to override)"
    exit 1
  fi
fi

# --- optional: GitHub token for tenant PR path ---
if [[ -z "${LOOP_GITHUB_TOKEN:-}" ]] && command -v gh >/dev/null; then
  export LOOP_GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
fi

# --- package (CRITICAL: unset baked localhost) ---
unset NEXT_PUBLIC_API_URL LOOP_STATIC
if ! rm -rf "$ROOT/dist/host" "$ROOT/dist/loop-host.tgz" 2>/dev/null; then
  docker run --rm -v "$ROOT/dist:/dist" alpine:3.20 rm -rf /dist/host /dist/loop-host.tgz
fi

echo "==> package-host.sh (docker + next build; a few minutes)"
./scripts/package-host.sh

# sanity: no localhost baked into static JS
if grep -R "127.0.0.1:8080" "$ROOT/dist/host/static" --include='*.js' -q; then
  echo "ABORT: localhost API URL baked into static JS — unset NEXT_PUBLIC_API_URL and rebuild"
  exit 1
fi

# --- deploy (persist runs inside deploy-gcp.sh when /api/config is 200) ---
echo "==> deploy-gcp.sh"
./scripts/deploy-gcp.sh

REV="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.latestReadyRevisionName)')"
echo "    new revision: $REV"

# --- postflight ---
sleep 8
for path in / /rooms /shop /api/config; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 60 "${PUBLIC_URL}${path}" || echo fail)"
  echo "    post ${path}: ${code}"
done

HANG_POST="$(curl -sS -o /tmp/loop-hang.json -w '%{http_code}' --max-time 90 \
  -H "Authorization: Bearer ${LOOP_ADMIN_TOKEN}" \
  "${PUBLIC_URL}/api/rooms/${HANG_ROOM}" || true)"
echo "    post hang: ${HANG_POST:-fail}"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/tmp/loop-hang.json")
if not p.exists():
    raise SystemExit
d = json.loads(p.read_text())
b = d.get("bundle") or {}
print("    hang state:", b.get("state"), "pending:", b.get("pending_actions"))
PY

echo
echo "DONE. Hard-refresh ${PUBLIC_URL}"
echo "Never merge Cove PR #17. Never approve act_4754e1ae24f5."
