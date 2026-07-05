"""
乘离率分析主入口
================
数据来源：同花顺 iFind（通过 agent 调用 MCP 工具获取，再传入本脚本）

用法一：agent 将 iFind 响应存为文件后调用
─────────────────────────────────────────
  python run_bias.py \\
      --index_list   index_list.csv \\
      --ifind_dir    ./ifind_responses/ \\
      --version      subtract \\
      --output       bias_result.xlsx

  ifind_dir 目录结构（每个指数单独一个文件，文件名即代码）：
      000300.SH.txt
      000905.SH.txt
      399006.SZ.txt
      ...

用法二：从 CSV 行情文件读取（本地测试 / 用户自己提供数据时）
─────────────────────────────────────────────────────────────
  python run_bias.py \\
      --index_list  index_list.csv \\
      --price_data  price_data.csv \\
      --version     subtract \\
      --output      bias_result.xlsx

作为模块供 agent Python 代码调用：
─────────────────────────────────────────────────────────────
  from run_bias import run_analysis
  from ifind_fetcher import build_price_df

  # responses: {code: ifind_response_text}
  price_df = build_price_df(responses, min_days=60)
  summary, details = run_analysis(index_list_df, price_df, version="subtract")
  print(summary)
"""

import argparse
import os
import sys
from datetime import date

import pandas as pd

from bias_calculator import calc_bias_batch, calc_bias_history, Version, THRESHOLDS
from ifind_fetcher import build_price_df, parse_file, IFindDataError


# ─── 数据加载 ─────────────────────────────────────────────────────────────────

def load_index_list(path: str) -> pd.DataFrame:
    """
    读取指数列表 CSV（列：code, name）
    示例：
        code,name
        000300.SH,沪深300
        000905.SH,中证500
    """
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()
    if "code" not in df.columns:
        raise ValueError("index_list 文件缺少 'code' 列")
    df["code"] = df["code"].str.strip()
    return df


def load_price_csv(path: str) -> pd.DataFrame:
    """
    读取本地行情 CSV（列：date, code, close）
    date 格式：YYYY-MM-DD
    也支持宽表（第一列 date，其余列为指数代码），自动 melt 转换。
    """
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()

    if "date" in df.columns and "code" not in df.columns:
        df = df.melt(id_vars="date", var_name="code", value_name="close")

    required = {"date", "code", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"price_data 缺少列：{missing}")

    df["date"]  = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["code"]  = df["code"].str.strip()
    return df.dropna(subset=["close"])


def load_ifind_dir(ifind_dir: str, codes: list[str], min_days: int = 60) -> pd.DataFrame:
    """
    从目录读取 iFind 响应文件（每个文件名为指数代码，如 000300.SH.txt），
    逐个解析校验后合并为 price_df。

    任何一个文件缺失或校验失败 → 立即抛出异常，整体停止。
    """
    responses = {}
    for code in codes:
        fname = os.path.join(ifind_dir, f"{code}.txt")
        if not os.path.exists(fname):
            raise FileNotFoundError(
                f"[{code}] iFind 响应文件不存在：{fname}\n"
                "请确认 agent 已为该指数单独获取数据并保存到该路径。\n"
                "运算已停止。"
            )
        with open(fname, encoding="utf-8") as f:
            responses[code] = f.read()

    print(f"[数据] 从 iFind 响应文件加载，共 {len(responses)} 个指数")
    return build_price_df(responses, min_days=min_days)


# ─── 核心分析 ─────────────────────────────────────────────────────────────────

