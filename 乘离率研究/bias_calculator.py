"""
乘离率（均线偏离度）计算模块
=====================================
基于广发策略刘晨明《如何区分主线是调整还是终结？》

【公式说明】
  Step 1: ln_close = ln(收盘价)
  Step 2: EMA20 = EMA(ln_close, span=20)
            alpha = 2 / (20 + 1) ≈ 0.0952，adjust=False
            与通达信 EMA 公式完全一致
  Step 3:
    减法版（推荐，适合 ETF / 宽基 / 行业指数）：
        bias(%) = (ln_close − EMA20) × 100
    除法版（广发原版，适合绝对价位较高的行业指数）：
        bias(%) = (ln_close / EMA20 − 1) × 100

【信号阈值】
  版本      过热      良性入场区     偏弱区      坚守区         止损
  减法版    >+15%    +5% ~ +15%   0% ~ +5%   −5% ~ 0%    < −5%
  除法版    >+2%     +0.6% ~ +1.8%  0% ~ +0.6%  −0.6% ~ 0%  < −0.6%

【趋势强度】（独立于乘离率阈值）
  近 20 个交易日中，收盘价在 EMA20 上方的天数：
    ≥ 10 天 → 上涨趋势有效
    < 10 天 → 趋势转弱（即使乘离率为正，也要警惕）
"""

from typing import Literal

import numpy as np
import pandas as pd

Version = Literal["subtract", "divide"]


# ─── 阈值常量 ─────────────────────────────────────────────────────────────────

THRESHOLDS: dict[str, dict] = {
    "subtract": {
        "overheat":  15.0,   # 过热上限
        "entry_hi":  15.0,   # 良性区上限（=过热下限）
        "entry_lo":   5.0,   # 良性区下限
        "zero":       0.0,
        "hold":      -5.0,   # 坚守区下限（=止损线）
    },
    "divide": {
        "overheat":   2.0,
        "entry_hi":   1.8,
        "entry_lo":   0.6,
        "zero":       0.0,
        "hold":      -0.6,
    },
}

TREND_MIN_DAYS_ABOVE = 10   # 近20日至少需在均线上方的天数
EMA_SPAN = 20               # 均线窗口


# ─── EMA 计算 ─────────────────────────────────────────────────────────────────

def calc_ema(series: pd.Series, span: int = EMA_SPAN) -> pd.Series:
    """
    与通达信一致的 EMA：EMA(t) = alpha × price(t) + (1−alpha) × EMA(t−1)
    alpha = 2 / (span + 1)，adjust=False
    """
    return series.ewm(span=span, adjust=False).mean()


# ─── 信号分类 ─────────────────────────────────────────────────────────────────

def classify_signal(bias: float, version: Version) -> str:
    """根据乘离率值返回信号文字（不含趋势判断）"""
    if pd.isna(bias):
        return "数据不足"
    th = THRESHOLDS[version]
    if bias > th["overheat"]:
        return "过热"
    if th["entry_lo"] <= bias <= th["entry_hi"]:
        return "良性"
    if th["zero"] < bias < th["entry_lo"]:
        return "偏弱"
    if th["hold"] <= bias <= th["zero"]:
        return "坚守"
    # bias < hold
    return "止损"


def classify_trend(days_above_20: float) -> str:
    """
    近20日均线上方天数 → 趋势强度
      ≥ 10 天：上涨趋势
      <  10 天：趋势转弱
    """
    if pd.isna(days_above_20):
        return "数据不足"
    return "上涨趋势" if days_above_20 >= TREND_MIN_DAYS_ABOVE else "趋势转弱"


def combined_signal(bias: float, days_above_20: float, version: Version) -> str:
    """
    综合信号：乘离率信号 × 趋势强度
    趋势转弱时，即使乘离率处于良性区也标注警告。
    """
    sig   = classify_signal(bias, version)
    trend = classify_trend(days_above_20)

    emoji_map = {
        "过热": "🔴",
        "良性": "🟢",
        "偏弱": "🟡",
        "坚守": "🟠",
        "止损": "🔴",
        "数据不足": "⚫",
    }
    trend_emoji = "✅" if trend == "上涨趋势" else "⚠️"

    # 趋势转弱时在信号后附加警告
    warn = f"  {trend_emoji}趋势转弱" if trend == "趋势转弱" else ""
    return f"{emoji_map.get(sig, '—')} {sig}{warn}"


# ─── 单标的乘离率序列计算 ──────────────────────────────────────────────────────

