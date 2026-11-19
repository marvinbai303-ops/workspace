---
name: industry-clock-verify
description: 当用户需要验证基金经理的产业时钟感、分析行业配置贡献、评估产业趋势判断能力、归因产业贝塔与选股阿尔法、或判断基金经理是靠赛道beta还是beta+alpha双驱动时使用。即使用户说"分析XX的产业时钟"、"看看XX的产业趋势判断能力"、"验证XX的产业入退场时点"，也应触发。
---

# 产业时钟验证 Skill

---

## Agent Interface（供其他 Agent 调用）

其他 Agent（如基金经理选股 Agent、研究报告生成 Agent）若需调用本 Skill，按以下接口规范传参。

### 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `manager_name` | string | ✅ | 基金经理姓名，例如 `"冯明远"` |
| `fund_code` | string | 二选一 | 代表基金代码，例如 `"519697"` |
| `period_start` | string | 否 | 分析起始季度，格式 `"2022Q1"`，默认当前时间往前3年 |
| `period_end` | string | 否 | 分析截止季度，格式 `"2025Q4"`，默认最近完整季度 |
| `benchmark` | string | 否 | 基准指数，默认 `"hs300"`，可选值见 `data/benchmarks/` 文件名前缀 |
| `industry_focus` | list[string] | 否 | 强制指定产业方向，例如 `["semiconductor", "photovoltaic"]`，不填则自动识别 |
| `output_dir` | string | 否 | 中间文件输出目录，默认 `.alphaclaw/tmp/` |

### 输出文件

所有文件写入 `{output_dir}/{manager_name}_` 前缀目录下：

| 文件名 | 说明 |
|--------|------|
| `{manager_name}_行业配置权重.csv` | 近N季度各行业权重明细 |
| `{manager_name}_行业指数收益率.csv` | 申万一级行业指数季度收益率 |
| `{manager_name}_Brinson归因结果.csv` | 季度行业配置贡献+选股贡献 |
| `{manager_name}_分行业配置贡献.csv` | 按申万一级行业汇总的累计贡献 |
| `{manager_name}_产业渗透率景气度.csv` | 匹配的产业景气指标时序数据 |
| `{manager_name}_产业时钟验证报告.md` | 最终分析报告（3000-4000字） |

### 调用示例

```python
# 场景1：分析单个基金经理（只需姓名）
invoke_skill("industry-clock-verify", {
    "manager_name": "冯明远"
})

# 场景2：指定基金代码 + 分析时段
invoke_skill("industry-clock-verify", {
    "fund_code": "519697",
    "manager_name": "冯明远",
    "period_start": "2022Q1",
    "period_end": "2025Q3",
    "benchmark": "cyb"
})

# 场景3：批量分析（多个基金经理，由上层 Agent 循环调用）
for manager in ["冯明远", "武阳", "孙硕"]:
    invoke_skill("industry-clock-verify", {"manager_name": manager})
```

### 返回值契约

Skill 执行完成后，调用方 Agent 可在 `output_dir` 下读取上述输出文件。最终报告 `.md` 文件包含：
- 第四节"核心结论与能力画像"中的 `core_tags`（1-3个产业趋势标签）
- Brinson 归因累计行业配置贡献值（正值=行业选择贡献超额收益）
- 产业时钟综合评分表（各产业方向 1-5 分）

---

## 概述

聚焦基金经理的产业趋势研究能力验证，核心输出两件事：
1. **Brinson 归因分解**——精确拆分行业配置贡献（产业贝塔）和选股贡献（阿尔法），基于持仓权重和行业指数收益率自主计算
2. **产业时钟感验证**——用产业渗透率、景气度等指标与持仓变化做时序匹配，量化验证基金经理的产业周期判断能力

本 Skill 依赖预置的产业景气度数据（data/ 目录），数据优先从本地读取，仅在本地缺失时才调 API 实时获取。

---

## 数据目录结构（data/）

