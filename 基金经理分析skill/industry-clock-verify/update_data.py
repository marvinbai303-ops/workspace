#!/usr/bin/env python3
"""
update_data.py — industry-clock-verify 数据更新工具

用法：
    python update_data.py --file <csv相对路径> --data '<JSON数组>'
    python update_data.py --file <csv相对路径> --data '<JSON数组>' --aggregate weekly
    python update_data.py --check                    # 检查所有文件是否需要更新
    python update_data.py --report                   # 打印数据覆盖范围报告

参数说明：
    --file       目标CSV文件路径，相对于本脚本所在目录（data/ 下）
    --data       iFinD EDB返回的原始数据，JSON数组格式：[["YYYY-MM-DD", value], ...]
    --aggregate  可选，"weekly" 表示将日频数据聚合为ISO周频（取周内均值，最后一个交易日为日期）
    --check      扫描所有CSV文件，输出需要更新的指标清单
    --report     打印所有数据文件的覆盖范围

调用示例（Claude执行，在 industry-clock-verify/ 目录下）：

1. 月度数据追加（如台积电营收）：
   python update_data.py \\
     --file data/semiconductor/tsmc_revenue_monthly.csv \\
     --data '[["2026-04-30", 88500], ["2026-05-31", 91200]]'

2. 日频→周频聚合追加（如碳酸锂价格）：
   python update_data.py \\
     --file data/upstream_materials/lithium_carbonate_weekly.csv \\
     --data '[["2026-04-25", 73200], ["2026-04-28", 73100], ["2026-04-29", 73050]]' \\
     --aggregate weekly

3. 检查哪些文件需要更新：
   python update_data.py --check

4. 打印数据覆盖报告：
   python update_data.py --report
"""

import csv
import json
import sys
import os
import argparse
from datetime import datetime, timedelta

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 所有需要管理的数据文件（相对于SCRIPT_DIR）及其更新频率
MANAGED_FILES = {
    "data/semiconductor/tsmc_revenue_monthly.csv":            {"freq": "monthly",  "date_col": 0, "update_lag_days": 45},
    "data/semiconductor/dram_ddr4_8gb_monthly.csv":           {"freq": "monthly",  "date_col": 0, "update_lag_days": 45},
    "data/semiconductor/nand_tlc_512gb_weekly.csv":           {"freq": "weekly",   "date_col": 0, "update_lag_days": 10},
    "data/new_energy_vehicle/battery_installation_monthly.csv": {"freq": "monthly", "date_col": 0, "update_lag_days": 15},
    "data/photovoltaic/polysilicon_price_weekly.csv":         {"freq": "weekly",   "date_col": 0, "update_lag_days": 10},
    "data/upstream_materials/lithium_carbonate_weekly.csv":   {"freq": "weekly",   "date_col": 0, "update_lag_days": 5},
    "data/upstream_materials/praseodymium_neodymium_weekly.csv": {"freq": "weekly", "date_col": 0, "update_lag_days": 5},
    "data/upstream_materials/copper_lme_weekly.csv":          {"freq": "weekly",   "date_col": 0, "update_lag_days": 5},
}


def parse_date(s):
    """解析多种日期格式为 datetime 对象"""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s}")


