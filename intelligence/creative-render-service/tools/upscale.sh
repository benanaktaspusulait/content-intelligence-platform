#!/usr/bin/env bash
# Video çözünürlük yükseltme aracı.
# Usage: ./upscale.sh [-r WxH] [-c CRF] [-s] file.mp4 [...]
set -euo pipefail

TARGET="1920x1080"
CRF=18
SAFE=0

usage() {
  sed -n '1,14p' "$0"
  exit "${1:-0}"
}

while getopts ":r:c:sh" opt; do
  case "$opt" in
    r) TARGET="$OPTARG" ;;
    c) CRF="$OPTARG" ;;
    s) SAFE=1 ;;
    h) usage 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage 1 ;;
    :) echo "-$OPTARG requires a value" >&2; usage 1 ;;
  esac
done
shift $((OPTIND - 1))

command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg not found." >&2; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ERROR: ffprobe not found." >&2; exit 1; }

TW="${TARGET%x*}"
TH="${TARGET#*x}"
if ! [[ "$TW" =~ ^[0-9]+$ && "$TH" =~ ^[0-9]+$ ]]; then
  echo "ERROR: invalid resolution '$TARGET' (expected WxH)." >&2
  exit 1
fi

if [[ "$#" -eq 0 ]]; then
  echo "ERROR: no input video provided." >&2
  usage 1
fi

process() {
  local input="$1"
  [[ -f "$input" ]] || { echo "Skipped missing file: $input" >&2; return; }

  local dims width height
  dims="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
    -of csv=p=0 "$input" 2>/dev/null || true)"
  width="${dims%,*}"
  height="${dims#*,}"
  if [[ -z "$width" || -z "$height" ]]; then
    echo "ERROR: video stream could not be read: $input" >&2
    return 1
  fi

  if [[ "$width" -ge "$TW" && "$height" -ge "$TH" ]]; then
    echo "Already at least ${TW}x${TH}; leaving unchanged: $(basename "$input")"
    return 0
  fi

  local directory base temporary
  directory="$(dirname "$input")"
  base="$(basename "${input%.*}")"
  temporary="${directory}/${base}_hd.mp4"

  echo "Upscaling ${width}x${height} -> ${TW}x${TH}: $(basename "$input")"
  ffmpeg -y -loglevel error -i "$input" \
    -vf "scale=${TW}:${TH}:force_original_aspect_ratio=increase:flags=lanczos,crop=${TW}:${TH}" \
    -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p \
    -c:a aac -b:a 130k \
    "$temporary"

  if [[ "$SAFE" -eq 1 ]]; then
    echo "Created: $(basename "$temporary")"
  else
    mv -f "$temporary" "$input"
    echo "Updated: $(basename "$input")"
  fi
}

for input in "$@"; do
  process "$input"
done