数据按行业分目录存储，每个行业目录包含若干 CSV 文件和一个 `_manifest.yaml` 描述文件。

```
data/
├── benchmarks/                          # 指数基准季度收益率
│   ├── hs300_quarterly_returns.csv      # 沪深300指数 (2022Q1-2026Q2)
│   ├── cs500_quarterly_returns.csv      # 中证500指数
│   ├── cs800_quarterly_returns.csv      # 中证800指数
│   ├── cs1000_quarterly_returns.csv     # 中证1000指数
│   ├── cs2000_quarterly_returns.csv     # 中证2000指数
│   ├── cyb_quarterly_returns.csv        # 创业板指
│   ├── kc50_quarterly_returns.csv       # 科创50指数
│   ├── thsqa_quarterly_returns.csv      # 同花顺全A
│   ├── hstech_quarterly_returns.csv     # 恒生科技指数
│   └── nasdaq100_quarterly_returns.csv  # 纳斯达克100指数
│
├── semiconductor/                       # 半导体/算力
│   ├── _manifest.yaml                   ← 读此文件了解所有指标定义
│   ├── wsts_semiconductor.csv           # WSTS全球半导体月度销售额+同比 (2022-01~2026-02) [同步]
│   ├── tsmc_revenue_monthly.csv         # 台积电月度营收 (2010-01~2026-03) [领先]
│   └── dram_ddr4_8gb_monthly.csv        # DRAM DDR4 8Gb合约均价 (2021-10~2026-02) [领先]
│
├── photovoltaic/                        # 光伏
│   ├── _manifest.yaml
│   ├── polysilicon_price_weekly.csv     # 多晶硅料现货均价，周度 (2025-02~2026-04) [领先]
│   └── pv_installation.csv             # 光伏新增装机累计值 (2022-02~2026-02) [同步]
│
├── new_energy_vehicle/                  # 新能源汽车
│   ├── _manifest.yaml
│   ├── nev_penetration.csv             # 新能源车批发渗透率 (2022-01~2026-03) [同步]
│   └── battery_installation_monthly.csv # 动力电池装车量+同比 (2017-01~2026-03) [同步]
│
├── upstream_materials/                  # 上游原材料（碳酸锂/稀土/铜）
│   ├── _manifest.yaml
│   ├── lithium_carbonate_weekly.csv     # 碳酸锂电池级均价，周度 (2026-01~2026-04) [领先] ⚠️历史较短
│   ├── praseodymium_neodymium_weekly.csv # 氧化镨钕均价，周度 (2026-01~2026-04) [领先] ⚠️历史较短
│   └── copper_lme_weekly.csv           # LME铜现货结算价，周度 (2024-01~2026-04) [领先]
│
└── wind_offshore/                       # 风电（含海风）
    ├── _manifest.yaml
    └── wind_installation.csv           # 风电新增装机累计值 (2022-02~2026-02) [同步]
```

**指标性质标注说明**：
- `[领先]`：通常领先行业景气拐点 1-3 个季度，可用于前瞻判断
- `[同步]`：与行业景气同步，用于验证和确认
- `[滞后]`：反映结果，用于事后归因
- ⚠️：数据历史较短，需补充后使用

---

## 执行步骤

### 步骤 1：确认分析目标

从用户输入中提取基金经理姓名或基金代码（必选），分析时间范围（默认最近 3 年，约 12 个季度）。

如果用户只给了姓名，先查询该基金经理管理的所有基金，选择管理时间最长、规模最大的代表性产品。

### 步骤 2：并行数据采集

同时发起 3 个 task（subagent_type="general"），每个 task 将结果保存为 CSV 到 `.alphaclaw/tmp/` 目录。

**task A — 基金行业配置权重与重仓股明细**

使用基金持仓查询工具获取近 12 个季度的行业配置权重（从前十大重仓股按申万一级行业归类）和前十大重仓股明细（名称、代码、占净值比、行业）。

