# -*- coding: utf-8 -*-
"""
批量入口 —— 输入一个指数代码列表，输出每个指数的温度。

用法:
    python batch_run.py 000998.CSI 399006.SZ 000300.SH
    python batch_run.py --file codes.txt            # 每行一个代码
    python batch_run.py 000998.CSI --history          # 同时导出每日温度历史

输出:
    指数温度_汇总.xlsx
        - sheet「最新温度」: 每个指数最新一日的温度 + 各分项分位数
        - sheet「<code>」  : 加 --history 时，每个指数的完整每日温度时间序列
"""
import sys
import argparse
import pandas as pd

from config import WEIGHTS, WIN, DATA_BEGIN
from compute import compute_temperature
import ifind_data


def run(codes, begin=DATA_BEGIN, end=None, history=False, user=None, pwd=None):
    ifind_data.login(user, pwd)
    market = ifind_data.fetch_market(begin, end)   # 全市场只取一次，所有指数复用

    latest_rows, hist = [], {}
    for code in codes:
        try:
            data = ifind_data.fetch_index(code, begin, end, market_series=market)
            df = compute_temperature(data, WEIGHTS, WIN)
            top = df.iloc[0].to_dict()
            top = {"指数代码": code, **top}
            latest_rows.append(top)
            if history:
                hist[code] = df
            print(f"[OK] {code}  {df.iloc[0]['日期'].date()}  温度={df.iloc[0]['温度']:.4f}")
        except Exception as e:
            print(f"[FAIL] {code}: {e}")
            latest_rows.append({"指数代码": code, "温度": None, "错误": str(e)})

    latest = pd.DataFrame(latest_rows)
    # 把日期、温度提到前面
    cols = ["指数代码", "日期", "温度"] + [c for c in latest.columns
                                       if c not in ("指数代码", "日期", "温度")]
    latest = latest[[c for c in cols if c in latest.columns]]

    out_path = "指数温度_汇总.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        latest.to_excel(w, sheet_name="最新温度", index=False)
        for code, df in hist.items():
            df.to_excel(w, sheet_name=code[:31], index=False)
    print(f"\n已输出 → {out_path}")
    return latest


def _parse_args(argv):
    p = argparse.ArgumentParser(description="行业/指数温度计 批量计算")
    p.add_argument("codes", nargs="*", help="指数代码, 如 000998.CSI 399006.SZ")
    p.add_argument("--file", help="代码清单文件, 每行一个")
    p.add_argument("--begin", default=DATA_BEGIN, help="取数起始日 (默认 %(default)s)")
    p.add_argument("--end", default=None, help="截止日 (默认今天)")
    p.add_argument("--history", action="store_true", help="同时导出每日温度历史")
    p.add_argument("--user", default=None, help="iFinD 账号 (或用环境变量 IFIND_USER)")
    p.add_argument("--pwd", default=None, help="iFinD 密码 (或用环境变量 IFIND_PWD)")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    codes = list(args.codes)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            codes += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not codes:
        print("请提供至少一个指数代码，或用 --file 指定清单。")
        sys.exit(1)
    run(codes, begin=args.begin, end=args.end, history=args.history,
        user=args.user, pwd=args.pwd)
