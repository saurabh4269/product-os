#!/usr/bin/env bash
# Cloud Run entry: fetch the LOOP bundle and serve API + console on $PORT.
set -euo pipefail
PORT="${PORT:-8080}"
APP="${LOOP_APP_DIR:-/app}"
mkdir -p "$APP"
cd "$APP"

if [[ -n "${LOOP_BUNDLE_URL:-}" ]]; then
  echo "loop-entry: fetching bundle"
  apt-get update -qq
  apt-get install -y -qq curl ca-certificates
  curl -fsSL "$LOOP_BUNDLE_URL" -o /tmp/loop.tgz
  tar -xzf /tmp/loop.tgz -C "$APP"
fi

export PYTHONPATH="${APP}/vendor:${APP}/services/loop:${PYTHONPATH:-}"
export LOOP_STATIC_DIR="${APP}/static"
export LOOP_DATA_DIR="${APP}/var"
export LOOP_CONSOLE_ORIGIN="${LOOP_CONSOLE_ORIGIN:-https://productos.heisenbug.in}"
export PYTHONUNBUFFERED=1
mkdir -p "$LOOP_DATA_DIR"
exec python -m uvicorn loop.api:app --host 0.0.0.0 --port "$PORT"
