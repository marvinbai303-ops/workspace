# 导出字段模板

只有表头，不含示例或虚构行情。无需把终端字段强行改成英文；保留原表头、单位与参数后可统一映射。

- `ma_history_seed.csv`：历史初始化，逐股至少250根实际日K；新股保留全部已存在日K。前复权基准日及因子定义另附导出参数。
- `stock_master.csv`：当日全部沪深A股清单，含ST及停牌股票。`is_st`须覆盖ST和*ST。
- `daily_snapshot.csv`：日常更新。数据源必须与初始化一致；股本单位股，价格元、量股、金额元，`return_pct=5`表示5%。
- `mcl_daily_append.csv`：已核验的同源涨跌家数日终增量。`source_id=ifind_A_share_advance_decline_report`，`scope_id=SHSZ_A_INCLUDE_ST_VENDOR_BREADTH_EOD_V1`。仅适用于本文含ST版本。
- `trading_calendar.csv`：可从已经核实的交易日历或上证指数有效日线生成，必须覆盖新增观察日。

完整规则见上级研究目录《历史底库与每日更新取数规范_2026-11-17.md》。
