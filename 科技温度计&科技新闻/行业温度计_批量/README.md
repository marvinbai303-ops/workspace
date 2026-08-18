# 行业 / 指数温度计 —— 批量计算代码

把 Excel 模板《行业温度计_量价_估值》逆向成 Python，输入一个**指数代码列表**，
批量返回每个指数的「温度」(0~1)。已用模板自带缓存数据校验：复算温度 **0.9423** vs 模板 E5 **0.9418**（差异仅来自模板显示四舍五入）。

---

## 一、温度怎么算的（拆解模板）

主表「市场情绪温度计」E 列：

```
温度 = Σ(各指标分位数 × 权重) / Σ权重
```

11 个指标列 H~R，每个指标在自己的底稿 sheet 里算出一个**滚动分位数**（Excel 的 `PERCENTRANK.INC`），主表只是做加权平均。模板默认权重见下表（超额PB=0，其余=1，S列创新高不进公式）：

| 列 | 指标 | 底稿计算（降序：第3行=最新） | 滚动窗口 | 权重 |
|----|------|------------------------------|----------|------|
| H | 月跌幅分位 | 30日涨跌幅均值 `((close-close[+29])/close[+29])/30`，再取分位 | 250日 | 1 |
| I | 成交额增速分位 | 30日均成交额，环比`(C-C[+30])/C[+30]`，再取分位 | 250日 | 1 |
| J | 换手率分位 | 30日均换手率，取分位 | 250日 | 1 |
| K | 上涨占比分位 | 上涨家数/总家数，30日均值，取分位 | 250日 | 1 |
| L | 偏离年线分位 | close − MA250，取分位 | 250日 | 1 |
| M | 涨停跌停分位 | (涨停−跌停)30日均值，取分位 | 250日 | 1 |
| N | 平均成交额分位 | 30日均成交额，取分位 | 250日 | 1 |
| O | PE分位 | PE_TTM 直接取分位 | **750日** | 1 |
| P | PB分位 | PB 直接取分位 | **750日** | 1 |
| Q | 超额PB分位 | 行业PB − 全市场PB，取分位 | 750日 | **0** |
| R | 拥挤度分位 | 行业成交额/全市场成交额，取分位 | 250日 | 1 |

> 关键点：Excel 的 `PERCENTRANK.INC` 与 pandas 的分位排名算法不同，必须精确复刻（见 `compute.py` 的 `percentrank_inc`），否则温度对不上。

---

## 二、数据接口怎么取（iFinD）

模板里的 `thsiFinD("<指标id>", code, date, ...)` 就是**同花顺 iFinD 数据接口**；
Python 里对应 iFinD SDK 的 `THS_DS(code, indicators, indiparams, "", begin, end)`（按日期返回序列）。指标 id 与模板完全一致：

| 用途 | iFinD 指标 id | 参数 |
|------|---------------|------|
| 收盘价 | `ths_close_price_stock` | `102,` (复权) |
| 成交额(元) | `ths_amt_stock` | |
| 换手率(%) | `ths_turnover_ratio_stock` | |
| 成分股上涨/下跌/总家数 | `ths_constituent_raise_number_index` / `..._fall_...` / `ths_constituent_num_index` | |
| 涨停/跌停家数 | `ths_constituent_up_number_index` / `ths_constituent_dl_number_index` | |
| PE_TTM | `ths_pe_ttm_sr_index` | `100,100` |
| PB | `ths_pb_index` | `108,100` |
| 全市场成交额/PB | 同上，code 用 `700001.TI`（万得全A） | |

> 注：模板原始公式里涨停家数 id 写成 `ths_constituent_ up_number_index`（带空格），代码里已去掉空格。若你的 iFinD 版本指标 id 不同，改 `config.py` 的 `IFIND_INDICATORS` 即可。
> 年线 MA250 模板用 `ths_ma_stock`，代码里直接用收盘价算 250 日均值，少一次请求、结果一致。

---

## 三、文件结构

```
config.py          指标id、参数、滚动窗口、权重（要改阈值/权重就改这里）
compute.py         计算引擎：PERCENTRANK.INC 复刻 + 各指标公式 + 加权温度
ifind_data.py      数据层：iFinDPy 登录 + THS_DS 拉数
batch_run.py       批量入口（命令行）
validate_offline.py 离线自检：用模板缓存数据验证引擎正确性
```

---

## 四、用法

```bash
pip install iFinDPy openpyxl pandas numpy

# 设置 iFinD 账号（或在命令行用 --user/--pwd）
export IFIND_USER=你的账号
export IFIND_PWD=你的密码

# 批量算多个指数（最新温度）
python batch_run.py 000998.CSI 399006.SZ 000300.SH

# 用清单文件 + 同时导出每日温度历史
python batch_run.py --file codes.txt --history
```

输出 `指数温度_汇总.xlsx`：
- sheet「最新温度」：每个指数最新一日的温度 + 11 个分项分位数
- 加 `--history` 后，每个指数一个 sheet，含完整每日温度时间序列

离线验证引擎（不需要 iFinD）：
```bash
python validate_offline.py            # 复算模板自带数据，对比 E5
```

---

## 五、注意事项

- **取数起点** `DATA_BEGIN=2007-01-01`：PE/PB 要 750 日(3年)滚动 + 250 日分位，需要足够长的历史才能算出最新分位。想看更早的温度就再往前取。
- 全市场序列 `700001.TI` 每次只取一次，所有指数复用，省请求。
- 某些行业指数可能没有"涨停/跌停家数""成分股家数"数据，对应分项会是 NaN，该日温度会跳过（除非把权重设 0）。
- 创新高数量(S列)依赖另一个插件函数 `i_techanal_stagehigh_num`，模板权重为 0、不进公式，故代码未实现；如需可单独补。
