#!/usr/bin/env bash
# Capture live browser walkthrough without Cursor branding (ffmpeg x11grab).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/apps/demo/out/live-walkthrough.mp4}"
DISPLAY="${DISPLAY:-:1}"
DUR="${DUR:-240}"
FPS="${FPS:-30}"
W="${W:-1920}"
H="${H:-1080}"

mkdir -p "$(dirname "$OUT")"

echo "Recording ${W}x${H} @ ${FPS}fps for ${DUR}s on ${DISPLAY} -> ${OUT}"
echo "Start browser walkthrough now."

ffmpeg -y \
  -f x11grab -draw_mouse 1 -framerate "$FPS" -video_size "${W}x${H}" -i "${DISPLAY}.0" \
  -t "$DUR" \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=0xf5f5f7" \
  -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -r "$FPS" \
  -movflags +faststart \
  "$OUT"

ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT"
ls -lh "$OUT"
echo "wrote $OUT"
