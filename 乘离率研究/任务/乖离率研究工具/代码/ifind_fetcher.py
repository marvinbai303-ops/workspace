"""
iFind 行情数据拉取与解析模块
==============================
职责：
  1. 解析 iFind MCP 工具返回的 Markdown 表格格式
  2. 严格校验数据完整性（不足/截断/缺失 → 抛异常，不估算、不补值）
  3. 将数据整理为 bias_calculator.py 所需的标准 DataFrame（date, code, close）

使用场景（供 agent 调用）：
  from ifind_fetcher import parse_ifind_response, validate_price_data, build_price_df

  # agent 已通过 MCP 工具获取到 response 字符串
  df = parse_ifind_response(response_text, expected_code="000300.SH")
  validate_price_data(df, code="000300.SH", min_days=60)

注意：
  - agent 必须对每个指数单独调用 iFind 工具，禁止合并多个指数批量查询，
    原因：批量查询会触发"以下为部分数据"截断，导致数据不完整。
  - 若返回数据被截断，parse_ifind_response 会抛出 DataTruncatedError，
    agent 应停止后续运算并报告错误。
"""

import re
import sys
from datetime import date, datetime, timedelta
from io import StringIO
from typing import Optional

import pandas as pd


# ─── 自定义异常 ───────────────────────────────────────────────────────────────

class IFindDataError(Exception):
    """iFind 数据获取或解析失败的基类"""
    pass

class DataTruncatedError(IFindDataError):
    """iFind 返回了截断数据（"以下为部分数据"）"""
    pass

class DataEmptyError(IFindDataError):
    """iFind 未返回任何有效行情数据"""
    pass

class DataInsufficientError(IFindDataError):
    """数据行数不足，无法保证 EMA 收敛"""
    pass

class DataStaleError(IFindDataError):
    """数据最新日期过旧，可能是未更新或取错了标的"""
    pass

class DataGapError(IFindDataError):
    """数据存在不可接受的缺失（NaN 收盘价）"""
    pass


# ─── 核心解析函数 ──────────────────────────────────────────────────────────────

