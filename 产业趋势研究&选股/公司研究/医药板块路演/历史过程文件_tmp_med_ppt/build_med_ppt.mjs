import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUTPUT = "/Users/yangguang/Documents/Codex/workspace/选股素材/医药板块投资机会_2026vs2025Q3.pptx";
const RENDER_DIR = "/Users/yangguang/Documents/Codex/workspace/选股素材/.tmp_med_ppt/rendered";

const C = {
  white: "#FFFFFF",
  ink: "#101828",
  muted: "#667085",
  panel: "#F2F4F7",
  rule: "#D0D5DD",
  blue: "#2F6BFF",
  blueLight: "#EAF0FF",
  cyan: "#6DCBF4",
  teal: "#0E9F8A",
  tealLight: "#E8F7F4",
  amber: "#F59E0B",
  amberLight: "#FFF5DF",
  gray: "#A8B0BD",
  red: "#D92D20",
};

const FONT = "STHeiti";
const W = 1280;
const H = 720;

function addText(slide, name, text, x, y, w, h, opts = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    fontSize: opts.fontSize ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.alignment ?? "left",
    verticalAlignment: opts.verticalAlignment ?? "top",
    autoFit: opts.autoFit ?? "shrinkText",
    wrap: opts.wrap ?? "square",
    insets: opts.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
    typeface: FONT,
    lineSpacing: opts.lineSpacing ?? 0.95,
  };
  return box;
}

function addPanel(slide, name, x, y, w, h, fill = C.panel, lineFill = "none", radius = 12) {
  return slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: lineFill, width: lineFill === "none" ? 0 : 1 },
    borderRadius: radius,
  });
}

function addLine(slide, name, x, y, w, h = 0, color = C.rule, width = 1) {
  return slide.shapes.add({
    geometry: "line",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: color, width },
  });
}

function addHeader(slide, title, kicker, page) {
  addText(slide, `kicker-${page}`, kicker, 48, 25, 520, 22, {
    fontSize: 15,
    bold: true,
    color: C.blue,
  });
  addText(slide, `title-${page}`, title, 48, 52, 1184, 58, {
    fontSize: 48,
    bold: true,
    color: C.ink,
    wrap: "none",
  });
  addLine(slide, `accent-${page}`, 48, 122, 92, 0, C.blue, 5);
}

function addFooter(slide, sourceText, page) {
  addLine(slide, `footer-rule-${page}`, 48, 651, 1184, 0, C.rule, 1);
  addText(slide, `source-${page}`, sourceText, 48, 660, 1115, 28, {
    fontSize: 11.5,
    color: C.muted,
    verticalAlignment: "top",
  });
  addText(slide, `page-${page}`, String(page).padStart(2, "0"), 1180, 660, 52, 24, {
    fontSize: 13,
    bold: true,
    color: C.muted,
    alignment: "right",
  });
}

function addMetric(slide, name, value, label, x, y, w, color) {
  addText(slide, `${name}-value`, value, x, y, w, 54, {
    fontSize: 43,
    bold: true,
    color,
  });
  addText(slide, `${name}-label`, label, x, y + 59, w, 48, {
    fontSize: 18,
    color: C.muted,
  });
}

const deck = Presentation.create({ slideSize: { width: W, height: H } });

