---
name: industry-clock-verify
description: >
  当用户需要评估基金经理的产业趋势研究能力时使用。覆盖两大场景：
  （1）模式A：用户指定某位基金经理，深度分析其产业时钟感——通过Brinson归因验证行业配置贡献、评估入退场时点的准确性；
  （2）模式B：用户看好某个产业方向（如AI算力、新能源），寻找最擅长该赛道的基金经理——从档案库中筛选+排名，输出推荐列表。
  触发示例："分析武阳的产业时钟"、"验证XX的产业趋势判断能力"、"哪位基金经理在半导体赛道上超额最强"、"推荐一个擅长AI算力的基金经理"。
---

# 产业时钟验证 Skill（双模式版）

---

## Agent Interface（供其他 Agent 调用）

### 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | 否 | `"A"`（评估指定经理）或 `"B"`（行业推荐）。不填则自动从 `manager_name` / `target_industry` 推断 |
| `manager_name` | string | 模式A必填 | 基金经理姓名，例如 `"武阳"` |
| `fund_code` | string | 否 | 代表基金代码，例如 `"011891"` |
| `target_industry` | string | 模式B必填 | 目标产业方向，可选：`semiconductor` / `photovoltaic` / `new_energy_vehicle` / `wind_offshore` / `upstream_materials` |
| `period_start` | string | 否 | 分析起始季度，格式 `"2022Q1"`，默认往前3年 |
| `period_end` | string | 否 | 分析截止季度，格式 `"2025Q4"`，默认最近完整季度 |
| `benchmark` | string | 否 | 基准指数，默认 `"hs300"`，可选值见 `data/benchmarks/` 文件名前缀 |
| `output_dir` | string | 否 | 输出目录，默认 `.alphaclaw/tmp/` |

### 输出文件

**模式A**（深度报告）：输出到 `{output_dir}/{manager_name}_` 前缀目录下：

| 文件名 | 说明 |
|--------|------|
| `{manager_name}_行业配置权重.csv` | 近N季度各行业权重明细 |
| `{manager_name}_行业指数收益率.csv` | 申万一级行业指数季度收益率 |
| `{manager_name}_Brinson归因结果.csv` | 季度行业配置贡献+选股贡献 |
| `{manager_name}_分行业配置贡献.csv` | 按申万一级行业汇总的累计贡献 |
| `{manager_name}_产业渗透率景气度.csv` | 匹配的产业景气指标时序数据 |
| `{manager_name}_产业时钟验证报告.md` | 最终分析报告（3000-4000字） |

**模式B**（推荐排名）：

| 文件名 | 说明 |
|--------|------|
| `{target_industry}_经理推荐排名.csv` | 经理评分排名表 |
| `{target_industry}_推荐报告.md` | 推荐说明报告（1000-1500字） |

### 调用示例

```python
# 模式A：深度分析单个基金经理
invoke_skill("industry-clock-verify", {
    "mode": "A",
    "manager_name": "武阳",
    "fund_code": "011891",
    "period_start": "2022Q1",
    "period_end": "2025Q3",
    "benchmark": "cyb"
})

# 模式B：找擅长半导体赛道的基金经理
invoke_skill("industry-clock-verify", {
    "mode": "B",
    "target_industry": "semiconductor"
})

# 自动模式推断（不填mode）
invoke_skill("industry-clock-verify", {"manager_name": "孙硕"})           # → 自动推断模式A
invoke_skill("industry-clock-verify", {"target_industry": "photovoltaic"}) # → 自动推断模式B
```

---

## 概述

聚焦基金经理的产业趋势研究能力，提供两种互补的分析路径：

- **模式A（评估）**：给定基金经理，输出 Brinson 归因+产业时钟感评分，量化回答"TA是靠赛道 beta 还是 beta+alpha 双驱动"
- **模式B（推荐）**：给定产业方向，从内置档案库扫描8位经理，按持仓匹配度+历史产业超额排名，输出推荐列表

两种模式共享同一套评分引擎（见步骤3）和产业数据体系（`data/` 目录）。

---

## 数据目录结构（data/）

