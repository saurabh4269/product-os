#!/usr/bin/env bash
# Pre-deploy gate: same as verify.sh but skips Remotion render (~2 min saved).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv "$ROOT/services/loop/.venv"
# shellcheck disable=SC1091
source "$ROOT/services/loop/.venv/bin/activate"
pip install -q -e "$ROOT/services/loop[dev]"

echo "== warehouse =="
python3 "$ROOT/data/generate.py"

echo "== ruff =="
ruff check "$ROOT/services/loop/loop" "$ROOT/services/loop/tests" "$ROOT/data/generate.py"

echo "== pytest =="
cd "$ROOT/services/loop"
python -m pytest -q

echo "== console =="
cd "$ROOT/apps/console"
if [[ ! -d node_modules ]]; then npm ci --silent; fi
npm run lint
npm run typecheck
export LOOP_STATIC=1
unset NEXT_PUBLIC_API_URL
npm run build

echo "verify-deploy: ok"
