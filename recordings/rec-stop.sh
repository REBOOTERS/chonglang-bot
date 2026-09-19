#!/usr/bin/env bash
# 停止 rec-start.sh 启动的录制，等待 ffmpeg 正常收尾（mp4 moov 原子落盘）
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/.rec.pid"

[[ -f "$PIDFILE" ]] || { echo "没有进行中的录制"; exit 0; }
PID="$(cat "$PIDFILE")"

kill -INT "$PID" 2>/dev/null || true
for _ in $(seq 1 30); do
  kill -0 "$PID" 2>/dev/null || break
  sleep 0.5
done
kill -9 "$PID" 2>/dev/null || true

OUT="$(cat "$DIR/.rec.out" 2>/dev/null || true)"
rm -f "$PIDFILE"
if [[ -n "$OUT" && -f "$OUT" ]]; then
  SIZE=$(du -h "$OUT" | cut -f1)
  echo "REC STOP -> $OUT ($SIZE)"
else
  echo "REC STOP（未找到输出文件）"
fi
