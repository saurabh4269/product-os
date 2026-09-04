#!/usr/bin/env bash
# Assemble Product OS film: title (Remotion) + live multi-tab capture + end (Remotion)
# plus natural neural voiceover audio track.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/apps/demo"
OUT="$ROOT/apps/console/public/demo"
TITLE="$DEMO/out/title.mp4"
END="$DEMO/out/end.mp4"
LIVE="${1:-$DEMO/out/live-walkthrough.mp4}"
AUDIO="$DEMO/out/narration/voiceover_master.mp3"
FINAL="$OUT/product-os-demo.mp4"
LIST="$(mktemp)"
TEMP_VIDEO="$(mktemp --suffix=.mp4)"

mkdir -p "$OUT" "$DEMO/out"

for f in "$TITLE" "$LIVE" "$END"; do
  if [[ ! -f "$f" ]]; then
    echo "assemble-product-film: missing $f" >&2
    exit 1
  fi
done

printf "file '%s'\nfile '%s'\nfile '%s'\n" "$TITLE" "$LIVE" "$END" >"$LIST"

echo "=== Concatenating video track (title + live multi-tab + end) ==="
ffmpeg -y -f concat -safe 0 -i "$LIST" \
  -map 0:v:0 -an \
  -c:v libx264 -preset medium -crf 24 -pix_fmt yuv420p -r 30 \
  "$TEMP_VIDEO"

if [[ -f "$AUDIO" ]]; then
  echo "=== Multiplexing audio narration with 5.0s title offset ==="
  # Add 5s delay to the audio so it starts right as the live walkthrough begins
  ffmpeg -y -i "$TEMP_VIDEO" -i "$AUDIO" \
    -filter_complex "[1:a]adelay=5000|5000,apad[a]" \
    -map 0:v:0 -map "[a]" \
    -c:v copy \
    -c:a aac -b:a 128k \
    -shortest \
    -movflags +faststart \
    "$FINAL"
else
  echo "=== No audio file found, finalizing video-only ==="
  ffmpeg -y -i "$TEMP_VIDEO" -c:v copy -movflags +faststart "$FINAL"
fi

rm -f "$LIST" "$TEMP_VIDEO"
ls -lh "$FINAL"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL"
echo "wrote $FINAL"