def get_last_date(filepath):
    """读取CSV文件，返回最后一行的日期"""
    abs_path = os.path.join(SCRIPT_DIR, filepath)
    if not os.path.exists(abs_path):
        return None
    last_date = None
    with open(abs_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or not row[0].strip():
                continue
            try:
                d = parse_date(row[0])
                if last_date is None or d > last_date:
                    last_date = d
            except ValueError:
                continue
    return last_date


def get_header_and_source_col(filepath):
    """返回 (header行, source列索引 or None)"""
    abs_path = os.path.join(SCRIPT_DIR, filepath)
    with open(abs_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    source_col = None
    for i, col in enumerate(header):
        if "source" in col.lower():
            source_col = i
            break
    return header, source_col


def aggregate_to_weekly(raw_data):
    """
    将日频数据聚合为ISO周频。
    输入: [[date_str, value], ...]（任意顺序）
    输出: [[last_weekday_date_str, avg_value], ...]（按日期升序）
    规则: 同一ISO周内取均值，日期键取该周最后一个交易日。
    """
    from collections import defaultdict

    buckets = defaultdict(list)
    for row in raw_data:
        d = parse_date(row[0])
        iso = d.isocalendar()[:2]  # (year, week_number)
        buckets[iso].append((d, float(row[1])))

    weekly = []
    for iso_key in sorted(buckets.keys()):
        entries = buckets[iso_key]
        last_date = max(e[0] for e in entries)
        avg_val = sum(e[1] for e in entries) / len(entries)
        weekly.append([last_date.strftime("%Y-%m-%d"), round(avg_val, 4)])

    return weekly


def append_new_rows(filepath, new_data, aggregate=None, source_label=None):
    """
    将新数据追加到CSV文件（自动跳过已有日期）。

    filepath: 相对路径
    new_data: [[date_str, value], ...] 或 [[date_str, value, extra...], ...]
    aggregate: None 或 "weekly"
    source_label: 写入source列的标注文字（可为None，保留原列数量）
    """
    abs_path = os.path.join(SCRIPT_DIR, filepath)
    last_date = get_last_date(filepath)
    header, source_col = get_header_and_source_col(filepath)
    n_cols = len(header)

    if aggregate == "weekly":
        new_data = aggregate_to_weekly(new_data)

    added = 0
    skipped = 0

    with open(abs_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in new_data:
            d = parse_date(row[0])
            if last_date is not None and d <= last_date:
                skipped += 1
                continue

            # 构造写入行，填满列数
            out = [d.strftime("%Y-%m-%d")]
            out.append(row[1] if len(row) > 1 else "")

            # 填充其余列（yoy等）
            for i in range(2, n_cols):
                if len(row) > i:
                    out.append(row[i])
                elif header[i].lower() in ("source",):
                    out.append(source_label or "iFinD EDB")
                else:
                    out.append("")

            writer.writerow(out)
            added += 1
            last_date = d  # 更新基准，防止同批数据重复

    return added, skipped


def update_manifest_last_updated(industry_dir, new_date_str):
    """
    更新 _manifest.yaml 中对应的 last_updated 字段。
    简单文本替换，不依赖 pyyaml。
    """
    manifest_path = os.path.join(SCRIPT_DIR, industry_dir, "_manifest.yaml")
    if not os.path.exists(manifest_path):
        return False
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    # 替换 last_updated: "YYYY-MM" 为新日期（取年月）
    new_ym = new_date_str[:7]  # "YYYY-MM"
    content_new = re.sub(r'last_updated:\s*"[\d\-]+"', f'last_updated: "{new_ym}"', content)
    if content_new != content:
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(content_new)
        return True
    return False


def cmd_check():
    """检查所有托管文件是否需要更新"""
    today = datetime.today()
    print(f"数据更新状态检查 — {today.strftime('%Y-%m-%d')}\n")
    print(f"{'文件':<55} {'最新日期':<12} {'距今(天)':<10} {'状态'}")
    print("-" * 95)
    needs_update = []
    for rel_path, cfg in sorted(MANAGED_FILES.items()):
        abs_path = os.path.join(SCRIPT_DIR, rel_path)
        if not os.path.exists(abs_path):
            print(f"  {rel_path:<53} {'文件不存在':<12} {'—':<10} ⚠️  MISSING")
            needs_update.append(rel_path)
            continue
        last = get_last_date(rel_path)
        if last is None:
            print(f"  {rel_path:<53} {'空文件':<12} {'—':<10} ⚠️  EMPTY")
            needs_update.append(rel_path)
            continue
        gap = (today - last).days
        lag = cfg["update_lag_days"]
        # 月度：超过60天算过期；周度：超过14天算过期
        threshold = 60 if cfg["freq"] == "monthly" else 14
        status = "✅ OK" if gap <= threshold + lag else "⚠️  需更新"
        if gap > threshold + lag:
            needs_update.append(rel_path)
        print(f"  {rel_path:<53} {last.strftime('%Y-%m-%d'):<12} {gap:<10} {status}")

    print()
    if needs_update:
        print(f"共 {len(needs_update)} 个文件需要更新：")
        for p in needs_update:
            print(f"  - {p}")
        print("\n参考 data/<行业>/_manifest.yaml 中的 update.ifind_query 获取对应iFinD指标ID。")
    else:
        print("所有文件均为最新。")


def cmd_report():
    """打印数据覆盖范围报告"""
    print(f"{'文件':<55} {'行数':<6} {'起始':<12} {'截止':<12} {'频率'}")
    print("-" * 100)
    for rel_path, cfg in sorted(MANAGED_FILES.items()):
        abs_path = os.path.join(SCRIPT_DIR, rel_path)
        if not os.path.exists(abs_path):
            print(f"  {rel_path:<53} {'—':<6} {'不存在'}")
            continue
        dates = []
        rows = 0
        with open(abs_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if not row or not row[0].strip():
                    continue
                try:
                    dates.append(parse_date(row[0]))
                    rows += 1
                except ValueError:
                    continue
        if dates:
            first = min(dates).strftime("%Y-%m-%d")
            last = max(dates).strftime("%Y-%m-%d")
        else:
            first = last = "—"
        print(f"  {rel_path:<53} {rows:<6} {first:<12} {last:<12} {cfg['freq']}")


def main():
    parser = argparse.ArgumentParser(description="industry-clock-verify 数据更新工具")
    parser.add_argument("--file", help="目标CSV文件路径（相对于脚本目录）")
    parser.add_argument("--data", help="新数据JSON数组: [[date, value], ...]")
    parser.add_argument("--aggregate", choices=["weekly"], help="日频→周频聚合")
    parser.add_argument("--source", help="写入source列的标注", default=None)
    parser.add_argument("--check", action="store_true", help="检查所有文件更新状态")
    parser.add_argument("--report", action="store_true", help="打印数据覆盖报告")
    args = parser.parse_args()

    if args.check:
        cmd_check()
        return

    if args.report:
        cmd_report()
        return

    if not args.file or not args.data:
        parser.print_help()
        sys.exit(1)

    # 解析新数据
    try:
        new_data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: --data 不是合法JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(new_data, list) or not new_data:
        print("ERROR: --data 应为非空JSON数组", file=sys.stderr)
        sys.exit(1)

    # 执行追加
    added, skipped = append_new_rows(
        args.file,
        new_data,
        aggregate=args.aggregate,
        source_label=args.source,
    )
    print(f"✅ 追加完成: 新增 {added} 行，跳过已有 {skipped} 行 → {args.file}")

    # 更新 manifest last_updated
    industry_dir = os.path.dirname(args.file)
    last = get_last_date(args.file)
    if last and update_manifest_last_updated(industry_dir, last.strftime("%Y-%m-%d")):
        print(f"   manifest last_updated 已更新为 {last.strftime('%Y-%m')}")


if __name__ == "__main__":
    main()
