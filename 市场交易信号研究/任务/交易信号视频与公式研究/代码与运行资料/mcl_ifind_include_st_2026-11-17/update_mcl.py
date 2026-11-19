"""同口径 MCL 日终序列的导入、增量合并与重算；不负责联网采集。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

SOURCE = "ifind_A_share_advance_decline_report"
SCOPE = "SHSZ_A_INCLUDE_ST_VENDOR_BREADTH_EOD_V1"
INPUT_FIELDS = ["date", "A", "D", "U", "source_id", "scope_id"]
OUTPUT_FIELDS = INPUT_FIELDS + ["N", "net_advances", "ema19", "ema39", "mcl", "warmed"]


def checked_date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError(f"日期必须是 YYYY-MM-DD：{value!r}")
    return value


def checked_count(value):
    if isinstance(value, bool):
        raise ValueError("家数不能为布尔值")
    s = str(value)
    if not s.isascii() or not s.isdigit():
        raise ValueError(f"家数必须为非负整数：{value!r}")
    return int(s)


def validate_rows(rows):
    out, seen = [], set()
    for raw in rows:
        if set(INPUT_FIELDS) - raw.keys():
            raise ValueError("缺少必填字段")
        row = {k: raw[k] for k in INPUT_FIELDS}
        row["date"] = checked_date(row["date"])
        if row["date"] in seen:
            raise ValueError(f"输入存在重复日期：{row['date']}")
        seen.add(row["date"])
        if row["source_id"] != SOURCE or row["scope_id"] != SCOPE:
            raise ValueError("数据源或股票池不一致；含 ST 和剔 ST 序列不能拼接")
        for k in ("A", "D", "U"):
            row[k] = checked_count(row[k])
        if sum(row[k] for k in ("A", "D", "U")) == 0:
            raise ValueError("全市场家数为零，应核实是否缺数据或非交易日")
        out.append(row)
    return sorted(out, key=lambda x: x["date"])


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return validate_rows(list(csv.DictReader(handle)))


def read_calendar(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        values = [checked_date(row["date"]) for row in csv.DictReader(handle)]
    if len(values) != len(set(values)):
        raise ValueError("交易日历有重复日期")
    return sorted(values)


def merge_rows(existing, incoming, calendar, allow_correction=False):
    existing, incoming = validate_rows(existing), validate_rows(incoming)
    merged = {x["date"]: x for x in existing}
    for row in incoming:
        old = merged.get(row["date"])
        if old is not None and old != row and not allow_correction:
            raise ValueError(f"{row['date']} 与原数据冲突；须核验修订后显式允许更正")
        merged[row["date"]] = row
    rows = sorted(merged.values(), key=lambda x: x["date"])
    if not rows:
        raise ValueError("没有有效数据")
    actual = {x["date"] for x in rows}
    if actual - set(calendar):
        raise ValueError(f"包含交易日历以外的日期：{sorted(actual-set(calendar))}")
    expected = {d for d in calendar if rows[0]["date"] <= d <= rows[-1]["date"]}
    if expected != actual:
        raise ValueError(f"历史交易日缺口：{sorted(expected-actual)}")
    return rows


def calculate(rows):
    rows = validate_rows(rows)
    result, fast, slow = [], None, None
    for i, row in enumerate(rows):
        net = row["A"] - row["D"]
        fast = net if fast is None else 0.1 * net + 0.9 * fast
        slow = net if slow is None else 0.05 * net + 0.95 * slow
        result.append({**row, "N": row["A"]+row["D"]+row["U"],
                       "net_advances": net, "ema19": fast, "ema39": slow,
                       "mcl": fast-slow, "warmed": i >= 200})
    return result


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def persist(directory, rows):
    directory = Path(directory)
    series = calculate(rows)
    if not series:
        raise ValueError("不能保存空序列")
    history_path = directory / "ifind_breadth_history.csv"
    write_csv(history_path, rows, INPUT_FIELDS)
    write_csv(directory / "mcl_daily.csv", series, OUTPUT_FIELDS)
    state = {
        "source_id": SOURCE, "scope_id": SCOPE, "formula": "EMA19(A-D)-EMA39(A-D)",
        "seed": "first net_advances", "warmup_transitions": 200,
        "seed_and_warmup_are_research_conventions": True,
        "first_date": series[0]["date"], "last_date": series[-1]["date"],
        "records": len(series), "last_ema19": series[-1]["ema19"],
        "last_ema39": series[-1]["ema39"], "last_mcl": series[-1]["mcl"],
        "history_sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
        "update_rule": "merge same-scope EOD rows, verify calendar, then recompute from unchanged seed",
        "midday_rule": "preview from previous EOD EMA state; never persist noon as another day",
    }
    (directory / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2)+"\n")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path, help="必须包含截至新观察日的完整 date 列")
    parser.add_argument("--store", type=Path, default=Path(__file__).parent)
    parser.add_argument("--allow-correction", action="store_true")
    args = parser.parse_args()
    path = args.store / "ifind_breadth_history.csv"
    old = read_rows(path) if path.exists() else []
    merged = merge_rows(old, read_rows(args.input), read_calendar(args.calendar), args.allow_correction)
    print(json.dumps(persist(args.store, merged), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