// Slide 1 — process / timeline composition inspired by Codex Grid slide 18.
{
  const slide = deck.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "医药正在从估值修复走向盈利周期", "医药板块投资机会｜2026年8月", 1);
  addText(slide, "subtitle-1", "创新资产全球化，正在形成“BD回款—研发投入—CXO订单—利润兑现”的正循环", 48, 137, 1184, 34, {
    fontSize: 23,
    color: C.muted,
  });

  // Arrows first, then nodes.
  addText(slide, "arrow-1", "→", 399, 315, 50, 48, { fontSize: 42, bold: true, color: C.blue, alignment: "center" });
  addText(slide, "arrow-2", "→", 811, 315, 50, 48, { fontSize: 42, bold: true, color: C.blue, alignment: "center" });

  const xs = [48, 460, 872];
  const ws = 360;
  xs.forEach((x, i) => addPanel(slide, `stage-panel-${i + 1}`, x, 188, ws, 330, i === 1 ? C.blueLight : C.panel));

  addText(slide, "stage1-head", "① 资产重估", 75, 214, 300, 34, { fontSize: 24, bold: true, color: C.blue });
  addMetric(slide, "stage1-metric", "997亿美元", "2026H1中国创新药BD\n约为2025全年交易额的73%", 75, 267, 300, C.ink);
  addLine(slide, "stage1-rule", 75, 398, 300, 0, C.rule, 1);
  addText(slide, "stage1-meaning", "中国创新资产\n从“可选”变为“必选”", 75, 420, 300, 64, { fontSize: 22, bold: true, color: C.ink });

  addText(slide, "stage2-head", "② 现金回流", 487, 214, 300, 34, { fontSize: 24, bold: true, color: C.blue });
  addMetric(slide, "stage2-metric", "≈60亿美元", "2026H1 BD首付款\n同比增长超过100%", 487, 267, 300, C.blue);
  addLine(slide, "stage2-rule", 487, 398, 300, 0, "#AFC3FF", 1);
  addText(slide, "stage2-meaning", "授权收入改善现金流\n并反哺下一轮研发", 487, 420, 300, 64, { fontSize: 22, bold: true, color: C.ink });

  addText(slide, "stage3-head", "③ 盈利兑现", 899, 214, 300, 34, { fontSize: 24, bold: true, color: C.teal });
  addMetric(slide, "stage3-metric", "664亿元", "药明康德持续经营业务在手订单\n同比增长25.2%", 899, 267, 300, C.teal);
  addLine(slide, "stage3-rule", 899, 398, 300, 0, C.rule, 1);
  addText(slide, "stage3-meaning", "持续经营收入 +48%\n经营现金流 +41.3%", 899, 420, 300, 64, { fontSize: 22, bold: true, color: C.ink });

  addPanel(slide, "thesis-banner-1", 48, 545, 1184, 78, C.ink, "none", 8);
  addText(slide, "thesis-1", "行业Beta成立：2025交易“想象空间”，2026开始交易“盈利周期”", 77, 565, 1126, 40, {
    fontSize: 28,
    bold: true,
    color: C.white,
    alignment: "center",
    verticalAlignment: "middle",
  });

  addFooter(slide, "来源：国家医保局；国金证券（2026/7/5）；药明康德2026H1；浙商证券（2026/7/13）；IMA嘉实郝淼交流（2026/8/21）", 1);
  slide.speakerNotes.textFrame.setText(`核心讲法：2025年政策和BD解决的是“有没有全球价值”；2026年订单、利润和现金流开始回答“价值如何进入报表”。\n\n[Sources]\n- https://www.nhsa.gov.cn/art/2025/7/1/art_104_17058.html\n- https://www.nhsa.gov.cn/art/2026/4/14/art_53_20215.html\n- https://data.eastmoney.com/report/zw_industry.jshtml?infocode=AP202607051826728220\n- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results\n- https://finance.sina.com.cn/wm/2026-07-13/doc-inihspyt4282488.shtml\n- IMA：嘉实基金郝淼交流，2026-08-21（私域资料）\n[/Sources]`);
}

