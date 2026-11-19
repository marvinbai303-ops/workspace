#!/bin/zsh
# sync_to_codex.sh — 把 douyin_research 的增量内容同步到 Codex 工作区
#
# 约定：本对话每次新增视频 / 逐字稿 / 报告 / 截图 / 抽帧 / 拼图后立即执行一次。
# 用法：
#   ./sync_to_codex.sh              # 常规同步（排除 work_crops 与调试目录）
#   ./sync_to_codex.sh --with-crops # 连 work_crops 一起同步
#   ./sync_to_codex.sh --dry-run    # 只预览，不写入
set -uo pipefail

SRC="/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research"
DST="/Users/yangguang/Documents/Codex/workspace/市场交易信号研究/douyin_research"

EXCLUDES=(
  --exclude='.DS_Store'
  --exclude='frames_test/'
  --exclude='frames_probe/'
  --exclude='frames_v2/'
  --exclude='frames_timing/'
)
WITH_CROPS=0
DRY=0
for a in "$@"; do
  case "$a" in
    --with-crops) WITH_CROPS=1 ;;
    --dry-run) DRY=1 ;;
  esac
done
(( WITH_CROPS == 0 )) && EXCLUDES+=(--exclude='work_crops/')
(( DRY == 1 )) && EXCLUDES+=(--dry-run --itemize-changes)

[[ -d "$SRC" ]] || { echo "源目录不存在: $SRC"; exit 1; }
mkdir -p "$DST"

STATS=$(rsync -a "${EXCLUDES[@]}" --stats "$SRC/" "$DST/" 2>&1)
RC=$?

if (( DRY == 1 )); then
  echo "$STATS" | sed -n '1,40p'
  echo "（dry-run，未写入）"
  exit 0
fi

FILES=$(echo "$STATS" | awk -F': *' '/Number of .*files transferred/{print $2; exit}')
BYTES=$(echo "$STATS" | awk -F': *' '/Total transferred file size/{print $2; exit}' | tr -d ' B,')
FILES=${FILES:-0}
BYTES=${BYTES:-0}

NV=$(ls "$DST"/videos/*.mp4 2>/dev/null | wc -l | tr -d ' ')
NT=$(ls "$DST"/transcripts/*.md 2>/dev/null | wc -l | tr -d ' ')
NS=$(ls "$DST"/关键截图_*.jpg 2>/dev/null | wc -l | tr -d ' ')
NR=$(ls "$DST"/*.md 2>/dev/null | wc -l | tr -d ' ')
# 注意：macOS 上对含中文的绝对路径 du 可能返回 0B（Unicode 归一化问题），必须 cd 进去统计
SIZE=$( (cd "$DST" 2>/dev/null && du -sh . 2>/dev/null | cut -f1) )
SIZE=${SIZE:-?}
TS=$(date "+%Y-%m-%d %H:%M")

LOG="$DST/_同步日志.md"
if [[ ! -f "$LOG" ]]; then
  {
    echo "# 同步日志（WorkBuddy → Codex）"
    echo ""
    echo "| 时间 | 传输文件 | 传输体积 | 视频 | 逐字稿 | 关键截图 | 根目录文档 | 目标体积 |"
    echo "|---|---|---|---|---|---|---|---|"
  } > "$LOG"
fi
printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' \
  "$TS" "$FILES" "$BYTES" "$NV" "$NT" "$NS" "$NR" "$SIZE" >> "$LOG"

echo "同步完成（rsync rc=$RC）"
echo "  本次传输: $FILES 个文件 / $BYTES"
echo "  目标现状: 视频 $NV ｜ 逐字稿 $NT ｜ 关键截图 $NS ｜ 根目录文档 $NR ｜ 总体积 $SIZE"
echo "  日志已追加: $LOG"
if (( RC != 0 )); then
  echo "  注意: rsync 返回 $RC（23=部分文件权限/被占用，24=传输中文件消失），请检查上方输出"
fi
