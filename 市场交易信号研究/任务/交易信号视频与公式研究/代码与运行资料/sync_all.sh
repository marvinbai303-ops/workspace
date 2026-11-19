#!/bin/zsh
# sync_all.sh — 一条命令完成「双目标」同步
#
#   ① Codex 工作区   → sync_to_codex.sh        （rsync 增量复制，供 Codex 读取）
#   ② Workbuddy 分类库 → archive_to_workbuddy.sh（按类型硬链接，不占额外空间）
#
# 触发场景：本对话每次新增视频 / 逐字稿 / 报告 / CSV / 关键截图 / 抽帧 / 拼图后，立即执行。
#
# 用法：
#   ./sync_all.sh             # 两个目标都同步
#   ./sync_all.sh --dry-run   # 只预览差异，不写入
#   ./sync_all.sh codex       # 只同步 Codex
#   ./sync_all.sh archive     # 只归档分类库
set -uo pipefail

cd "$(dirname "$0")" || exit 1
MODE="${1:-all}"

run_codex() {
  echo "──────── ① 同步到 Codex 工作区 ────────"
  if [[ "$MODE" == "--dry-run" ]]; then
    ./sync_to_codex.sh --dry-run
  else
    ./sync_to_codex.sh
  fi
}

run_archive() {
  echo "──────── ② 归档到 Workbuddy 分类库 ────────"
  if [[ "$MODE" == "--dry-run" ]]; then
    ./archive_to_workbuddy.sh --dry-run
  else
    ./archive_to_workbuddy.sh
  fi
}

case "$MODE" in
  codex)   run_codex ;;
  archive) run_archive ;;
  all|--dry-run) run_codex; echo; run_archive ;;
  *) echo "用法：./sync_all.sh [--dry-run|codex|archive]"; exit 1 ;;
esac