// Slide 2 — chart-led evidence inspired by Codex Grid slide 20.
{
  const slide = deck.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "2026年医药行情大概率强于2025年Q3", "历史类比｜产业、市场与机构交易", 2);
  addText(slide, "subtitle-2", "2025是风险偏好中的板块轮动；2026是在弱指数环境中走出的独立Alpha", 48, 137, 1184, 32, {
    fontSize: 23,
    color: C.muted,
  });
  addText(slide, "chart-caption-2", "区间涨跌幅（%）｜仅作为行情形态旁证", 52, 178, 620, 26, { fontSize: 17, bold: true, color: C.muted });

  slide.charts.add("bar", {
    position: { left: 42, top: 206, width: 660, height: 405 },
    categories: ["沪深300", "医药生物", "创新药", "CXO"],
    series: [
      { name: "2025/6–9", categories: ["沪深300", "医药生物", "创新药", "CXO"], values: [20.8, 14.9, 22.3, 44.2], fill: C.gray, valuesFormatCode: "0.0" },
      { name: "2026/6–8.21", categories: ["沪深300", "医药生物", "创新药", "CXO"], values: [-5.6, 9.9, 16.0, 41.9], fill: C.blue, valuesFormatCode: "0.0" },
    ],
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fontSize: 14, fill: C.muted, typeface: FONT } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 13, bold: true, fill: C.ink, typeface: FONT } },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: {
      visible: true,
      line: { style: "solid", width: 1, fill: C.rule },
      textStyle: { typeface: FONT, fontSize: 15, fill: C.ink },
    },
    yAxis: {
      visible: true,
      min: -10,
      max: 50,
      majorUnit: 10,
      numberFormatCode: "0",
      majorGridlines: { style: "solid", width: 1, fill: "#E9ECF0" },
      line: { style: "solid", width: 0, fill: C.white },
      textStyle: { typeface: FONT, fontSize: 12, fill: C.muted },
    },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 80 },
  });

  addPanel(slide, "logic-card-1", 742, 184, 490, 122, C.panel);
  addText(slide, "logic-title-1", "① 行情独立性", 770, 205, 210, 28, { fontSize: 21, bold: true, color: C.blue });
  addText(slide, "logic-main-1", "沪深300 -5.6%  vs  CXO +41.9%", 770, 241, 425, 32, { fontSize: 25, bold: true, color: C.ink });
  addText(slide, "logic-sub-1", "本轮首先是产业Alpha，而非牛市轮动", 770, 278, 425, 20, { fontSize: 16, color: C.muted });

  addPanel(slide, "logic-card-2", 742, 323, 490, 122, C.blueLight);
  addText(slide, "logic-title-2", "② 产业兑现度", 770, 344, 210, 28, { fontSize: 21, bold: true, color: C.blue });
  addText(slide, "logic-main-2", "997亿美元BD  +  664亿元订单", 770, 380, 425, 32, { fontSize: 25, bold: true, color: C.ink });
  addText(slide, "logic-sub-2", "预期开始向收入、利润和现金流传导", 770, 417, 425, 20, { fontSize: 16, color: C.muted });

  addPanel(slide, "logic-card-3", 742, 462, 490, 149, C.ink);
  addText(slide, "logic-title-3", "③ 机构结构", 770, 483, 210, 28, { fontSize: 21, bold: true, color: C.cyan });
  addText(slide, "logic-main-3", "医药仓位6.54%｜内部CXO占28.2%", 770, 519, 425, 32, { fontSize: 24, bold: true, color: C.white });
  addText(slide, "logic-sub-3", "板块仍有增配空间，但CXO已局部拥挤\n→ 超越2025需要创新药接力", 770, 556, 425, 44, { fontSize: 17, bold: true, color: "#E4E7EC" });

  addFooter(slide, "来源：同花顺iFinD（2025/6/1–9/30；2026/6/1–8/21）；国信证券26Q2基金持仓；华源证券25Q3基金持仓", 2);
  slide.speakerNotes.textFrame.setText(`结论不是“2026涨得更多”，而是本轮行情的驱动力更独立、兑现度更高。2025年医药整体跑输大盘，CXO在7月完成快速补涨；2026年大盘走弱时医药仍产生超额收益。\n\n注：2025与2026基金持仓报告样本口径不同，PPT不将绝对仓位直接横比，只使用各自报告中的方向与结构。\n\n[Sources]\n- 同花顺iFinD：000300.SH、000808.CSI、931152.CSI、884244.TI；区间为2025-06-01至2025-09-30、2026-06-01至2026-08-21\n- https://data.eastmoney.com/report/info/AP202607301827476211.html\n- https://field.10jqka.com.cn/20251104/c672228873.shtml\n[/Sources]`);
}