```
data/
├── benchmarks/                          # 指数基准季度收益率
│   ├── hs300_quarterly_returns.csv      # 沪深300 (2022Q1-2026Q2)
│   ├── cs500_quarterly_returns.csv      # 中证500
│   ├── cs800_quarterly_returns.csv      # 中证800
│   ├── cs1000_quarterly_returns.csv     # 中证1000
│   ├── cs2000_quarterly_returns.csv     # 中证2000
│   ├── cyb_quarterly_returns.csv        # 创业板指
│   ├── kc50_quarterly_returns.csv       # 科创50
│   ├── thsqa_quarterly_returns.csv      # 同花顺全A
│   ├── hstech_quarterly_returns.csv     # 恒生科技
│   └── nasdaq100_quarterly_returns.csv  # 纳斯达克100
│
├── managers/                            # ★ 基金经理档案库（Layer 1 预置数据）
│   ├── _manifest.yaml                   ← 读此文件了解经理列表、更新方式、行业映射
│   ├── manager_profiles.csv             # 8位经理基本档案（代码/公司/任职/类型/行业）
│   ├── fund_performance.csv             # 近1年/近3年收益率、规模（截至2026-04-28）
│   ├── fund_turnover.csv                # 2024年全年换手率
│   └── fund_top10_holdings_2024q4.csv   # 2024年四季报前十大重仓股
│
├── semiconductor/                       # 半导体/AI算力
│   ├── _manifest.yaml                   ← 读此文件了解所有指标定义
│   ├── wsts_semiconductor.csv           # WSTS全球半导体月度销售额+同比 [同步]
│   ├── tsmc_revenue_monthly.csv         # 台积电月度营收 (2010-01~2026-03) [领先]
│   ├── dram_ddr4_8gb_monthly.csv        # DRAM DDR4 8Gb合约均价 [领先]
│   └── nand_tlc_512gb_weekly.csv        # NAND TLC 512Gb Wafer现货均价，周度 [领先]
│
├── photovoltaic/                        # 光伏
│   ├── _manifest.yaml
│   ├── polysilicon_price_weekly.csv     # 多晶硅料现货均价，周度 [领先]
│   └── pv_installation.csv             # 光伏新增装机累计值 [同步]
│
├── new_energy_vehicle/                  # 新能源汽车
│   ├── _manifest.yaml
│   ├── nev_penetration.csv             # 新能源车批发渗透率 [同步]
│   └── battery_installation_monthly.csv # 动力电池装车量+同比 [同步]
│
├── upstream_materials/                  # 上游原材料（碳酸锂/稀土/铜）
│   ├── _manifest.yaml
│   ├── lithium_carbonate_weekly.csv     # 碳酸锂电池级均价，周度 [领先] ⚠️历史较短
│   ├── praseodymium_neodymium_weekly.csv # 氧化镨钕均价，周度 [领先] ⚠️历史较短
│   └── copper_lme_weekly.csv           # LME铜现货结算价，周度 [领先]
│
└── wind_offshore/                       # 风电（含海风）
    ├── _manifest.yaml
    └── wind_installation.csv           # 风电新增装机累计值 [同步]
```

**指标性质标注说明**：
- `[领先]`：领先行业景气拐点 1-3 个季度，可用于前瞻判断
- `[同步]`：与行业景气同步，用于验证和确认
- ⚠️：数据历史较短，需补充后使用

---

## 执行步骤

### 步骤 0：意图识别与模式选择

根据输入参数判断运行模式：

```
if mode == "A" 或 输入包含 manager_name:
    → 进入模式A流程（步骤1A → 2A → 3A → 4A）
elif mode == "B" 或 输入包含 target_industry:
    → 进入模式B流程（步骤1B → 2B → 3B）
else:
    → 询问用户："您是想评估某位具体的基金经理，还是想找擅长某个行业的基金经理推荐？"
```

---

## 模式A：深度评估指定基金经理

### 步骤 1A：确认分析对象与基础数据

1. 首先读取 `data/managers/manager_profiles.csv`，检查该经理是否已在档案库中
2. 如在档案库中：直接使用预置的 `fund_code`、`tenure_start`、`primary_industries`
3. 如不在档案库中：通过 iFind `search_funds` + `get_fund_profile` 查询基金代码和基本信息
4. 确认分析时间范围（默认：tenure_start 至今，最多12个季度）

### 步骤 2A：并行数据采集

同时发起 3 个 task 并行执行（subagent_type="general"）：

**task A — 基金行业配置权重与重仓股明细**

