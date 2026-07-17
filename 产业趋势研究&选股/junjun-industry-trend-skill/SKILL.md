---
name: junjun-industry-trend-skill
description: "Use this skill for Chinese buy-side style industry trend and stock prosperity diagnosis inspired by 君君/军军/君总: judging whether a stock is trading on real prosperity or theme narrative, scoring prosperity quality vs position risk, processing sell-side/buy-side notes through a source gate, mapping industry topology, analyzing AI/semi value-chain profit redistribution, storage cycles, capex duration, and building falsifiable verification checklists. Trigger on 君君产业趋势skill, 君君, 军军, 君总, 景气度诊断, 景气还是主题, 信源闸门, 底子分/位置分, 产业拓扑, 97/久期, AI产业链价值重分配, or requests to diagnose an industry trend or stock's current market pricing logic."
---

# 君君产业趋势skill

This skill diagnoses what the market is currently paying for: real prosperity, narrative/theme, or a mixture. It is a research and verification framework, not a trading recommendation tool.

Respond in Chinese unless the user asks otherwise. Keep final responsibility with the user; do not give guaranteed-return language or direct buy/sell commands.

## Core Distinction

Always separate these two questions:

1. **Does the company/industry have real prosperity?**
2. **Is the current stock price trading that prosperity, or trading a theme/narrative/liquidity setup?**

Price and volume can support **theme/position-risk** analysis, but they must not be treated as prosperity evidence.

## Default Workflow

1. **Set scope**
   - Identify the company, ticker, market, value-chain node, and time window.
   - If the request is current or stock-specific, use live/available market and financial data where possible. If data tools are unavailable, state which checks need verification.

2. **Build the industry topology**
   - Map upstream resources, materials/equipment/components, modules, systems, and downstream demand.
   - Split broad labels into tradable/observable nodes. For example, do not stop at "光模块"; split into light source, EML, CW light source, LPO/NPO, CPO, PCB/CCL, connectors, testing, and packaging where relevant.
   - Label each node as route-independent, route-dependent, scarce, substitutable, or mainly narrative.

3. **Run the source gate**
   - For each note, roadshow, post, transcript, or report, ask:
     - Is it already-observed data or forward narrative?
     - Is it first-hand, sell-side, buy-side note, self-media, or market rumor?
     - Did data come before price, or did chart/price come before the story?
     - Does it include verifiable quantities such as orders, tons, utilization, shipment, price, customers, capex, delivery time, or certification progress?
     - Is it too clean, too sexy, or too dependent on a single source?
   - Route hard, checkable, cross-confirmed evidence into prosperity scoring. Route soft, remote, single-source, and self-contradictory claims into theme score and red flags.

4. **Locate duration and value pool**
   - Before judging prosperity, mark whether the claim trades 26H2, 2027, 2028, or a longer cycle.
   - For AI/semi chains, ask who is taking too much value, who must give value back, and who recovers certainty after value redistribution.
   - If one component's BOM or operating-cost share becomes too high, check whether downstream users are cutting demand, reducing specs, negotiating long-term prices, changing routes, or delaying capex.

5. **Judge prosperity vs theme**
   - Prosperity signals: earnings acceleration, margin expansion, price pass-through, real shipment/volume, supply scarcity, duration that can cross the near-term cost/capex gap, and orderly value-chain ranking.
   - Theme signals: price far ahead of data, financing/leverage crowding, high turnover, valuation detachment, single-source narrative, forward-only TAM, "unique bottleneck" storytelling without evidence, or profit-pool imbalance.
   - Output a blended judgment such as "景气 6 成 / 主题 4 成" only after explaining the key evidence.

6. **Score quality and position separately**
   - **底子分**: prosperity logic, realization, scarcity, duration match, value-pool health, beta/alpha character, and ranking order.
   - **位置分**: valuation percentile, financing balance, turnover/crowding, institutional vs speculative holders, and liquidity risk.
   - Never let a high valuation alone kill a real prosperity case, and never let a true industry logic excuse weak realization plus crowded money.

7. **Build falsifiable checks**
   - Convert the conclusion into hard variables and failure conditions.
   - Prefer physical or contractual evidence: procurement volume, shipment, utilization, capex orders, long-term contract price, customer orders, delivery time, certification progress, inventory, accounts receivable, and gross margin.
   - Set the observation window, usually the next 1-2 quarters unless the user specifies otherwise.

## AI/Semi Value-Chain Rules

Use these rules when diagnosing AI infrastructure, semiconductors, optical links, PCB/CCL, storage, servers, foundry, or equipment:

- **Value redistribution is not trend death**: an AI correction can mean profits are moving away from an over-earning layer back toward layers that keep capex sustainable.
- **BOM share has a ceiling**: if one layer takes too much of system cost without productivity improvement, downstream will push back through price negotiation, demand cuts, route changes, or capex delay.
- **Separate cabinet-internal and cabinet-external spend**: external cloud storage/peripheral spend can be cut first; core compute, in-cabinet interconnect, and components required for next-generation platforms may be defended.
- **Prioritize duration crossing**: a node that can survive 26H2/2027 cost pressure and still support 2028 platform demand deserves a higher quality score than one that only has a far-future story.

## Storage-Cycle Rules

For memory/storage chains, separate original manufacturers, module makers, server vendors, and downstream users:

- Original manufacturers: focus on near-term price, expansion intent, equipment orders, and long-term contract prices. 2028/2029 expansion promises do not solve a 2027 capex gap.
- Module makers: the first half of an upcycle earns inventory gains; the later stage earns processing fees. Do not annualize one quarter of inventory profit when price second-derivative is slowing or long-term contracts are approaching.
- Server/module intermediaries: rising storage prices can create positive beta; falling expected prices can create amplified negative beta.
- Technology substitution: memory pooling, compression, and KV cache optimization may be directionally valid, but only count for the current cycle if certification, standards, and productization can happen inside the relevant time window.
- Reality test: long-term contract prices, spot/contract price changes, customer capex guidance, and equipment-company guidance decide whether the price/capex issue has been absorbed.

## Output Shape

For a full diagnosis, use this structure:

1. **一句话结论**
2. **信源处理**
3. **久期与价值池**
4. **景气 vs 主题判别**
5. **景气度打分: 底子分 vs 位置分**
6. **怎么验证: 硬变量、证伪条件、观察窗口**
7. **跟踪建议**

For short user requests, compress the structure but keep the separation between prosperity, theme, position, and verification.

## References

Read `references/full-methodology.md` when:

- the user explicitly asks for the complete 君君 method;
- a diagnosis requires the detailed scoring table, source-gate language, or examples;
- the case involves AI value redistribution, storage cycles, capex duration, or "97/久期" analysis;
- you need to align output with the original full instruction manual.
