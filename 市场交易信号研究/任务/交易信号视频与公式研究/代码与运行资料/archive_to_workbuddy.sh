#!/bin/zsh
# archive_to_workbuddy.sh — 把 douyin_research 的新增文件按类型硬链接到 Workbuddy 分类库
#
# 规则（与 2026-11-18 归档一致，一级按类型、二级按项目）：
#   *.sh/*.py/*.swift/*.js/*.log/编译产物 → 01_代码/douyin_research/
#   *.md（根目录）                  → 02_说明文档/douyin_research/
#   *.csv / *.json / *.txt（数据）   → 03_数据源/douyin_research/
#   videos/ audio/                  → 04_视频/douyin_research/
#   transcripts/ *.zip              → 05_转写稿/douyin_research/
#   关键截图_*.jpg                  → 06_报告与图表/douyin_research/
#   frames/ sheets/ work_crops/ …   → 07_中间产物/douyin_research/
#
# 硬链接优先（同一份数据两个入口、不占额外空间）；跨卷或已存在时回退为复制/跳过。
# 幂等：可反复执行，已归档的文件不会被改动。
#
# 用法：
#   ./archive_to_workbuddy.sh            # 归档（增量）
#   ./archive_to_workbuddy.sh --dry-run  # 只统计待新增数量，不写入
set -uo pipefail

SRC="/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research"
LIB="/Users/yangguang/Documents/Workbuddy"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

[[ -d "$SRC" ]] || { echo "源目录不存在: $SRC"; exit 1; }
[[ -d "$LIB" ]] || { echo "归档库不存在: $LIB"; exit 1; }