- 优先读取 `data/managers/fund_top10_holdings_2024q4.csv` 获取基础持仓
- 通过 iFind `get_fund_portfolio` 查询近12个季度的前十大重仓股，按申万一级行业归类
- 计算每季度各行业的持仓权重（市值/总净值）

输出：`{manager_name}_行业配置权重.csv`

**task B — 申万行业指数季度收益率 + 基金与基准收益率**

- 基准：读取 `data/benchmarks/hs300_quarterly_returns.csv`（或参数指定的基准）
- 申万行业指数季度收益率：通过 iFind EDB 查询日频收盘价，提取季度首末收益率
- 基金季度净值收益率：通过 iFind `get_fund_market_performance` 获取

输出：`{manager_name}_行业指数收益率.csv`

**task C — 产业景气度数据**

根据 `manager_profiles.csv` 中该经理的 `primary_industries`，读取对应行业目录下的本地数据文件。必须先读取该行业的 `_manifest.yaml` 了解各指标的性质（`nature`）和 `clock_logic`。

| primary_industry | 读取目录 | 核心文件 |
|-----------------|----------|---------|
| semiconductor | `data/semiconductor/` | tsmc_revenue_monthly.csv, dram_ddr4_8gb_monthly.csv, nand_tlc_512gb_weekly.csv |
| new_energy_vehicle | `data/new_energy_vehicle/` | nev_penetration.csv, battery_installation_monthly.csv |
| photovoltaic | `data/photovoltaic/` | polysilicon_price_weekly.csv, pv_installation.csv |
| wind_offshore | `data/wind_offshore/` | wind_installation.csv |
| upstream_materials | `data/upstream_materials/` | lithium_carbonate_weekly.csv, copper_lme_weekly.csv |

检查数据时间覆盖是否满足分析期间，不足则按 `_manifest.yaml` 中 `update.ifind_query` 补充最新数据。

输出：`{manager_name}_产业渗透率景气度.csv`

### 步骤 3A：归因计算

3个task全部完成后，发起归因计算task：

读取行业权重和行业指数收益率，用Python（仅csv标准库）计算 Brinson 归因：

```python
# 核心公式
虚拟行业配置回报 = Σ(基金行业权重_i × 申万行业指数收益率_i)
行业配置贡献 = 虚拟行业配置回报 - 基准收益率
选股贡献 = 基金实际收益率 - 虚拟行业配置回报
# 注：未被重仓股覆盖的仓位使用基准收益率作为代理
```

同时计算产业时钟吻合度评分（各产业方向 1-5 分）：

| 评分维度 | 满分 | 评分方法 |
|---------|------|---------|
| 入场时点准确性 | 5 | 持仓权重上升时间点 vs 领先指标拐点的超前/滞后季度数 |
| 加码节奏合理性 | 5 | 权重加码是否与景气加速阶段吻合 |
| 退出/回避判断 | 5 | 减仓时点 vs 景气指标见顶时间 |

输出：`{manager_name}_Brinson归因结果.csv`、`{manager_name}_分行业配置贡献.csv`

### 步骤 4A：撰写产业时钟验证报告

读取全部CSV，撰写 3000-4000 字的结构化报告：

**报告结构**：
1. **基金经理概览**（300字以内）——基本信息、评估区间、核心结论先行
2. **Brinson 业绩归因**（约1500字）——方法说明、季度汇总表、关键季度深度解读、分行业配置路径
3. **产业时钟感验证**（约2000字，核心章节）——各产业方向分节，嵌入渗透率×持仓权重匹配表，评价入场/加码/退出时点，给出产业时钟综合评分表
4. **核心结论与能力画像**——核心标签（1-3个）、能力圈、风格特征
5. **风险提示与归因局限性**

**格式铁律**：全部使用Markdown表格；百分比精确到两位小数；禁止"约"、"大约"等模糊词；不使用emoji；3000-4000字。

---

## 模式B：行业推荐——找最擅长该赛道的基金经理

### 步骤 1B：读取档案库并初筛

1. 读取 `data/managers/manager_profiles.csv`，筛选 `primary_industries` 包含 `target_industry` 的经理
2. 读取 `data/managers/fund_performance.csv` 获取收益率数据
3. 读取 `data/managers/fund_turnover.csv` 获取换手率数据
4. 读取 `data/managers/fund_top10_holdings_2024q4.csv`，计算每位经理在该行业的持仓集中度