输出文件：`.alphaclaw/tmp/{基金经理姓名}_行业配置权重.csv`

**task B — 申万行业指数季度收益率 + 基金与基准收益率**

- 基准收益率：优先读取本地文件 `data/benchmarks/hs300_quarterly_returns.csv`
- 申万一级行业指数季度收益率：使用 EDB 查询"申万行业指数:一级行业:{行业名} 收盘价日频数据"，从日频收盘价提取季度收益率
- 分析基金的季度净值收益率：使用基金行情工具

输出文件：`.alphaclaw/tmp/{基金经理姓名}_行业指数收益率.csv`

**task C — 产业渗透率与景气度数据**

根据基金主配方向，读取对应行业目录下的本地数据文件，并参考该目录的 `_manifest.yaml` 了解各指标的性质和使用方法：

| 产业方向 | 目录 | 核心指标文件 | 指标性质 |
|----------|------|------------|---------|
| TMT/AI算力 | `data/semiconductor/` | tsmc_revenue_monthly.csv, dram_ddr4_8gb_monthly.csv, wsts_semiconductor.csv | 领先+同步 |
| 新能源车 | `data/new_energy_vehicle/` | nev_penetration.csv, battery_installation_monthly.csv | 同步 |
| 光伏 | `data/photovoltaic/` | polysilicon_price_weekly.csv, pv_installation.csv | 领先+同步 |
| 风电/海风 | `data/wind_offshore/` | wind_installation.csv | 同步 |
| 上游原材料 | `data/upstream_materials/` | lithium_carbonate_weekly.csv, copper_lme_weekly.csv, praseodymium_neodymium_weekly.csv | 领先 |

读取后检查数据时间覆盖范围，若最新月份不够（与分析截止日差距超过 2 个月），参照 `_manifest.yaml` 中的 `update` 字段说明通过 iFinD EDB 补充最新数据并追加至文件。

输出文件：`.alphaclaw/tmp/{基金经理姓名}_产业渗透率景气度.csv`

### 步骤 3：归因计算

3 个数据采集 task 全部完成后，发起 task（subagent_type="general"）：

读取 `{基金经理姓名}_行业配置权重.csv` 和 `{基金经理姓名}_行业指数收益率.csv`，编写并运行 Python 脚本计算 Brinson 归因：

- 虚拟行业配置回报 = Σ(基金各行业权重_i × 申万一级行业指数收益率_i)
- 行业配置贡献 = 虚拟行业配置回报 - 基准收益率
- 选股贡献 = 基金实际收益率 - 虚拟行业配置回报
- 未被重仓股覆盖的仓位（"其他行业"）使用基准收益率作为代理

Python 仅使用 csv 标准库。

输出文件：
- `.alphaclaw/tmp/{基金经理姓名}_Brinson归因结果.csv`
- `.alphaclaw/tmp/{基金经理姓名}_分行业配置贡献.csv`

### 步骤 4：产业时钟验证与报告撰写

读取全部 CSV 文件，发起 task（subagent_type="make-report", stream_to_parent=True），撰写产业时钟验证报告。

报告结构：

#### 一、基金经理概览（300字以内）

基本信息、评估区间、基准（沪深300指数）、核心结论先行（一句话概括归因结果）。

#### 二、Brinson 业绩归因（约 1500 字）

- 2.1 方法说明（基准沪深300、公式、数据来源）
- 2.2 季度归因汇总表（嵌入完整 Brinson 归因结果）
- 2.3 累计归因结论（累计值、正确率）
- 2.4 关键季度深度解读（3-4 个代表性季度）
- 2.5 分行业配置路径（主配行业权重变化时间线）

#### 三、产业时钟感验证（约 2000 字，核心章节）