NEW=0
LINKED=0
COPIED=0
RELINKED=0
# 归档前后按「库内实际文件数」快照统计，避免 rsync/ln 计数不准造成误导
TOTAL_BEFORE=$(find "$LIB"/*/douyin_research -type f 2>/dev/null | wc -l | tr -d ' ')

# 统计某源目录中「目标缺失」的文件数（dry-run 用）
count_missing() {
  local s="$1" d="$2" f rel n=0
  [[ -d "$s" ]] || { echo 0; return; }
  while IFS= read -r f; do
    rel="${f#$s/}"
    [[ -e "$d/$rel" ]] || n=$((n+1))
  done < <(find "$s" -type f ! -name '.DS_Store')
  echo "$n"
}

link_file() { # $1=源绝对路径 $2=目标目录
  local s="$1" d="$2" b
  b="$(basename "$s")"
  [[ -f "$s" ]] || return 0
  case "$b" in __probe*|.DS_Store) return 0 ;; esac
  if [[ -e "$d/$b" ]]; then
    # 已存在：硬链接是必须维护的不变量。只要 inode 不同（曾被原子重写或复制过）就重链
    if (( DRY == 0 )); then
      local si di
      si=$(stat -f '%i' "$s" 2>/dev/null)
      di=$(stat -f '%i' "$d/$b" 2>/dev/null)
      if [[ "$si" != "$di" ]]; then
        rm -f "$d/$b" && ln "$s" "$d/$b" 2>/dev/null && RELINKED=$((RELINKED+1))
      fi
    fi
    return 0
  fi
  if (( DRY == 1 )); then NEW=$((NEW+1)); return 0; fi
  mkdir -p "$d"
  if ln "$s" "$d/$b" 2>/dev/null; then LINKED=$((LINKED+1))
  elif cp -p "$s" "$d/$b" 2>/dev/null; then COPIED=$((COPIED+1)); fi
}

link_dir() { # $1=源子目录名 $2=目标目录
  local s="$SRC/$1" d="$2" before after
  [[ -d "$s" ]] || return 0
  if (( DRY == 1 )); then
    NEW=$(( NEW + $(count_missing "$s" "$d") ))
    return 0
  fi
  mkdir -p "$d"
  before=$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')
  # --link-dest 指向源树本身：内容必然相同 → 全部硬链接；--ignore-existing 保证幂等
  rsync -a --ignore-existing --link-dest="$s" "$s/" "$d/" 2>/dev/null \
    || cp -aln "$s/." "$d/" 2>/dev/null
  after=$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')
  LINKED=$(( LINKED + after - before ))
}

# ---- 目录类 ----
link_dir videos             "$LIB/04_视频/douyin_research/videos"
link_dir audio              "$LIB/04_视频/douyin_research/audio"
link_dir audio_new          "$LIB/07_中间产物/douyin_research/audio_new"
link_dir transcripts        "$LIB/05_转写稿/douyin_research/transcripts"
link_dir frames             "$LIB/07_中间产物/douyin_research/frames"
link_dir sheets             "$LIB/07_中间产物/douyin_research/sheets"
link_dir work_crops         "$LIB/07_中间产物/douyin_research/work_crops"
link_dir refine             "$LIB/07_中间产物/douyin_research/refine"
link_dir visual_scan        "$LIB/07_中间产物/douyin_research/visual_scan"
link_dir visual_transcripts "$LIB/07_中间产物/douyin_research/visual_transcripts"
link_dir times              "$LIB/07_中间产物/douyin_research/times"
link_dir batches            "$LIB/07_中间产物/douyin_research/batches"
link_dir cats               "$LIB/07_中间产物/douyin_research/cats"
link_dir drafts             "$LIB/07_中间产物/douyin_research/drafts"
link_dir frames_test        "$LIB/07_中间产物/douyin_research/frames_test"
link_dir frames_probe       "$LIB/07_中间产物/douyin_research/frames_probe"
link_dir frames_v2          "$LIB/07_中间产物/douyin_research/frames_v2"
link_dir frames_timing      "$LIB/07_中间产物/douyin_research/frames_timing"

# ---- 数据快照目录（按日期批次）----
for d in core_indicators_2026-11-16 data_source_audit_2026-11-17 formula_audit \
         full_validation_2026-11-17 ifind_batch_retry_2026-11-17 mcl_ifind_include_st_2026-11-17; do
  link_dir "$d" "$LIB/03_数据源/douyin_research/$d"
done
# 新增的日期批次目录（*_20xx-xx-xx）自动归入 03_数据源
for s in "$SRC"/*_20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]; do
  [[ -d "$s" ]] || continue
  link_dir "$(basename "$s")" "$LIB/03_数据源/douyin_research/$(basename "$s")"
done

# ---- 根目录文件类 ----
for f in "$SRC"/*.md; do
  [[ -e "$f" ]] || continue
  link_file "$f" "$LIB/02_说明文档/douyin_research"
done
for f in "$SRC"/*.csv "$SRC"/*.json "$SRC"/*.txt; do
  [[ -e "$f" ]] || continue
  link_file "$f" "$LIB/03_数据源/douyin_research"
done
for f in "$SRC"/*.sh "$SRC"/*.py "$SRC"/*.swift "$SRC"/*.js "$SRC"/*.log; do
  [[ -e "$f" ]] || continue
  link_file "$f" "$LIB/01_代码/douyin_research"
done
for f in "$SRC"/关键截图_*.jpg; do
  [[ -e "$f" ]] || continue
  link_file "$f" "$LIB/06_报告与图表/douyin_research"
done
for f in "$SRC"/*.zip; do
  [[ -e "$f" ]] || continue
  link_file "$f" "$LIB/05_转写稿/douyin_research"
done
# 编译产物（无扩展名的可执行文件）
for b in frame_extract frame_extract2 frame_extract3 make_sheet extract_audio; do
  link_file "$SRC/$b" "$LIB/01_代码/douyin_research"
done

# ---- 未映射目录检查（新增目录若未归入规则会被提示）----
for s in "$SRC"/*/; do
  name="$(basename "$s")"
  case "$name" in
    videos|audio|audio_new|transcripts|frames|sheets|work_crops|refine|visual_scan|visual_transcripts|times|batches|cats|drafts|frames_test|frames_probe|frames_v2|frames_timing) ;;
    core_indicators_2026-11-16|data_source_audit_2026-11-17|formula_audit|full_validation_2026-11-17|ifind_batch_retry_2026-11-17|mcl_ifind_include_st_2026-11-17) ;;
    *_20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
    *) echo "  ⚠ 未映射目录：$name（不会归档，请补进 link_dir 规则）" ;;
  esac
done

# ---- 汇总 ----
if (( DRY == 1 )); then
  echo "dry-run：待新增 $NEW 个文件（未写入）"
  exit 0
fi
TOTAL_AFTER=$(find "$LIB"/*/douyin_research -type f 2>/dev/null | wc -l | tr -d ' ')
echo "归档完成：本次新增 $(( TOTAL_AFTER - TOTAL_BEFORE )) 个文件，重链 $RELINKED 个（库内合计 $TOTAL_AFTER）"
for d in 01_代码 02_说明文档 03_数据源 04_视频 05_转写稿 06_报告与图表 07_中间产物; do
  n=$(find "$LIB/$d/douyin_research" -type f 2>/dev/null | wc -l | tr -d ' ')
  printf "  %-12s douyin_research: %s files\n" "$d" "$n"
done
