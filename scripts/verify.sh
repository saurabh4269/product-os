#!/usr/bin/env bash
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
if [[ ! -d node_modules ]]; then npm install; fi
npm run lint
npm run typecheck
npm run build

echo "== remotion =="
cd "$ROOT/apps/demo"
if [[ ! -d node_modules ]]; then npm install; fi
python3 -m loop.cli export-demo -o "$ROOT/apps/demo/public/loop.json"
npx remotion compositions src/index.ts
npx remotion render src/index.ts LoopDemo /tmp/loop-demo.mp4
npx remotion render src/index.ts MacOsDemo /tmp/macos-demo.mp4
ls -la /tmp/loop-demo.mp4 /tmp/macos-demo.mp4

echo "verify: ok"
