# -*- coding: utf-8 -*-
"""
数据层 —— 用同花顺 iFinD Python SDK(iFinDPy) 拉取底稿所需的原始序列。

Excel 里的 thsiFinD("<指标id>", code, date, p1, p2) 就是 iFinD 数据接口；
在 Python 里对应 THS_DS(code, indicators, indiparams, globalparams, begin, end)
（按日期返回一段序列，比逐格 THS_BD 高效得多）。

登录方式（任选其一）：
  1) 环境变量 IFIND_USER / IFIND_PWD
  2) 直接传给 login()
若本机已用 iFinD 超级命令登录过，THS_iFinDLogin('','') 也可复用会话。
"""
import os
import numpy as np
import pandas as pd

from config import (DATA_BEGIN, MARKET_CODE, IFIND_INDICATORS,
                    IFIND_MARKET_INDICATORS)

_LOGGED_IN = False


def login(user=None, pwd=None):
    global _LOGGED_IN
    if _LOGGED_IN:
        return
    from iFinDPy import THS_iFinDLogin
    user = user or os.getenv("IFIND_USER", "")
    pwd = pwd or os.getenv("IFIND_PWD", "")
    ret = THS_iFinDLogin(user, pwd)
    if ret not in (0, "0"):
        raise RuntimeError(f"iFinD 登录失败, 返回码={ret}")
    _LOGGED_IN = True


def _ds(code, indicator, indiparams, begin, end):
    """单指标 THS_DS，返回 {Timestamp: value}（升序）。"""
    from iFinDPy import THS_DS
    r = THS_DS(code, indicator, indiparams, "", begin, end)
    # iFinDPy 既可能返回带 .data 的对象，也可能直接返回 DataFrame
    df = getattr(r, "data", r)
    if df is None or len(df) == 0:
        return pd.Series(dtype=float)
    df = pd.DataFrame(df)
    val_col = [c for c in df.columns if c not in ("thscode", "time")][-1]
    s = pd.Series(df[val_col].values,
                  index=pd.to_datetime(df["time"].values))
    return pd.to_numeric(s, errors="coerce")


def fetch_index(code, begin=DATA_BEGIN, end=None, market_series=None):
    """
    拉取单个指数的全部原始序列，返回 compute.compute_temperature 所需的 dict
    （所有序列按日期降序，index 0 = 最新）。
    market_series: 可传入已缓存的全市场序列 {'mkt_amt':Series,'mkt_pb':Series}，避免重复请求。
    """
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    raw = {}
    for key, (ind, par) in IFIND_INDICATORS.items():
        raw[key] = _ds(code, ind, par, begin, end)

    if market_series is None:
        market_series = fetch_market(begin, end)
    raw["mkt_amt"] = market_series["mkt_amt"]
    raw["mkt_pb"] = market_series["mkt_pb"]

    # 以收盘价的交易日为基准，统一对齐后降序
    idx = raw["close"].dropna().index
    idx = pd.DatetimeIndex(sorted(idx, reverse=True))
    data = {"dates": idx}
    for key, s in raw.items():
        data[key] = s.reindex(idx).to_numpy(dtype=float)
    return data


def fetch_market(begin=DATA_BEGIN, end=None):
    """全市场(700001.TI)成交额与PB，供拥挤度/超额PB使用，可缓存复用。"""
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    out = {}
    for key, (ind, par) in IFIND_MARKET_INDICATORS.items():
        out[key] = _ds(MARKET_CODE, ind, par, begin, end)
    return out
