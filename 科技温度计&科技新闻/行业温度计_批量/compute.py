# -*- coding: utf-8 -*-
"""
计算引擎 —— 与 Excel 底稿公式一一对应。

约定：所有 series 都是【按日期降序】的 numpy 数组（index 0 = 最新交易日），
跟 Excel 底稿的行顺序一致（第3行=最新）。这样"滚动回看过去 W 天"就是 arr[i:i+W]。

核心：Excel 的 PERCENTRANK.INC 与 pandas 的分位排名不同，必须精确复刻，
否则温度对不上模板。本文件已用模板缓存值验证过（误差仅来自显示四舍五入）。
"""
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Excel PERCENTRANK.INC 精确复刻
# ---------------------------------------------------------------------------
def percentrank_inc(arr, x):
    """等价于 Excel 的 _xlfn.PERCENTRANK.INC(arr, x)。返回 0~1。"""
    a = np.sort(np.asarray([v for v in arr if v is not None and not np.isnan(v)], dtype=float))
    n = a.size
    if n == 0 or x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if n == 1:
        return 0.0
    if x <= a[0]:
        return 0.0
    if x >= a[-1]:
        return 1.0
    # 命中某个值 → (严格小于它的个数)/(n-1)，取首个相等位置
    idx = np.searchsorted(a, x, side="left")
    if a[idx] == x:
        return idx / (n - 1)
    # 落在 a[idx-1] 与 a[idx] 之间，线性插值
    lo = idx - 1
    frac = (x - a[lo]) / (a[idx] - a[lo])
    return (lo + frac) / (n - 1)


def roll_pctrank(series, win):
    """out[i] = PERCENTRANK.INC(series[i:i+win], series[i])（降序=回看过去 win 天）。"""
    s = np.asarray(series, dtype=float)
    n = s.size
    out = np.full(n, np.nan)
    for i in range(n):
        window = s[i:i + win]
        if np.count_nonzero(~np.isnan(window)) >= 2:
            out[i] = percentrank_inc(window, s[i])
    return out


def roll_mean(series, win):
    """out[i] = mean(series[i:i+win])，忽略 NaN（对应 Excel AVERAGE 的尾窗）。"""
    s = pd.Series(series, dtype=float)
    # 降序数组上做"向后看 win 个"的均值
    return s[::-1].rolling(win, min_periods=1).mean()[::-1].to_numpy()


def shift_back(series, offset):
    """返回 series[i+offset]（降序数组里=更早 offset 天的值），越界给 NaN。"""
    s = np.asarray(series, dtype=float)
    out = np.full(s.size, np.nan)
    if offset < s.size:
        out[:s.size - offset] = s[offset:]
    return out


# ===========================================================================
# 各底稿指标 → 最终"分位数列"。入参 d 是含原始序列的 dict（均为降序数组）。
# 每个函数返回与日期等长的分位数数组。
# ===========================================================================
def calc_month_drop(d, W):
    """250日月跌幅均值滚动百分位 (主表H)。"""
    close = d["close"]
    base = shift_back(close, W["ret_offset"])
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = ((close - base) / base) / W["ret_div"]  # 30日涨跌幅均值
    return roll_pctrank(ret, W["ret_pct_win"])


def calc_amt_growth(d, W):
    """月均成交额同比增长率250日滚动分位数 (主表I)。"""
    amt = d["amt"] / 1e8
    avg = roll_mean(amt, W["amt_avg_win"])
    base = shift_back(avg, W["amtgrow_offset"])
    with np.errstate(divide="ignore", invalid="ignore"):
        grow = (avg - base) / base
    return roll_pctrank(grow, W["amtgrow_pct_win"])


def calc_turnover(d, W):
    """日均换手率滚动分位 (主表J)。"""
    avg = roll_mean(d["turnover"], W["turn_avg_win"])
    return roll_pctrank(avg, W["turn_pct_win"])


def calc_raise_ratio(d, W):
    """上涨股票占比滚动分位 (主表K)。"""
    ratio = d["raise_num"] / d["total_num"]
    avg = roll_mean(ratio, W["raise_avg_win"])
    return roll_pctrank(avg, W["raise_pct_win"])


def calc_year_line_dev(d, W):
    """指数偏离年线幅度分位 (主表L)。MA250 = 收盘价250日均值。"""
    close = d["close"]
    ma = roll_mean(close, W["ma_win"])
    dev = close - ma
    return roll_pctrank(dev, W["dev_pct_win"])


def calc_limit(d, W):
    """涨停-跌停 30日均值滚动分位 (主表M)。"""
    diff = d["limit_up"] - d["limit_dn"]
    avg = roll_mean(diff, W["limit_avg_win"])
    return roll_pctrank(avg, W["limit_pct_win"])


def calc_avg_amt(d, W):
    """平均成交额滚动分位 (主表N)。"""
    amt = d["amt"] / 1e8
    avg = roll_mean(amt, W["avgamt_avg_win"])
    return roll_pctrank(avg, W["avgamt_pct_win"])


def calc_pe(d, W):
    """PE 750日滚动分位 (主表O)。"""
    return roll_pctrank(d["pe"], W["pe_pct_win"])


def calc_pb(d, W):
    """PB 750日滚动分位 (主表P)。"""
    return roll_pctrank(d["pb"], W["pb_pct_win"])


def calc_excess_pb(d, W):
    """超额PB(行业PB-全市场PB) 750日滚动分位 (主表Q, 默认权重0)。"""
    if "mkt_pb" not in d:
        return np.full(d["pb"].size, np.nan)
    excess = d["pb"] - d["mkt_pb"]
    return roll_pctrank(excess, W["expb_pct_win"])


def calc_crowding(d, W):
    """行业拥挤度(行业成交额/全市场成交额)滚动分位 (主表R)。"""
    if "mkt_amt" not in d:
        return np.full(d["amt"].size, np.nan)
    ratio = (d["amt"] / 1e8) / (d["mkt_amt"] / 1e8)
    return roll_pctrank(ratio, W["crowd_pct_win"])


# 指标名 → 计算函数（键名与 config.WEIGHTS 对应）
INDICATOR_FUNCS = {
    "月跌幅分位":     calc_month_drop,
    "成交额增速分位": calc_amt_growth,
    "换手率分位":     calc_turnover,
    "上涨占比分位":   calc_raise_ratio,
    "偏离年线分位":   calc_year_line_dev,
    "涨停跌停分位":   calc_limit,
    "平均成交额分位": calc_avg_amt,
    "PE分位":         calc_pe,
    "PB分位":         calc_pb,
    "超额PB分位":     calc_excess_pb,
    "拥挤度分位":     calc_crowding,
}


def compute_temperature(data, weights, win):
    """
    data: dict, 每个键是降序的原始序列(numpy)，以及一个 'dates'(降序日期)。
    weights: {指标名: 权重}
    返回 DataFrame: 日期 + 各指标分位 + 温度，按日期降序（第一行=最新）。
    """
    dates = data["dates"]
    out = pd.DataFrame({"日期": dates})
    active = [k for k, w in weights.items() if w != 0]

    for name in weights:
        if name in INDICATOR_FUNCS:
            out[name] = INDICATOR_FUNCS[name](data, win)

    wsum = sum(weights[k] for k in active)
    temp = np.zeros(len(dates))
    valid = np.zeros(len(dates), dtype=bool) | True
    acc = np.zeros(len(dates))
    for k in active:
        col = out[name if False else k].to_numpy(dtype=float)
        acc = acc + np.nan_to_num(col) * weights[k]
        valid &= ~np.isnan(col)
    out["温度"] = np.where(valid, acc / wsum, np.nan)
    return out
