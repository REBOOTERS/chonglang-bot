#!/usr/bin/env bash
# 启动全屏录制（覆盖 ZCode 窗口内的浏览器 IAB + 命令行输出，两者同框）
# 用法: ./rec-start.sh <case-id> [avfoundation屏幕索引，默认1]
#   屏幕索引查看: ffmpeg -hide_banner -f avfoundation -list_devices true -i ""
# 停止: ./rec-stop.sh（SIGINT 优雅收尾，保证 mp4 头完整）
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CASE_ID="${1:?用法: rec-start.sh <case-id> [屏幕索引]}"
SCREEN="${2:-1}"
PIDFILE="$DIR/.rec.pid"
OUTFILE="$DIR/$(date +%Y%m%d_%H%M%S)_${CASE_ID}.mp4"

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "已有录制进行中 (pid $(cat "$PIDFILE"))，请先执行 rec-stop.sh" >&2
  exit 1
fi

# -nostdin 防止后台挂起；-t 3600 为 1 小时安全上限，防止忘停录满磁盘
ffmpeg -nostdin -hide_banner -loglevel error \
  -f avfoundation -framerate 24 -capture_cursor 1 -i "$SCREEN" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -t 3600 "$OUTFILE" >/dev/null 2>&1 &

echo $! > "$PIDFILE"
echo "$OUTFILE" > "$DIR/.rec.out"
echo "REC START pid=$(cat "$PIDFILE") screen=$SCREEN -> $OUTFILE"