持仓集中度计算：
```python
# 将top10重仓股映射到产业方向（参考 managers/_manifest.yaml 中的 industry_mapping）
industry_concentration = (匹配该行业的持仓市值合计) / (top10持仓总市值)
```

### 步骤 2B：评分

对每位初筛经理，按以下5个维度打分（总分100分）：

| 维度 | 权重 | 评分依据 |
|------|------|---------|
| 持仓集中度 | 30% | top10中该行业持仓占比（0-100%线性映射到0-30分） |
| 近3年收益率 | 25% | 组内排名（第1名=25分，末名=5分，线性插值） |
| 任职年限 | 20% | 管理该基金年限（>5年=20分，3-5年=15分，<3年=10分） |
| 换手率匹配度 | 15% | 产业型经理适合中低换手（<300%=15分，300-500%=10分，>500%=5分） |
| 近1年收益率 | 10% | 组内排名（体现当前时效性） |

### 步骤 3B：输出推荐排名

生成推荐排名表（CSV + 报告）：

**排名CSV**（`{target_industry}_经理推荐排名.csv`）列：
`rank, manager_name, fund_code, fund_name, company, total_score, holding_concentration_pct, return_3y_pct, return_1y_pct, tenure_years, turnover_2024_pct, manager_type, top3_holdings`

**推荐报告**（`{target_industry}_推荐报告.md`，1000-1500字）结构：
1. 行业当前景气状态（读取对应行业 `_manifest.yaml` 的 `clock_logic`，结合最新数据给出1-2句结论）
2. 候选经理排名表（嵌入完整CSV内容）
3. Top3经理简评（各100-150字，聚焦持仓特点和历史产业操作亮点）
4. 投资建议（结合行业景气阶段，给出配置时点建议）

---

## 数据更新指南

### 检查数据时效

执行分析前，对每个用到的CSV检查最新日期：
- 月度数据：差距 > 2个月 → 需要更新
- 周度数据：差距 > 4周 → 需要更新
- 经理档案：每季度末更新一次（持仓为季报口径）

### 产业数据更新（iFinD EDB）

打开对应行业 `_manifest.yaml`，找到 `update.ifind_query`：
```python
# 示例：更新台积电营收
get_edb_data(index_ids=['S002975304', 'S009085265'],
             start_date='20260101', end_date='20260428')
```
新增行追加至CSV，更新 `last_updated` 字段。

### 经理档案更新（iFinD 基金工具）

```python
# 每季度末更新持仓（更换 report_date）
get_fund_portfolio("011891.OF 在2025-03-31的前十大重仓股")

# 每月更新业绩
get_fund_market_performance("011891.OF 近1年收益率、近3年收益率")

# 每年更新换手率（次年4月年报发布后）
get_fund_financials("011891.OF 在2025-12-31的换手率、资产净值规模")
```

### 批量补充历史价格数据

iFinD EDB每次最多返回约60条记录。日频价格数据（碳酸锂、氧化镨钕）需分年份批量拉取：
```python
# 批次1-5，每批约250条，再用 update_data.py --aggregate weekly 聚合为周频
python update_data.py \
  --file data/upstream_materials/lithium_carbonate_weekly.csv \
  --data '[["2023-01-05", 510000], ...]' \
  --aggregate weekly
```

---

## 注意事项

1. **本地数据优先**：先读取 `data/` 目录，有则直接使用，无则调API补充。
2. **Manifest 必读**：每次分析前读取目标行业 `_manifest.yaml`，尤其是 `nature`（领先/同步）和 `clock_logic`。
3. **避免后视偏差**：评估时钟感时，基于决策时点可获得的信息判断，而非事后倒推。
4. **档案库优先用于模式B**：`data/managers/` 的8位经理是预置MVP，iFind实时查询可扩展至任意经理。
5. **Python 计算**：使用系统环境Python，仅csv标准库，不依赖pandas。
6. **数据工具优先级**：本地CSV > iFind专业工具（EDB/基金/股票） > websearch。
7. **典型标杆经理**（参考对比）：易方达武阳(011891)、宏利孙硕(001170)、东吴刘元海(001323)、景顺张仲维(000411)、易方达郑希(001513)。
