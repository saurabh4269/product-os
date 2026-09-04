#!/usr/bin/env bash
# Assemble Product OS film: title (Remotion) + live capture + end (Remotion).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/apps/demo"
OUT="$ROOT/apps/console/public/demo"
TITLE="$DEMO/out/title.mp4"
END="$DEMO/out/end.mp4"
LIVE="${1:-$DEMO/out/live-walkthrough.mp4}"
FINAL="$OUT/product-os-demo.mp4"
LIST="$(mktemp)"

mkdir -p "$OUT" "$DEMO/out"

for f in "$TITLE" "$LIVE" "$END"; do
  if [[ ! -f "$f" ]]; then
    echo "assemble-product-film: missing $f" >&2
    exit 1
  fi
done

printf "file '%s'\nfile '%s'\nfile '%s'\n" "$TITLE" "$LIVE" "$END" >"$LIST"

ffmpeg -y -f concat -safe 0 -i "$LIST" \
  -map 0:v:0 -an \
  -c:v libx264 -preset medium -crf 28 -pix_fmt yuv420p -r 30 \
  -movflags +faststart \
  "$FINAL"

rm -f "$LIST"
ls -lh "$FINAL"
echo "wrote $FINAL"
