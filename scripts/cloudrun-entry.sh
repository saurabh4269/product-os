#!/usr/bin/env bash
# Cloud Run entry: fetch the LOOP bundle and serve API + console on $PORT.
# No apt-get — python:3.12-slim already has CA certs; urllib fetches the tarball.
set -euo pipefail
PORT="${PORT:-8080}"
APP="${LOOP_APP_DIR:-/app}"
mkdir -p "$APP"
cd "$APP"

if [[ -n "${LOOP_BUNDLE_URL:-}" ]]; then
  echo "loop-entry: fetching bundle"
  python -c 'import os,urllib.request as u; u.urlretrieve(os.environ["LOOP_BUNDLE_URL"], "/tmp/loop.tgz")'
  tar -xzf /tmp/loop.tgz -C "$APP"
fi

export PYTHONPATH="${APP}/vendor:${APP}/services/loop:${PYTHONPATH:-}"
export LOOP_STATIC_DIR="${APP}/static"
export LOOP_DATA_DIR="${APP}/var"
export LOOP_CONSOLE_ORIGIN="${LOOP_CONSOLE_ORIGIN:-https://productos.heisenbug.in}"
export PYTHONUNBUFFERED=1
mkdir -p "$LOOP_DATA_DIR"
exec python -m uvicorn loop.api:app --host 0.0.0.0 --port "$PORT"
