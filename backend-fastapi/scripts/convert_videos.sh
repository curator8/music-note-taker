#!/usr/bin/env bash
set -euo pipefail

VIDEO_DIR="${1:-video}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is not installed. Install it first, for example: sudo apt install ffmpeg"
  exit 1
fi

if [ ! -d "$VIDEO_DIR" ]; then
  echo "Video directory not found: $VIDEO_DIR"
  exit 1
fi

found=0

for input in "$VIDEO_DIR"/*.MOV "$VIDEO_DIR"/*.mov; do
  [ -e "$input" ] || continue
  found=1

  output="${input%.*}.mp4"

  if [ -e "$output" ]; then
    echo "Skipping existing file: $output"
    continue
  fi

  echo "Converting $input -> $output"
  ffmpeg -i "$input" \
    -c:v libx264 \
    -c:a aac \
    -movflags +faststart \
    "$output"
done

if [ "$found" -eq 0 ]; then
  echo "No .MOV or .mov files found in $VIDEO_DIR"
fi
