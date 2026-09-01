#!/usr/bin/env bash
# Render architecture via excalidraw-skill workflow (build JSON -> export PNG/SVG).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXCALIDRAW="$ROOT/docs/architecture-full.excalidraw"
SVG="$ROOT/docs/architecture-full.svg"
PNG="$ROOT/docs/architecture-full.png"
JPG="$ROOT/docs/architecture-full.jpg"

python3 "$ROOT/scripts/build-architecture-excalidraw.py"

if command -v excalidraw-brute-export-cli >/dev/null 2>&1; then
  excalidraw-brute-export-cli -i "$EXCALIDRAW" -o "$PNG" -f png -s 2 -b true
  excalidraw-brute-export-cli -i "$EXCALIDRAW" -o "$SVG" -f svg -s 1 -b true
else
  curl -sf -X POST https://kroki.io/excalidraw/svg \
    -H "Content-Type: text/plain" \
    --data-binary "@$EXCALIDRAW" \
    -o "$SVG"
  convert -background white -density 220 "$SVG" "$PNG"
fi

convert -quality 93 "$PNG" "$JPG"
cp "$PNG" "$ROOT/docs/architecture.png"
cp "$JPG" "$ROOT/docs/architecture.jpg"
cp "$SVG" "$ROOT/docs/architecture.svg"
cp "$EXCALIDRAW" "$ROOT/docs/architecture.excalidraw"
identify "$PNG"
echo "render-architecture: wrote $PNG and $JPG"
