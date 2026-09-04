#!/usr/bin/env bash
# Record multi-tab walkthrough driven by Playwright with ffmpeg x11grab.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/apps/demo"
OUT="$DEMO/out/live-walkthrough.mp4"
SCRIPT="$ROOT/scripts/run-walkthrough.py"
PYTHON="$ROOT/services/loop/.venv/bin/python3"
DISPLAY="${DISPLAY:-:1}"
W=1920
H=1080
FPS=30

mkdir -p "$DEMO/out"

echo "=== Starting ffmpeg screen capture on ${DISPLAY} (${W}x${H} @ ${FPS}fps) ==="
ffmpeg -y \
  -f x11grab -draw_mouse 1 -framerate "$FPS" -video_size "${W}x${H}" -i "${DISPLAY}.0" \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=0xf5f5f7" \
  -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -r "$FPS" \
  "$OUT" &
FFMPEG_PID=$!

sleep 2

echo "=== Starting Playwright walkthrough runner ==="
"$PYTHON" "$SCRIPT"

echo "=== Playwright runner finished. Waiting 3s then stopping ffmpeg ==="
sleep 3
kill -INT "$FFMPEG_PID" 2>/dev/null || kill -TERM "$FFMPEG_PID" 2>/dev/null || true
wait "$FFMPEG_PID" 2>/dev/null || true

echo "=== Screen recording complete ==="
ls -lh "$OUT"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT"