def calc_bias(
    close: pd.Series,
    version: Version = "subtract",
    span: int = EMA_SPAN,
) -> pd.DataFrame:
    """
    计算单只标的的完整乘离率历史序列。

    Parameters
    ----------
    close   : 收盘价 Series，index 为日期（DatetimeIndex），按时间正序
    version : "subtract"（减法版）| "divide"（除法版）
    span    : EMA 窗口，默认 20

    Returns
    -------
    DataFrame，列：
        close          原始收盘价
        ln_close       对数收盘价
        ema20          ln_close 的 EMA(20)
        bias           乘离率（%）
        above_ema      bool，收盘价是否在 EMA 上方（bias > 0）
        days_above_20  近20日中 above_ema 为 True 的天数
        trend          "上涨趋势" / "趋势转弱" / "数据不足"
        signal_raw     仅乘离率的信号文字（不含趋势）
        signal         综合信号（含趋势警告）
    """
    df = pd.DataFrame({"close": close})
    df["ln_close"] = np.log(df["close"])
    df["ema20"]    = calc_ema(df["ln_close"], span=span)

    if version == "subtract":
        df["bias"] = (df["ln_close"] - df["ema20"]) * 100
    else:
        df["bias"] = (df["ln_close"] / df["ema20"] - 1) * 100

    df["above_ema"] = df["bias"] > 0

    # ── 趋势强度：近 span 日中有多少天在均线上方 ──────────────────────────────
    # min_periods=span 确保前期不足时填 NaN，不产生误判
    df["days_above_20"] = (
        df["above_ema"]
        .rolling(window=span, min_periods=span)
        .sum()
    )

    df["trend"]      = df["days_above_20"].apply(classify_trend)
    df["signal_raw"] = df["bias"].apply(lambda b: classify_signal(b, version))
    df["signal"]     = df.apply(
        lambda r: combined_signal(r["bias"], r["days_above_20"], version), axis=1
    )

    return df


# ─── 批量计算（多指数快照）───────────────────────────────────────────────────

def calc_bias_batch(
    price_df: pd.DataFrame,
    index_col: str = "code",
    date_col:  str = "date",
    close_col: str = "close",
    version:   Version = "subtract",
    span:      int = EMA_SPAN,
    recent_n:  int = 5,
) -> pd.DataFrame:
    """
    批量计算多个指数的最新乘离率快照。

    Parameters
    ----------
    price_df  : 行情 DataFrame，含 date / code / close 列
    version   : 公式版本
    span      : EMA 窗口
    recent_n  : 结果中附带近 N 日乘离率走势

    Returns
    -------
    summary DataFrame，每行一个指数的最新状态
    """
    price_df = price_df.copy()
    price_df[date_col] = pd.to_datetime(price_df[date_col])
    price_df = price_df.sort_values([index_col, date_col])

    records = []
    for code, grp in price_df.groupby(index_col):
        series = grp.set_index(date_col)[close_col].dropna()

        if len(series) < span:
            records.append({
                "code":  code,
                "error": f"数据不足（{len(series)} 条，需 ≥ {span}）",
            })
            continue

        hist = calc_bias(series, version=version, span=span)
        last = hist.iloc[-1]

        bias_col_name = f"bias_{version}(%)"
        recent_biases = hist["bias"].iloc[-recent_n:].round(2).tolist()

        records.append({
            "code":              code,
            "latest_date":       hist.index[-1].strftime("%Y-%m-%d"),
            "close":             round(float(last["close"]), 4),
            bias_col_name:       round(float(last["bias"]), 2),
            "signal":            last["signal"],
            "trend":             last["trend"],
            "days_above_ema20":  (
                int(last["days_above_20"])
                if not pd.isna(last["days_above_20"]) else None
            ),
            f"recent_{recent_n}d_bias": recent_biases,
        })

    return pd.DataFrame(records)


# ─── 历史序列（供画图/详细分析）──────────────────────────────────────────────

def calc_bias_history(
    price_df:  pd.DataFrame,
    code:      str,
    index_col: str = "code",
    date_col:  str = "date",
    close_col: str = "close",
    version:   Version = "subtract",
    span:      int = EMA_SPAN,
) -> pd.DataFrame:
    """返回单个指数的完整乘离率历史序列"""
    series = (
        price_df[price_df[index_col] == code]
        .set_index(date_col)[close_col]
        .sort_index()
        .dropna()
    )
    return calc_bias(series, version=version, span=span)


# ─── 自测 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    np.random.seed(42)
    dates  = pd.date_range("2024-01-01", periods=80, freq="B")
    prices = 100 * np.exp(np.cumsum(
        np.concatenate([
            np.random.normal(0.005, 0.008, 40),   # 上涨段
            np.random.normal(-0.003, 0.008, 40),   # 回调段
        ])
    ))
    close = pd.Series(prices, index=dates)

    print("=" * 60)
    print("减法版 — 最近 10 行")
    print("=" * 60)
    df = calc_bias(close, version="subtract")
    cols = ["close", "bias", "days_above_20", "trend", "signal"]
    print(df[cols].tail(10).to_string())

    print("\n" + "=" * 60)
    print("除法版 — 最近 5 行")
    print("=" * 60)
    df2 = calc_bias(close, version="divide")
    print(df2[cols].tail(5).to_string())

    # 校验趋势转弱判断：回调段 days_above_20 应 < 10
    last_10 = df["days_above_20"].iloc[-10:]
    weak_count = (last_10 < TREND_MIN_DAYS_ABOVE).sum()
    assert weak_count > 0, "回调段应触发趋势转弱"
    print(f"\n✅ 趋势转弱判断正常（最后10行中 {weak_count} 行触发）")
    print("✅ 所有自测通过")
