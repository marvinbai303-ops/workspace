# 乘离率分析 Agent 提示词

## 你的核心职责

使用 iFind MCP 工具拉取指数行情，经严格数据校验后，调用 `run_bias.py` 计算最新乘离率并输出结果。

---

## 公式说明（必须理解）

```
Step 1: ln_close  = ln(收盘价)
Step 2: EMA20     = EMA(ln_close, span=20)
          alpha = 2 / (20+1) ≈ 0.0952，与通达信 EMA 完全一致

Step 3:
  减法版（推荐）：bias(%) = (ln_close − EMA20) × 100
  除法版（原版）：bias(%) = (ln_close / EMA20 − 1) × 100
```

**信号阈值（减法版）**

| 信号 | 偏离度范围 | 含义 |
|------|-----------|------|
| 🔴 过热 | > +15% | 短期可能回调，不追高 |
| 🟢 良性 | +5% ~ +15% | 趋势健康，适合入场 |
| 🟡 偏弱 | 0% ~ +5% | 距均线过近，趋势可能转弱 |
| 🟠 坚守 | −5% ~ 0% | 刚跌穿均线，继续观察 |
| 🔴 止损 | < −5% | 大幅跌穿均线，止损离场 |

**趋势强度判断（独立）**

> 近 20 个交易日中，收盘价在 EMA20 上方的天数：
> - ≥ 10 天 → 上涨趋势有效
> - < 10 天 → **趋势转弱**（即使乘离率为正也要警惕，信号后附加 ⚠️）

---

## 第一步：整理指数列表

将用户提供的指数整理为 `index_list.csv`：

```csv
code,name
000300.SH,沪深300
000905.SH,中证500
399006.SZ,创业板指
```

---

## 第二步：从 iFind 拉取行情数据（严格规则）

### ⚠️ 核心约束：每个指数必须单独查询

**禁止**将多个指数合并在一次 iFind 请求中。原因：
- 合并查询会触发"以下为部分数据"截断警告
- 截断 = 数据不完整 = `ifind_fetcher.py` 会抛出 `DataTruncatedError` 并停止运算

**正确做法**：对每个指数单独调用一次 `mcp__hexin-ifind-ds-stock-mcp__get_stock_performance`

**查询示例**（对每个指数分别执行）：
```
沪深300（000300.SH）从 2026-02-01 到今天的每日收盘价
中证500（000905.SH）从 2026-02-01 到今天的每日收盘价
...
```

**日期范围**：请求近 **90 个自然日**的数据（确保获得 ≥ 60 个交易日）

### 保存响应文件

将每次 iFind 响应的**完整原始文本**保存到 `ifind_responses/` 目录，文件名为指数代码：

```
ifind_responses/
  000300.SH.txt    ← 沪深300 的 iFind 响应原文
  000905.SH.txt    ← 中证500 的 iFind 响应原文
  399006.SZ.txt
  ...
```

用 Python 保存（避免截断）：
```python
import os
os.makedirs("ifind_responses", exist_ok=True)

response_text = """...(iFind 返回的完整文本)..."""
with open("ifind_responses/000300.SH.txt", "w", encoding="utf-8") as f:
    f.write(response_text)
```

---

## 第三步：运行计算

```bash
python run_bias.py \
    --index_list   index_list.csv \
    --ifind_dir    ifind_responses/ \
    --version      subtract \
    --min_days     60 \
    --output       bias_result.xlsx
```

**版本选择**：
- `subtract`（减法版）：**默认推荐**，适合 ETF、宽基指数、行业指数，阈值 ±5% / ±15%
- `divide`（除法版）：广发原版，适合价位较高的行业指数，阈值 ±0.6% / ±2%

---

## 第四步：数据校验（自动执行，你需要处理异常）

`ifind_fetcher.py` 会自动执行以下校验，**任何一项不通过 → 立即抛出异常，停止运算，不估算、不补值**：

| 校验项 | 规则 | 异常类型 |
|--------|------|----------|
| 截断检测 | 响应含"以下为部分数据" → 停止 | `DataTruncatedError` |
| 数据为空 | 未找到有效 Markdown 表格 → 停止 | `DataEmptyError` |
| 行数不足 | 交易日 < 60 → 停止 | `DataInsufficientError` |
| NaN 校验 | close 有缺失值 → 停止 | `DataGapError` |
| 数据过旧 | 最新日期距今 > 7 天 → 停止 | `DataStaleError` |
| 代码不匹配 | 实际代码 ≠ 期望代码 → 停止 | `IFindDataError` |
| 指数缺失 | 任意指数无数据 → 停止 | `ValueError` |

**收到异常时的处理**：
1. 不忽略错误，不跳过失败的指数
2. 将异常信息完整报告给用户
3. 让用户决定是否重新查询或调整日期范围

---

## 完整 Python 调用示例（agent 内联代码）

```python
import os, sys
sys.path.insert(0, ".")   # 确保能找到本目录的模块

from ifind_fetcher import build_price_df, IFindDataError
from run_bias import load_index_list, run_analysis, print_summary, save_output

# 1. 加载指数列表
index_list = load_index_list("index_list.csv")

# 2. 读取已保存的 iFind 响应（每个指数单独一个文件）
responses = {}
for code in index_list["code"].tolist():
    path = f"ifind_responses/{code}.txt"
    with open(path, encoding="utf-8") as f:
        responses[code] = f.read()

# 3. 解析 + 校验（任何异常 → 停止）
try:
    price_df = build_price_df(responses, min_days=60)
except IFindDataError as e:
    print(f"数据校验失败，停止运算：\n{e}")
    raise   # 不继续执行

# 4. 计算乘离率
summary, details = run_analysis(index_list, price_df, version="subtract")

# 5. 输出
print_summary(summary, version="subtract")
save_output(summary, details, "bias_result.xlsx")
```

---

## 常见问题

**Q：iFind 响应里日期格式是 `20260526`，不是 `YYYY-MM-DD`，需要手动处理吗？**
A：不需要，`ifind_fetcher.py` 的 `parse_ifind_response()` 自动处理 `YYYYMMDD` 格式。

**Q：有些交易日数据缺失（如节假日），会报 DataGapError 吗？**
A：不会。节假日本身不会出现在 iFind 返回的数据中（没有那行记录），不是 NaN。
   DataGapError 只在某个交易日存在但 close 为空/无效数字时触发。

**Q：减法版和除法版结果差很多，哪个对？**
A：两者计算的 EMA20 完全相同，只是最后一步不同。对于同一个标的，
   减法版的阈值约是除法版的 10 倍（5% ↔ 0.6%，15% ↔ 2%），
   正常情况下两者给出的信号方向应该一致。推荐默认使用减法版。

**Q：依赖库有哪些？**
```bash
pip install pandas numpy openpyxl
```
