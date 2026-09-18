---
name: yiyao-yanjiu-skill
description: "Use this skill for Chinese buy-side research on pharmaceutical sectors and stocks, especially innovative drugs, modality-specific pipelines, and CXO/CRO/CDMO companies. It classifies business models, locates the current prosperity-transmission stage, scores stock opportunity, data confidence, and position risk separately, and states when the CXO framework is not applicable."
---

# 医药研究 skill

面向创新药及 CXO 的行业、公司和个股机会研究。输出研究判断和可证伪线索，不执行交易，也不把市场上涨本身当作基本面证据。

默认用中文回答。涉及当前事实或数字时必须核对来源与日期；无法核实则明确标为待验证。除非用户明确要求“使用聚源”，否则不要调用聚源数据。市场、财务和公告数据可优先使用可用的 iFinD 或监管、交易所、公司原始披露。

## 先做适用性判断

先识别公司属于以下哪一类：

1. 创新药研发及商业化；
2. CXO：向第三方提供 CRO、SMO、CMO、CDMO 或 CRDMO 服务；
3. 同时拥有创新药和 CXO 业务；
4. 两者均不属于。

只有内部研发、内部生产能力而没有第三方外包服务收入，不属于 CXO。若公司不涉及 CXO，必须直接写明“CXO框架不适用”，不得强行套用订单、产能利用率或外包渗透率评分。若只存在非核心或披露不足的 CXO 业务，标记“部分适用”，只分析对应分部并降低数据可信分。

## 核心工作流

1. 明确公司、代码、市场、研究时点和用户关注期限。
2. 通过信源闸门区分已发生事实、公司指引、卖方推演和市场叙事。价量只进入位置风险，不进入基本面机会分。
3. 按业务类型读取对应框架：
   - 创新药公司或技术路线研究：读 [references/innovation-drug-framework.md](references/innovation-drug-framework.md)。
   - CXO 公司或行业研究：必须读 [references/cxo-framework.md](references/cxo-framework.md)。
4. 涉及数字、来源选择、缺失数据或可比性时，读 [references/data-source-gate.md](references/data-source-gate.md)。
5. 个股机会、数据可信度或位置风险打分时，必须读 [references/scoring.md](references/scoring.md)。
6. 输出时使用 [references/output-template.md](references/output-template.md)；短问可压缩，但不能省略适用性、数据日期和三分分离。

## 不可破坏的判断原则

- 创新药必须按“技术路线 × 靶点/机制 × 适应症 × 临床阶段”分析，不能只按热门技术路线排序。
- CXO 必须先分型再打分；临床 CRO 与 CDMO 不得共用一套经营指标权重。
- 景气传导不能被压成一句“融资回暖利好 CXO”。必须标出领先节点、已确认节点、传导断点和当前方向。
- 机会分、数据可信分、位置风险分分别为 0–100，互不替代，也不得直接相减成一个伪精确总分。
- 缺失数据记为 NA，不按 50 分处理；覆盖不足时停止排名并说明还缺什么。
- 市场规模预测、外包率远期预测、License-out 总交易金额和单一卖方预测只能作为背景，不能直接给个股加分。
- 对文章、纪要或研报中的数字，尽量追溯到监管、交易所、公司公告、临床登记或原始数据库；无法追溯时降低可信度。
- 明确列出证伪条件和下一次可观察的数据窗口。

