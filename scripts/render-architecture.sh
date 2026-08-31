#!/usr/bin/env bash
# Render Archify HTML from JSON IR (architecture + investigation workflow).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCH_DIR="$ROOT/apps/console/public/architecture"
ARCHIFY_BIN="${ARCHIFY_BIN:-}"

if [[ -z "$ARCHIFY_BIN" ]]; then
  for candidate in \
    "$ROOT/../archify/archify/bin/archify.mjs" \
    "/tmp/archify-check/archify/bin/archify.mjs"; do
    if [[ -f "$candidate" ]]; then
      ARCHIFY_BIN="$candidate"
      break
    fi
  done
fi

if [[ ! -f "$ARCHIFY_BIN" ]]; then
  echo "Archify CLI not found. Clone https://github.com/tt-a1i/archify or set ARCHIFY_BIN." >&2
  exit 1
fi

render() {
  local type="$1"
  local json="$2"
  local html="$3"
  node "$ARCHIFY_BIN" deliver "$type" "$json" "$html" --quality standard
  echo "Wrote $html"
}

render architecture "$ARCH_DIR/product-os.architecture.json" "$ARCH_DIR/product-os.architecture.html"
render workflow "$ARCH_DIR/product-os.investigation.workflow.json" "$ARCH_DIR/product-os.investigation.html"
