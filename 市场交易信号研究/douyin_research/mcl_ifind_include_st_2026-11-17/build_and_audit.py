"""复核已经缓存的 iFinD 沪深涨跌家数报表，并构建独立的含 ST MCL。"""
from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path

from update_mcl import SOURCE, SCOPE, merge_rows, persist, calculate, write_csv, INPUT_FIELDS

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
FULL = RESEARCH / "full_validation_2026-11-17"
PRIOR = RESEARCH / "ifind_batch_retry_2026-11-17"


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    source = FULL / "downloads/ifind_history_counts_probe_0.csv"
    raw = read(source)
    index_path = PRIOR / "normalized/上证指数_日线及VW_MACD.csv"
    index = read(index_path)
    close = {r["date"]: Decimal(r["close_points"]) for r in index}
    counts = []
    for row in raw:
        for label in ("上涨", "下跌", "平盘"):
            n = int(row["沪深两市_"+label])
            assert n >= 0
            assert n == int(row["沪市_"+label])+int(row["深市_"+label])
        assert Decimal(row["沪市_收盘点位"]) == close[row["日期"]]
        counts.append({"date": row["日期"], "A": row["沪深两市_上涨"],
                       "D": row["沪深两市_下跌"], "U": row["沪深两市_平盘"],
                       "source_id": SOURCE, "scope_id": SCOPE})
    counts = merge_rows([], counts, sorted(close))
    assert {x["date"] for x in counts} == set(close)
    series = calculate(counts)

    # 与独立 Decimal 递推交叉核验；另比较首值与零值两种初始化的影响。
    decimal_errors, seed_differences = [], []
    with localcontext() as ctx:
        ctx.prec = 40
        fast = slow = None
        zero_fast = zero_slow = Decimal(0)
        for row, calculated in zip(counts, series):
            net = Decimal(row["A"]-row["D"])
            fast = net if fast is None else Decimal("0.1")*net+Decimal("0.9")*fast
            slow = net if slow is None else Decimal("0.05")*net+Decimal("0.95")*slow
            zero_fast = Decimal("0.1")*net+Decimal("0.9")*zero_fast
            zero_slow = Decimal("0.05")*net+Decimal("0.95")*zero_slow
            decimal_errors.append(abs(float(fast-slow)-calculated["mcl"]))
            seed_differences.append(float((fast-slow)-(zero_fast-zero_slow)))
    assert max(decimal_errors) < 1e-9

    # 日终剔 ST 快照加有有效成交额的 ST 行，应与报表逐项相等。
    nonst_path = PRIOR / "normalized/全市场日终_2026-11-16.csv"
    st_path = FULL / "downloads/ifind_st_history_20261116_0.csv"
    nonst, st = read(nonst_path), read(st_path)
    def tally(rows, ret, amount):
        usable = [x for x in rows if x[amount] and Decimal(x[amount]) > 0]
        return {"A": sum(Decimal(x[ret]) > 0 for x in usable),
                "D": sum(Decimal(x[ret]) < 0 for x in usable),
                "U": sum(Decimal(x[ret]) == 0 for x in usable), "N": len(usable)}
    f = tally(nonst, "return_pct", "amount_yuan")
    s = tally(st, "涨跌幅:不复权[20261116]", "成交额[20261116]")
    assert not ({x["code"] for x in nonst} & {x["股票代码"] for x in st})
    assert all(f[k]+s[k] == counts[-1][k] for k in ("A", "D", "U"))
    missing_st = [{"code": x["股票代码"], "name": x["股票简称"]}
                  for x in st if not x["成交额[20261116]"]]
    # 不将空成交额直接解释为停牌；这些股票不用于逐股勾稽。
    state = persist(HERE, counts)
    audit = {
        "status": "accepted_for_ifind_vendor_SHSZ_including_ST_variant",
        "assumption_from_user": "本轮不考虑ST解释为MCL包含ST；其他指标剔ST规则不变",
        "source_report": "内地专题统计_二级市场_市场表现_A股涨跌家数统计",
        "source_report_path": "/专题统计/内地专题统计/二级市场/市场表现/A股涨跌家数统计",
        "source_parameters": {"开始日期": "20250901", "截止日期": "20261116", "统计范围": "A股"},
        "checks": {"records": len(counts), "unique_dates": len({x['date'] for x in counts}),
                   "negative_counts": 0, "sh_plus_sz_equals_total_every_day": True,
                   "dates_equal_cached_Shanghai_index_dates": True,
                   "report_index_close_equals_cached_index_close_every_day": True,
                   "max_mcl_error_against_decimal": max(decimal_errors),
                   "last_day_nonst_plus_trading_st_equals_report": True},
        "latest_reconciliation": {"date": counts[-1]["date"], "nonst": f, "st_with_amount": s,
                                  "report": {k: counts[-1][k] for k in ("A", "D", "U")},
                                  "st_rows_with_missing_amount_not_assumed_zero": missing_st},
        "initialization": {"seed": "first net advances", "warmup_transitions": 200,
                           "warmed_rows": sum(x["warmed"] for x in series),
                           "first_warmed_date": next(x["date"] for x in series if x["warmed"]),
                           "seed_first_minus_zero_mcl_at_last_date": seed_differences[-1],
                           "note": "种子及200次预热为工程约定；两种种子对比不等同于证明原博主起点"},
        "latest": series[-1], "recent_five": series[-5:],
        "limitations": [
            "采用iFinD报表的沪深A股涨跌方向口径；未逐股重建291天的历史上市及交易状态。",
            "最新日的逐股勾稽通过不等于每个历史日都独立验证了停牌、零成交及除权参考价。",
            "不与原先剔ST的Wind样本拼接，不宣称复制博主历史屏幕的全部数值。",
            "本文件仅截至2026-11-16，未取得2026-11-17收盘值。",
        ],
        "files": [{"path": str(p.relative_to(RESEARCH)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in (source, FULL/"raw/ifind_history_counts_probe.json", index_path, nonst_path, st_path)],
    }
    (HERE/"validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n")
    write_csv(HERE/"templates/mcl_daily_append.csv", [], INPUT_FIELDS)
    print(json.dumps({"state": state, "checks": audit["checks"], "initialization": audit["initialization"],
                      "reconciliation": audit["latest_reconciliation"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
