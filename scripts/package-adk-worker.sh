#!/usr/bin/env bash
# ADK + Antigravity worker bundle — no console static.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/adk-worker"
rm -rf "$DIST"
mkdir -p "$DIST/vendor" "$DIST/services/loop" "$DIST/data" "$DIST/config" "$DIST/playbooks" "$DIST/var"

docker run --rm \
  -v "$ROOT/services/loop/requirements-adk-worker.txt:/req.txt:ro" \
  -v "$DIST/vendor:/vendor" \
  python:3.12-slim \
  bash -c "pip install -q --upgrade pip && pip install -q -r /req.txt --target /vendor"

cp -a "$ROOT/services/loop/loop" "$DIST/services/loop/loop"
cp -a "$ROOT/services/loop/pyproject.toml" "$DIST/services/loop/"
cp -a "$ROOT/data/." "$DIST/data/"
cp -a "$ROOT/config/." "$DIST/config/"
cp -a "$ROOT/playbooks/." "$DIST/playbooks/"

mkdir -p "$ROOT/dist"
tar -C "$DIST" -czf "$ROOT/dist/loop-adk-worker.tgz" .
echo "wrote $ROOT/dist/loop-adk-worker.tgz ($(du -h "$ROOT/dist/loop-adk-worker.tgz" | awk '{print $1}'))"
