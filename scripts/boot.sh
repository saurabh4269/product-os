#!/usr/bin/env bash
# One command from a clean clone: warehouse, API, console.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/services/loop/.venv" ]]; then
  python3 -m venv "$ROOT/services/loop/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/services/loop/.venv/bin/activate"
pip install -q -e "$ROOT/services/loop[dev]"

python3 "$ROOT/data/generate.py"
python3 -m loop.cli detect >/tmp/loop-detect.json
python3 -m loop.cli run >/tmp/loop-run.json
python3 -m loop.cli export-demo

if [[ ! -d "$ROOT/apps/console/node_modules" ]]; then
  (cd "$ROOT/apps/console" && npm install)
fi
if [[ ! -d "$ROOT/apps/demo/node_modules" ]]; then
  (cd "$ROOT/apps/demo" && npm install)
fi

export LOOP_HOST=127.0.0.1
export LOOP_PORT=8080
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8080

echo "Starting LOOP API on :8080 and console on :3000"
python3 -m uvicorn loop.api:app --host 127.0.0.1 --port 8080 &
API_PID=$!
(cd "$ROOT/apps/console" && npm run dev -- --hostname 127.0.0.1 --port 3000) &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT
echo "API pid=$API_PID console pid=$WEB_PID"
echo "Open http://127.0.0.1:3000"
wait