def run_analysis(
    index_list: pd.DataFrame,
    price_df:   pd.DataFrame,
    version:    Version = "subtract",
    span:       int = 20,
    recent_n:   int = 5,
) -> tuple[pd.DataFrame, dict]:
    """
    对 index_list 中所有指数计算乘离率。

    Returns
    -------
    summary : DataFrame，每行一个指数的最新快照
    details : dict，{code: 完整历史 DataFrame}
    """
    codes_in_list  = set(index_list["code"].tolist())
    codes_in_price = set(price_df["code"].unique())
    missing = codes_in_list - codes_in_price

    if missing:
        # 严格模式：有指数缺数据 → 停止
        raise ValueError(
            f"以下指数在行情数据中缺失，无法继续运算：{sorted(missing)}\n"
            "请为所有指数提供完整行情数据。"
        )

    summary = calc_bias_batch(
        price_df,
        version=version,
        span=span,
        recent_n=recent_n,
    )

    if "name" in index_list.columns:
        name_map = index_list.set_index("code")["name"].to_dict()
        summary.insert(1, "name", summary["code"].map(name_map).fillna(""))

    details = {}
    for code in codes_in_list:
        try:
            details[code] = calc_bias_history(
                price_df, code=code, version=version, span=span
            )
        except Exception as e:
            print(f"  [警告] {code} 历史序列计算失败：{e}", file=sys.stderr)

    return summary, details


# ─── 终端打印 ────────────────────────────────────────────────────────────────

def print_summary(summary: pd.DataFrame, version: Version):
    th = THRESHOLDS[version]
    bias_col   = f"bias_{version}(%)"
    recent_col = next((c for c in summary.columns if c.startswith("recent_")), None)

    print("\n" + "═" * 72)
    print(f"  乘离率分析结果  ·  公式：{version}版  ·  {date.today()}")
    print("═" * 72)

    for _, row in summary.iterrows():
        if "error" in row.index and pd.notna(row.get("error")):
            print(f"\n  ⚠️  [{row['code']}]  {row['error']}")
            continue

        name        = row.get("name", "")
        code        = row["code"]
        bias        = row.get(bias_col, float("nan"))
        signal      = row.get("signal", "—")
        trend       = row.get("trend", "—")
        days_above  = row.get("days_above_ema20")
        latest_date = row.get("latest_date", "—")
        recent      = row.get(recent_col, []) if recent_col else []

        trend_bar = _trend_bar(days_above)

        print(f"\n  {'─'*60}")
        print(f"  {name}（{code}）  最新日期: {latest_date}")
        print(f"  乘离率: {bias:+.2f}%   {signal}")
        print(f"  趋势: {trend_bar}  {trend}（近20日均线上方 {days_above}/20 天）")
        if recent:
            arrow = " → ".join(f"{v:+.2f}%" for v in recent)
            print(f"  近期走势: {arrow}")

    print("\n" + "═" * 72)
    print(_legend(version))
    print("═" * 72 + "\n")


def _trend_bar(days_above) -> str:
    """用格状字符可视化近20日均线上方天数"""
    if days_above is None:
        return "[数据不足]"
    n = int(days_above)
    bar = "█" * n + "░" * (20 - n)
    return f"[{bar}]"


def _legend(version: Version) -> str:
    th = THRESHOLDS[version]
    if version == "subtract":
        return (
            "信号说明（减法版）\n"
            f"  🟢 良性   偏离度 +{th['entry_lo']}% ~ +{th['entry_hi']}%  趋势健康，适合入场\n"
            f"  🔴 过热   偏离度 > +{th['overheat']}%              不追高，等回落\n"
            f"  🟡 偏弱   偏离度 0% ~ +{th['entry_lo']}%          距均线过近，趋势可能转弱\n"
            f"  🟠 坚守   偏离度 {th['hold']}% ~ 0%            刚跌穿均线，观察后续\n"
            f"  🔴 止损   偏离度 < {th['hold']}%               大幅跌穿均线，止损离场\n"
            f"  ⚠️  趋势转弱  近20日中均线上方天数 < 10 天，即使信号良性也需警惕"
        )
    else:
        return (
            "信号说明（除法版）\n"
            f"  🟢 良性   偏离度 +{th['entry_lo']}% ~ +{th['entry_hi']}%\n"
            f"  🔴 过热   偏离度 > +{th['overheat']}%\n"
            f"  🟡 偏弱   偏离度 0% ~ +{th['entry_lo']}%\n"
            f"  🟠 坚守   偏离度 {th['hold']}% ~ 0%\n"
            f"  🔴 止损   偏离度 < {th['hold']}%\n"
            f"  ⚠️  趋势转弱  近20日中均线上方天数 < 10 天"
        )


