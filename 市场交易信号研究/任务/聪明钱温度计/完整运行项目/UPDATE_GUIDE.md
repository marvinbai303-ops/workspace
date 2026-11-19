# 聪明钱温度计：日常更新约定

主目录：`/Users/yangguang/Documents/Codex/workspace/市场交易信号研究/smart_money_dashboard`。
本看板使用已验收数据，不输出未经回测的加权总分。温度固定为涨家占比 p×100；结论由 p 相对50%、金额TRIN相对1的方向组合生成。均线比例暂未通过全市场验收，ETF MA20、换手率阈值、股债代理不纳入。VW-MACD已加入博主原式12/26/9，日线及已完成周线独立显示。MCL 是保留的原式宽度动量，内含 EMA19/39，不是价格均线。

## 时点、数据源和股票池

- 北京时间每天12:00、17:00触发；先以可靠交易日历核对是否沪深交易日，休市跳过。
- 12:00采集当日11:30完整上午；17:00采集当日收盘；不要用采集时间代替行情时间，不把前日数据贴上今天日期。
- 数据源顺序 iFinD、妙想、Wind。当前已验收序列采用 iFinD，换源必须做重叠口径核验，新源不要直接拼接。
- 非ST宽度/成交分布：当日沪深A股，剔北交所、当日ST/*ST、全天停牌和零成交。每日重新获取动态名单，不能硬编码5027家或上一日名单。
- MCL：固定 iFinD 报表“内地专题统计_二级市场_市场表现_A股涨跌家数统计”的沪深含ST序列；参数统计范围A股，读取沪深合计。不要拿非ST快照替代。
- ETF：510300.SH、510050.SH、588000.SH。只显示三只合计成交额，不识别买方身份。

## 可复用的已验收取数路径

1. 当日非ST沪深股票名单及收盘价量可用 `mcp__hexin_ifind_ds_stock_mcp__search_stocks`。按证券代码前缀分块，下载完整CSV，不使用对话内截断样例。原始请求与返回格式见 `../douyin_research/ifind_batch_retry_2026-11-17/raw/prefix_000.json`。动态确定分块，单块导出条数需等于供应商选中数且小于1000；过大继续细分；完整合并代码集合与总选中数核对。
2. 日终字段：行情日期、代码、名称、不复权收盘价、相对当日交易所参考昨收的原精度涨跌幅、成交股数、成交元数。不要用昨日本地收盘价替代除权日参考价。
3. 午盘已验收路线：`stock_highfreq_quotes`，每批10只、60分钟、字段“收盘价,成交量,成交额,涨跌”。每只仅取10:30与11:30两根完成K线，量额为两根增量之和，参考昨收=第一根收盘-第一根涨跌，第二根收盘与两根涨跌合计交叉检查。不得把累计量再次相加。原实现 `../douyin_research/full_validation_2026-11-17/audit_noon.py`，任务结构 `noon_jobs.json`；它们锁定旧日期，只参考算法，日常脚本必须参数化日期。缺行需要停牌/无交易明确证据，不能自动当零。
4. iFinD 批量上限沿用已验收配置5并发；如果权益报限流则降到2。优先直接连接工具；如需本地批量请求，可复用已安装 ifind-finance-data 的 call-node.js，不读取、打印或复制密钥，不把密钥写入看板或网站。
5. MCL 日终用 `mcp__hexin_ifind_ds_mcp__market_statistics` 请求上面同一报表截至最新交易日。保存原始回执、下载完整表；验收沪市+深市=沪深，每个日期无重复、非负、与可靠交易日历相符。用现有 `../douyin_research/mcl_ifind_include_st_2026-11-17/update_mcl.py --input 新行.csv --calendar 交易日历.csv` 合并重算。历史冲突先核对，不自动允许更正。现有看板发布接口故意拒绝改写历史，如确需修订需明确说明依据，修订规则单独处理。
6. MCL 午盘暂维持“最近日终参考”。未来拿到同口径含ST完整午盘且通过审计，才增加临时递推；这需要修改明确的数据结构，不能直接向日终历史多插入一条。
7. ETF午盘使用已完成上午高频数据，收盘用有效日线。历史底库见 `../douyin_research/ifind_batch_retry_2026-11-17/normalized/三只ETF_有效日线.csv`。午盘与全天不得直接算同比例放量，不乘二估全天。

## 导入规范与生成

每次运行将原始回执、下载文件、动态股票池、排除清单、审计结果保存到 `data/runs/YYYY-MM-DD_noon` 或 `_eod`。保持每个路径的既有内容可审计，不覆盖冲突旧数。

非ST规范化CSV字段与初始日终/午盘CSV一致，至少 date,code,name,return_pct,amount_yuan,volume_shares；午盘额外 time=11:30。验证后在 `data/imports/YYYY-MM-DD_noon.json`（或eod）写如下清单：

```json
{"date":"YYYY-MM-DD","session":"noon","provider":"iFinD MCP","scope_id":"SHSZ_NONST_ACTIVE_V1","csv":"smart_money_dashboard/data/runs/YYYY-MM-DD_noon/normalized.csv","sha256":"文件真实SHA256","expected_codes":["完整已验收的有效股票代码集合"],"validation":{"accepted":true,"missing_codes":[],"universe_count":"真实名单数","excluded_codes":[],"checks":"记录日期、单位、重复、分块完整性、样本勾稽和排除证据"}}
```

只有真实完成验收才写 accepted=true。expected_codes 必须来自核过的动态名单减去有证据的排除项，不能仅从已返回的行情行抄出并宣称完整。金额元、成交量股；原始缺值不得填0。

ETF新增记录追加到 `data/etf_updates.json` 列表，每项含 date,session,time,amount（元）,parts（三只代码和amount）,validated=true,source（工作区源文件相对路径）,sha256（该文件真实指纹）。不得从总额猜三只分项。

运行 `python3 assemble.py` 后，会复算并输出 `data/dashboard.json` 和 `聪明钱温度计.html`；构建中任何断言失败即停止更新，保留此前发布版本。`node test_runtime.mjs` 用于改动算法/发布逻辑后的核验，平常仅数据更新由复算和读回校验即可。

每次保存运行状态与摘要至 `data/runs/日期_时点/run_status.json`，包括成功/跳过/失败、观察截止时间、缺数据字段和来源。不要仅因工具返回success就验收。

## 在线看板更新

Site 标识在 `.openai/hosting.json`。私有网站提供持久化工具 get_thermometer、initialize_thermometer、update_thermometer。运行时先从 ALL_TOOLS 搜索这几个名字，调用正式连接工具；不使用浏览器模拟写数据，不通过匿名网络请求绕过鉴权。

首次用 initialize_thermometer 写入发布的初始底库。日常用 update_thermometer，把 `data/dashboard.json` 完整文本传入 data_json。成功结果必须有 persisted=true、readbackVerified=true；随后 get_thermometer 核对最新快照日期、时点、读数和MCL截止日。只更新数据，不重复部署网站。

如果私有网站工具暂未出现在当前会话，保留本地HTML，明确汇报在线同步未完成。不要修改访问权限，不以浏览器操作或临时凭据替代正式连接。连接恢复后再同步，并以读回结果为准。

数据源失败则保留上一有效快照并明确过期，不输出伪造当期结论。线上只保存经核验汇总数据，逐股原始回执留本地。

## 每次简报

用中文在本对话给出：更新是否成功；数据截止时点与覆盖家数；温度、金额TRIN、额价差；MCL读数及其独立日期；ETF合计额及其时点；一条明确判断及其验证条件；数据缺口；在线及本地看板入口。不要把TRIN、涨额占比、额价差当成三票。

本轮初始数据日期：2026-11-17午盘；上个收盘2026-11-16；MCL291日；ETF209个完整交易日。以实时文件为准，禁止把这些历史计数硬编码为未来要求。

## VW-MACD 日常更新（2026-11-18新增）

对象固定上证指数000001.SH。原式取自视频36 01:40：VC1=SUM(C*V,12)/SUM(V,12)，VC2=SUM(C*V,26)/SUM(V,26)，DIF=VC1-VC2，DEA=EMA(DIF,9)，柱=2*(DIF-DEA)。不能替换成EMA(CV)/EMA(V)。

17:00用iFinD指数日行情取得已完成日线的收盘点数C和成交股数V；补齐底库最后日期到当日间所有交易日，并与可靠交易日历核对。只需获取新增日线，不重下全历史。将新条目追加到data/vw_daily_updates.json，每项date、code=000001.SH、session=eod、close、volume、validated=true、source（原始回执工作区相对路径）、sha256（真实指纹）。assemble.py复算全序列并勾稽原始底库，前25根空值，DEA首个有效DIF初始化。午盘引用最近有效日终，不把半日K插入日终序列。

已完成周的C=周内最后收盘，V=全周成交量之和，按12/26/9根周K计算。当前周只在星期五已收盘或已有可靠交易日历证明结束时加入；节假日缩短周未获证明则等待下一周确认，不误标完成。日线/周线都显示独立日期，DIF零轴与柱值方向分开解读。

MA20/60/150直取复测见 ../douyin_research/ma_native_retry_2026-11-18/均线直接取数复测结论.md。目前原生MA小批量路线取得有效样本；全市场比例仍不发布。以后沿此路线取当日截面并严格验证日期、复权、覆盖与空值原因，不使用已发现日期混合或口径不符的筛选家数。
