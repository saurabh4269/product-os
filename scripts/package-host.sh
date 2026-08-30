#!/usr/bin/env bash
# Build a slim hosted bundle: vendor wheels + static console + code. No credentials.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/host"
rm -rf "$DIST"
mkdir -p "$DIST/vendor" "$DIST/static" "$DIST/services/loop" "$DIST/data" "$DIST/config" "$DIST/playbooks" "$DIST/var"

python3 -m pip install -q -r "$ROOT/services/loop/requirements-host.txt" --target "$DIST/vendor"
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