# ─── 输出保存 ────────────────────────────────────────────────────────────────

def save_output(
    summary: pd.DataFrame,
    details: dict,
    output_path: str,
):
    ext = os.path.splitext(output_path)[1].lower()

    if ext == ".csv":
        summary.to_csv(output_path, index=False, encoding="utf-8-sig")
    else:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            summary.to_excel(writer, sheet_name="最新乘离率", index=False)

            for code, df in details.items():
                sheet = code.replace(".", "_")[:31]
                out_cols = [
                    "close", "ln_close", "ema20", "bias",
                    "days_above_20", "trend", "signal_raw", "signal",
                ]
                export = df[[c for c in out_cols if c in df.columns]].copy()
                export.index.name = "date"
                export.to_excel(writer, sheet_name=sheet)

            for ws in writer.book.worksheets:
                for col in ws.columns:
                    w = max((len(str(cell.value or "")) for cell in col), default=8)
                    ws.column_dimensions[col[0].column_letter].width = min(w + 2, 45)

    print(f"[输出] 已保存：{output_path}（摘要 + {len(details)} 个指数历史 Sheet）")


# ─── 命令行入口 ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="乘离率批量计算（iFind 数据源）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--index_list", required=True,
                        help="指数列表 CSV（列：code, name）")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ifind_dir",
                        help="iFind 响应文件目录（每文件名为指数代码，如 000300.SH.txt）")
    source.add_argument("--price_data",
                        help="本地行情 CSV（列：date, code, close）；仅用于测试")

    parser.add_argument("--version", default="subtract",
                        choices=["subtract", "divide"],
                        help="公式版本：subtract（默认）| divide（广发原版）")
    parser.add_argument("--span",     type=int, default=20,  help="EMA 窗口，默认 20")
    parser.add_argument("--recent_n", type=int, default=5,   help="显示近 N 日历史，默认 5")
    parser.add_argument("--min_days", type=int, default=60,  help="每指数最少交易日数，默认 60")
    parser.add_argument("--output",   default="bias_result.xlsx",
                        help="输出路径（.xlsx 或 .csv），默认 bias_result.xlsx")
    args = parser.parse_args()

    # ── 加载指数列表 ──────────────────────────────────────────────────────────
    print(f"[加载] 指数列表：{args.index_list}")
    index_list = load_index_list(args.index_list)
    codes = index_list["code"].tolist()
    print(f"       共 {len(codes)} 个指数：{codes}")

    # ── 加载行情数据 ──────────────────────────────────────────────────────────
    try:
        if args.ifind_dir:
            price_df = load_ifind_dir(args.ifind_dir, codes, min_days=args.min_days)
        else:
            print(f"[加载] 本地行情：{args.price_data}")
            price_df = load_price_csv(args.price_data)
            dr = f"{price_df['date'].min().date()} ~ {price_df['date'].max().date()}"
            print(f"       数据范围：{dr}，共 {len(price_df)} 条")

    except IFindDataError as e:
        print(f"\n[错误] 数据校验失败，运算已停止：\n{e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n[错误] {e}", file=sys.stderr)
        sys.exit(1)

    # ── 计算 ──────────────────────────────────────────────────────────────────
    print(f"[计算] 公式版本：{args.version}，EMA 窗口：{args.span}")
    try:
        summary, details = run_analysis(
            index_list, price_df,
            version=args.version,
            span=args.span,
            recent_n=args.recent_n,
        )
    except ValueError as e:
        print(f"\n[错误] {e}", file=sys.stderr)
        sys.exit(1)

    print_summary(summary, version=args.version)
    save_output(summary, details, args.output)


if __name__ == "__main__":
    main()
