#!/usr/bin/env bash
# Build a slim hosted bundle: vendor wheels + static console + code. No credentials.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/host"
if ! rm -rf "$DIST" 2>/dev/null; then
  docker run --rm -v "$ROOT/dist:/dist" alpine:3.20 rm -rf /dist/host
fi
mkdir -p "$DIST/vendor" "$DIST/static" "$DIST/services/loop" "$DIST/data" "$DIST/config" "$DIST/playbooks" "$DIST/var"

# Vendor for Cloud Run python:3.12-slim (local python is 3.13; native wheels must match 3.12).
docker run --rm \
  -v "$ROOT/services/loop/requirements-host.txt:/req.txt:ro" \
  -v "$DIST/vendor:/vendor" \
  python:3.12-slim \
  bash -c "pip install -q --upgrade pip && pip install -q -r /req.txt --target /vendor"
cp -a "$ROOT/services/loop/loop" "$DIST/services/loop/loop"
cp -a "$ROOT/services/loop/pyproject.toml" "$DIST/services/loop/"
cp -a "$ROOT/data/." "$DIST/data/"
cp -a "$ROOT/config/." "$DIST/config/"
cp -a "$ROOT/playbooks/." "$DIST/playbooks/"
cp "$ROOT/scripts/cloudrun-entry.sh" "$DIST/cloudrun-entry.sh"

export LOOP_STATIC=1
unset NEXT_PUBLIC_API_URL
(cd "$ROOT/apps/console" && npm ci --silent && npm run build)
cp -a "$ROOT/apps/console/out/." "$DIST/static/"

mkdir -p "$ROOT/dist"
tar -C "$DIST" -czf "$ROOT/dist/loop-host.tgz" .
echo "wrote $ROOT/dist/loop-host.tgz ($(du -h "$ROOT/dist/loop-host.tgz" | awk '{print $1}'))"
