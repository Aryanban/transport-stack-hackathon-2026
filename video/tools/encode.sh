#!/usr/bin/env bash
# encode.sh <master.mp4> <out.mp4> - web copy under 10 MB: two-pass H.264 sized to the duration, AAC 96k, voice at -16 LUFS.
set -euo pipefail
IN="$1"; OUT="$2"; LIMIT_BYTES=${LIMIT_BYTES:-9600000}
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
AUDIO_K=96
VIDEO_K=$(python3 -c "print(int($LIMIT_BYTES*8/1000/$DUR*0.96 - $AUDIO_K))")
echo "duration ${DUR}s -> video ${VIDEO_K}k + audio ${AUDIO_K}k"
TMP=$(mktemp -d)
ffmpeg -loglevel error -y -i "$IN" -c:v libx264 -preset slow -b:v ${VIDEO_K}k -pass 1 -passlogfile "$TMP/p" -pix_fmt yuv420p -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$IN" -c:v libx264 -preset slow -b:v ${VIDEO_K}k -maxrate $((VIDEO_K*2))k -bufsize $((VIDEO_K*4))k -pass 2 -passlogfile "$TMP/p" -pix_fmt yuv420p \
  -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a ${AUDIO_K}k -ar 48000 -movflags +faststart "$OUT"
rm -rf "$TMP"
ls -l "$OUT" | awk '{print $5, "bytes"}'