def parse_ifind_response(
    response_text: str,
    expected_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    解析 iFind MCP 工具返回的原始文本（含 Markdown 表格），
    提取 date / code / close 三列，按日期正序排列。

    Parameters
    ----------
    response_text : iFind MCP 工具返回的完整字符串
    expected_code : 期望的指数代码（用于校验，防止拿错数据）

    Returns
    -------
    DataFrame，列为：date(datetime), code(str), close(float)

    Raises
    ------
    DataTruncatedError  - 响应中出现"以下为部分数据"
    DataEmptyError      - 未找到任何表格行
    IFindDataError      - 代码不匹配或其他解析异常
    """
    # ── 1. 截断检测（硬停）───────────────────────────────────────────────────
    if "以下为部分数据" in response_text:
        raise DataTruncatedError(
            f"[{expected_code}] iFind 返回数据被截断（响应含【以下为部分数据】提示）。\n"
            "请将该指数单独查询，不要与其他指数合并请求。\n"
            "运算已停止，不使用不完整数据。"
        )

    # ── 2. 提取 Markdown 表格 ────────────────────────────────────────────────
    lines = response_text.split("\n")
    table_lines = [l.strip() for l in lines if l.strip().startswith("|")]

    if len(table_lines) < 3:  # 至少需要：表头 + 分隔线 + 1行数据
        raise DataEmptyError(
            f"[{expected_code}] iFind 响应中未找到有效的 Markdown 表格。\n"
            f"响应内容摘要：{response_text[:300]}"
        )

    # ── 3. 解析表头 ──────────────────────────────────────────────────────────
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # 找到各列索引（列名可能含单位说明，用关键词匹配）
    def find_col(keywords: list[str]) -> Optional[int]:
        for i, h in enumerate(headers):
            if any(kw in h for kw in keywords):
                return i
        return None

    col_code  = find_col(["证券代码", "代码"])
    col_date  = find_col(["日期"])
    col_close = find_col(["收盘价（单位", "收盘价(不前推)", "收盘价（不前推", "收盘价"])

    # 优先用"不前推"的收盘价（更适合指数），若不存在则用普通收盘价
    col_close_no_fwd = find_col(["收盘价（不前推）", "收盘价(不前推)"])
    if col_close_no_fwd is not None:
        col_close = col_close_no_fwd

    missing_cols = []
    if col_code  is None: missing_cols.append("证券代码")
    if col_date  is None: missing_cols.append("日期")
    if col_close is None: missing_cols.append("收盘价")

    if missing_cols:
        raise IFindDataError(
            f"[{expected_code}] 表格缺少必要列：{missing_cols}。\n"
            f"识别到的表头：{headers}"
        )

    # ── 4. 解析数据行 ────────────────────────────────────────────────────────
    records = []
    for line in table_lines[2:]:  # 跳过表头和分隔线
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) <= max(col_code, col_date, col_close):
            continue  # 行列数不足，跳过（防御）

        code_val  = cells[col_code].strip()
        date_val  = cells[col_date].strip()
        close_val = cells[col_close].strip()

        # 跳过空行或非数据行
        if not date_val or not close_val or close_val in ("—", "-", "null", ""):
            continue

        try:
            dt    = datetime.strptime(date_val, "%Y%m%d").date()
            close = float(close_val)
        except (ValueError, TypeError):
            continue  # 忽略无法解析的行（不估算）

        records.append({"date": dt, "code": code_val, "close": close})

    if not records:
        raise DataEmptyError(
            f"[{expected_code}] 表格中未解析到任何有效数据行。"
        )

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # ── 5. 代码一致性校验 ────────────────────────────────────────────────────
    if expected_code is not None:
        actual_codes = df["code"].unique().tolist()
        if len(actual_codes) > 1:
            raise IFindDataError(
                f"[{expected_code}] 响应中含多个指数代码：{actual_codes}。\n"
                "请单独查询每个指数，不要批量合并请求。"
            )
        if actual_codes[0] != expected_code:
            raise IFindDataError(
                f"期望代码 {expected_code}，但数据实际代码为 {actual_codes[0]}。"
            )

    return df


# ─── 数据校验（硬停，不估算）────────────────────────────────────────────────

def validate_price_data(
    df: pd.DataFrame,
    code: str,
    min_days: int = 60,
    max_stale_days: int = 7,
) -> None:
    """
    对单个指数的行情数据做严格校验，任一项不通过则抛出异常、停止运算。

    校验项：
      1. 最少交易日数 >= min_days（保证 EMA20 充分收敛）
      2. close 列无 NaN（不补值、不估算）
      3. 最新日期距今不超过 max_stale_days 个自然日（防止数据过旧）

    Parameters
    ----------
    df            : parse_ifind_response 返回的 DataFrame
    code          : 指数代码，用于错误信息
    min_days      : 最少需要的交易日数，默认 60
    max_stale_days: 最新数据距今允许的最大自然日数，默认 7（含周末）

    Raises
    ------
    DataInsufficientError  - 数据行数不足
    DataGapError           - close 中存在 NaN
    DataStaleError         - 最新日期过旧
    """
    # ── 1. 行数校验 ──────────────────────────────────────────────────────────
    actual_days = len(df)
    if actual_days < min_days:
        raise DataInsufficientError(
            f"[{code}] 数据不足：获取到 {actual_days} 个交易日，"
            f"最少需要 {min_days} 个。\n"
            "请扩大查询日期范围（建议请求近 90 个自然日）。\n"
            "运算已停止。"
        )

    # ── 2. NaN 校验 ──────────────────────────────────────────────────────────
    nan_count = df["close"].isna().sum()
    if nan_count > 0:
        nan_dates = df[df["close"].isna()]["date"].dt.strftime("%Y-%m-%d").tolist()
        raise DataGapError(
            f"[{code}] close 价格存在 {nan_count} 处缺失（NaN），\n"
            f"涉及日期：{nan_dates[:10]}{'...' if len(nan_dates) > 10 else ''}。\n"
            "不允许估算或填充缺失值，运算已停止。"
        )

    # ── 3. 数据新鲜度校验 ────────────────────────────────────────────────────
    latest_date = df["date"].max().date()
    today       = date.today()
    gap_days    = (today - latest_date).days

    if gap_days > max_stale_days:
        raise DataStaleError(
            f"[{code}] 数据过旧：最新日期为 {latest_date}，"
            f"距今已 {gap_days} 天（允许最多 {max_stale_days} 天）。\n"
            "请检查 iFind 查询的日期参数，或确认该标的是否仍在交易。\n"
            "运算已停止。"
        )


# ─── 合并多个指数数据 ──────────────────────────────────────────────────────────

def build_price_df(
    responses: dict[str, str],
    min_days: int = 60,
    max_stale_days: int = 7,
) -> pd.DataFrame:
    """
    将多个指数的 iFind 响应文本解析、校验并合并为统一的 price_df。

    Parameters
    ----------
    responses : {code: response_text}，每个指数的 iFind 原始返回文本
    min_days  : 每个指数最少需要的交易日数
    max_stale_days : 最新数据允许距今的最大自然日数

    Returns
    -------
    price_df : DataFrame（date, code, close），供 run_bias.run_analysis() 使用

    Notes
    -----
    - 任何一个指数校验失败，函数立即抛出对应异常，整体运算停止。
    - 不跳过失败的指数，不使用估算数据。
    """
    all_dfs = []
    for code, text in responses.items():
        print(f"  [解析] {code} ...", end=" ", flush=True)
        df = parse_ifind_response(text, expected_code=code)
        validate_price_data(df, code=code, min_days=min_days, max_stale_days=max_stale_days)
        print(f"✅  {len(df)} 个交易日，最新：{df['date'].max().date()}")
        all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True)


# ─── 命令行工具：解析单个响应文件 ─────────────────────────────────────────────

def parse_file(path: str, expected_code: str, min_days: int = 60) -> pd.DataFrame:
    """
    从文件读取 iFind 响应文本，解析并校验，返回 DataFrame。
    供 agent 将 iFind 响应保存为文件后调用。
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    df = parse_ifind_response(text, expected_code=expected_code)
    validate_price_data(df, code=expected_code, min_days=min_days)
    return df


# ─── 自测 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 测试 1：正常解析
    mock_ok = """|证券代码|证券简称|日期|收盘价（单位：元）|
|---|---|---|---|
|000300.SH|沪深300|20260526|4947.8493|
|000300.SH|沪深300|20260525|4921.5974|
|000300.SH|沪深300|20260522|4845.0956|
"""
    df = parse_ifind_response(mock_ok, expected_code="000300.SH")
    print("测试1（正常解析）通过，行数：", len(df))
    print(df)

    # 测试 2：截断检测
    mock_truncated = "为您找到144条数据，以下为部分数据：\n|证券代码|...|"
    try:
        parse_ifind_response(mock_truncated, expected_code="000300.SH")
        print("测试2 失败：未抛出 DataTruncatedError")
    except DataTruncatedError as e:
        print(f"\n测试2（截断检测）通过：{type(e).__name__}")

    # 测试 3：数据行数不足
    try:
        validate_price_data(df, code="000300.SH", min_days=60)
    except DataInsufficientError as e:
        print(f"\n测试3（行数不足）通过：{type(e).__name__}")
        print(str(e))