- 按产业方向分节，每节嵌入渗透率×持仓权重匹配表
- 分析持仓权重变化与景气指标的时序关系（参考各行业 `_manifest.yaml` 的 `clock_logic`）
- 评价入场时点、加码节奏、退出时点
- 特别注意区分领先指标（基金经理是否在数据领先时就做出决策）与同步指标（追涨信号）
- **产业时钟综合评分表**：| 产业方向 | 入场判断 | 加码节奏 | 退出/回避 | 综合评分 |

#### 四、核心结论与能力画像

核心标签、能力圈、风格特征、关注点。

#### 五、风险提示与归因局限性

行业权重推算偏差、选股贡献含残差、样本期有限、渗透率数据时滞、基准选择影响。

**格式铁律**：
- 所有百分比精确到两位小数
- 禁止"约"、"大约"、"左右"等模糊词
- 全部使用 Markdown 表格
- 数据标注来源
- 3000-4000 字
- 不使用 emoji

报告保存路径：`.alphaclaw/tmp/{基金经理姓名}_产业时钟验证报告.md`

---

## 数据更新指南

### 何时需要更新

执行分析时，对每个用到的 CSV 文件，检查其最新日期与当前分析截止日的差距：
- 月度数据：差距 > 2 个月 → 需要更新
- 周度数据：差距 > 4 周 → 需要更新

### 如何更新（Claude 执行）

1. 打开对应行业目录的 `_manifest.yaml`，找到目标指标的 `update` 字段
2. 若 `update.method: ifind_edb`，调用 iFinD EDB 工具拉取增量数据：
   ```
   # 示例：更新台积电营收
   get_edb_data(index_ids=['S002975304', 'S009085265'],
                start_date='20260101', end_date='20260427')
   ```
3. 将新增行追加至对应 CSV 文件（保持原有列格式，不重复已有数据）
4. 更新 `_manifest.yaml` 中的 `update.last_updated` 字段

### 分批拉取历史数据

iFinD EDB 工具每次最多返回约 60 条记录。对于历史较短的日频价格数据（碳酸锂、氧化镨钕），如需补充完整历史，按年份分批拉取：
```
# 批次1：get_edb_data(['S020190575'], start_date='20210101', end_date='20211231')
# 批次2：get_edb_data(['S020190575'], start_date='20220101', end_date='20221231')
# 批次3：get_edb_data(['S020190575'], start_date='20230101', end_date='20231231')
# 批次4：get_edb_data(['S020190575'], start_date='20240101', end_date='20241231')
# 批次5：get_edb_data(['S020190575'], start_date='20250101', end_date='20260427')
```
拉取后用 Python 聚合为周度（ISO 周，取最后一个交易日为日期键，周内均价），追加至 CSV。

---

## 注意事项

1. **本地数据优先**：执行时先用 read 工具检查 data/ 目录下是否有对应文件，有则直接读取，无则调 API。读取后检查数据时间覆盖范围，不够则用 EDB 补充最新数据。

2. **Manifest 优先阅读**：每次分析前务必读取目标行业目录的 `_manifest.yaml`，了解各指标的 `nature`（领先/同步/滞后）和 `clock_logic`，避免用同步指标错误替代领先指标。

3. **行业方向自动识别**：根据最近 4 个季度行业权重均值自动判定主配方向（TMT/新能源/医药/有色/消费等），动态选择匹配的景气度指标。

4. **Python 计算环境**：使用系统环境中的 Python（AlphaEngine 目录），仅使用 csv 标准库，不依赖 pandas。

5. **数据工具优先级**：本地 CSV > iFind 专业工具（EDB/基金/股票）> query_finance_data > websearch。专业工具获取失败时降级。

6. **避免后视偏差**：评估时钟感时，基于当时可获得的信息判断决策合理性，而非事后结果倒推。领先指标需确认基金经理决策时该数据已发布（注意数据发布滞后）。

7. **参考案例**：典型产业趋势基金经理：易方达武阳、宏利基金孙硕、东吴刘元海、交银冯明远、华商伍文友、国投瑞银王鹏等。
