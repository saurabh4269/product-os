#!/usr/bin/env bash
# Assemble Product OS film: title (Remotion) + live multi-tab capture + end (Remotion)
# plus natural neural voiceover audio track.
# Uses filter_complex concat to avoid demuxer timestamp freezes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/apps/demo"
OUT="$ROOT/apps/console/public/demo"
TITLE="$DEMO/out/title.mp4"
END="$DEMO/out/end.mp4"
LIVE="${1:-$DEMO/out/live-walkthrough.mp4}"
AUDIO="$DEMO/out/narration/voiceover_master.mp3"
FINAL="$OUT/product-os-demo.mp4"

TITLE_NORM="$(mktemp --suffix=_title.mp4)"
END_NORM="$(mktemp --suffix=_end.mp4)"
TEMP_VIDEO="$(mktemp --suffix=.mp4)"

mkdir -p "$OUT" "$DEMO/out"

for f in "$TITLE" "$LIVE" "$END"; do
  if [[ ! -f "$f" ]]; then
    echo "assemble-product-film: missing $f" >&2
    exit 1
  fi
done

echo "=== Normalizing title and end cards to yuv420p @ 30fps ==="
ffmpeg -y -i "$TITLE" -an -pix_fmt yuv420p -r 30 "$TITLE_NORM" 2>/dev/null
ffmpeg -y -i "$END" -an -pix_fmt yuv420p -r 30 "$END_NORM" 2>/dev/null

echo "=== Filter-complex concatenating title + live + end ==="
ffmpeg -y \
  -i "$TITLE_NORM" \
  -i "$LIVE" \
  -i "$END_NORM" \
  -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" \
  -map "[v]" \
  -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -r 30 \
  "$TEMP_VIDEO"

if [[ -f "$AUDIO" ]]; then
  echo "=== Multiplexing audio narration with 5.0s title offset ==="
  ffmpeg -y -i "$TEMP_VIDEO" -i "$AUDIO" \
    -filter_complex "[1:a]adelay=5000|5000,apad[a]" \
    -map 0:v:0 -map "[a]" \
    -c:v copy \
    -c:a aac -b:a 128k \
    -shortest \
    -movflags +faststart \
    "$FINAL"
else
  echo "=== Finalizing video-only ==="
  ffmpeg -y -i "$TEMP_VIDEO" -c:v copy -movflags +faststart "$FINAL"
fi

rm -f "$TITLE_NORM" "$END_NORM" "$TEMP_VIDEO"
ls -lh "$FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL"
echo "wrote $FINAL"