// Slide 3 — paired comparison inspired by Codex Grid slide 11.
{
  const slide = deck.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "CXO定胜率，创新药决定行情上限", "配置结论｜胜率与赔率分工", 3);
  addText(slide, "subtitle-3", "当前更适合“CXO做底仓、创新药做增量”，而不是继续追逐单一赛道斜率", 48, 137, 1184, 32, {
    fontSize: 23,
    color: C.muted,
  });

  addPanel(slide, "cxo-panel", 48, 184, 565, 250, C.blueLight);
  addText(slide, "cxo-head", "CXO｜更高胜率", 76, 206, 300, 34, { fontSize: 27, bold: true, color: C.blue });
  addText(slide, "cxo-value1", "664亿元", 76, 256, 210, 54, { fontSize: 43, bold: true, color: C.ink });
  addText(slide, "cxo-label1", "在手订单｜同比 +25.2%", 76, 310, 250, 26, { fontSize: 17, color: C.muted });
  addText(slide, "cxo-value2", "35.4×", 342, 256, 210, 54, { fontSize: 43, bold: true, color: C.blue });
  addText(slide, "cxo-label2", "PE｜2025/9约36.8×", 342, 310, 225, 26, { fontSize: 17, color: C.muted });
  addLine(slide, "cxo-rule", 76, 354, 509, 0, "#B8C8FF", 1);
  addText(slide, "cxo-bottom", "收入、订单、现金流均已验证\n但PE处于近一年约82%分位", 76, 373, 480, 48, { fontSize: 19, bold: true, color: C.ink });

  addPanel(slide, "drug-panel", 667, 184, 565, 250, C.amberLight);
  addText(slide, "drug-head", "创新药｜更高赔率", 695, 206, 300, 34, { fontSize: 27, bold: true, color: C.amber });
  addText(slide, "drug-value1", "997亿美元", 695, 256, 235, 54, { fontSize: 43, bold: true, color: C.ink });
  addText(slide, "drug-label1", "2026H1 BD｜2025全年73%", 695, 310, 265, 26, { fontSize: 17, color: C.muted });
  addText(slide, "drug-value2", "50.4×", 978, 256, 210, 54, { fontSize: 43, bold: true, color: C.amber });
  addText(slide, "drug-label2", "PE｜2025/9约58×", 978, 310, 220, 26, { fontSize: 17, color: C.muted });
  addLine(slide, "drug-rule", 695, 354, 509, 0, "#F5D28C", 1);
  addText(slide, "drug-bottom", "估值尚未回到2025高点\n盈利型资产有望承接下一棒", 695, 373, 480, 48, { fontSize: 19, bold: true, color: C.ink });

  addText(slide, "score-caption", "研究框架评分（5分制）", 55, 455, 300, 26, { fontSize: 17, bold: true, color: C.muted });
  slide.charts.add("bar", {
    position: { left: 48, top: 480, width: 760, height: 155 },
    categories: ["盈利确定性", "短期拥挤度", "中期赔率"],
    series: [
      { name: "CXO", categories: ["盈利确定性", "短期拥挤度", "中期赔率"], values: [5, 4, 3], fill: C.blue },
      { name: "创新药", categories: ["盈利确定性", "短期拥挤度", "中期赔率"], values: [3, 2, 5], fill: C.amber },
    ],
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fontSize: 13, fill: C.muted, typeface: FONT } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 12, bold: true, fill: C.ink, typeface: FONT } },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: { visible: true, min: 0, max: 5, majorUnit: 1, majorGridlines: { style: "solid", width: 1, fill: "#E9ECF0" }, line: { style: "solid", width: 0, fill: C.white }, textStyle: { fontSize: 11, fill: C.muted, typeface: FONT } },
    yAxis: { visible: true, line: { style: "solid", width: 0, fill: C.white }, textStyle: { fontSize: 14, fill: C.ink, typeface: FONT } },
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 60 },
  });

  addPanel(slide, "final-banner", 842, 478, 390, 157, C.ink, "none", 10);
  addText(slide, "final-banner-kicker", "本轮能否超过2025", 870, 501, 335, 27, { fontSize: 18, bold: true, color: C.cyan });
  addText(slide, "final-banner-main", "取决于创新药\n能否接力CXO", 870, 535, 335, 62, { fontSize: 31, bold: true, color: C.white });
  addText(slide, "final-banner-sub", "CXO持有、不追斜率；增量关注盈利与数据催化", 870, 605, 335, 20, { fontSize: 14.5, color: "#E4E7EC" });

  addFooter(slide, "来源：同花顺iFinD（估值截至2026/8/21）；药明康德2026H1；国金证券（2026/7/5）；浙商证券（2026/7/13）。评分为研究判断", 3);
  slide.speakerNotes.textFrame.setText(`配置判断：未来6—12个月，CXO仍具备更高的盈利确定性，但估值和交易拥挤度已经明显修复；创新药的胜率低于CXO，但相对估值位置和事件弹性更好。\n\n“研究框架评分”为基于产业兑现、估值位置和交易拥挤度的定性判断，仅用于比较，不是收益预测。\n\n[Sources]\n- 同花顺iFinD：931152.CSI、884244.TI，估值截至2026-08-21\n- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results\n- https://data.eastmoney.com/report/zw_industry.jshtml?infocode=AP202607051826728220\n- https://finance.sina.com.cn/wm/2026-07-13/doc-inihspyt4282488.shtml\n[/Sources]`);
}

await fs.mkdir(RENDER_DIR, { recursive: true });
for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1.5 });
  await fs.writeFile(`${RENDER_DIR}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${RENDER_DIR}/${stem}.layout.json`, await layout.text());
}

const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(`${RENDER_DIR}/deck-montage.webp`, new Uint8Array(await montage.arrayBuffer()));
const inspect = await deck.inspect({ kind: "slide,textbox,shape,chart,notes", maxChars: 20000 });
await fs.writeFile(`${RENDER_DIR}/deck-inspect.ndjson`, inspect.ndjson);

const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUTPUT);

