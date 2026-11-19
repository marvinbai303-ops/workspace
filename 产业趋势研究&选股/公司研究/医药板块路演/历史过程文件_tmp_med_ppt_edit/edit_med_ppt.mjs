import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const INPUT = "/Users/yangguang/Documents/Codex/workspace/选股素材/.tmp_med_ppt_edit/template-starter.pptx";
const OUTPUT = "/Users/yangguang/Documents/Codex/workspace/选股素材/医药板块投资机会_2026vs2025Q3_v2.pptx";
const OUT_DIR = "/Users/yangguang/Documents/Codex/workspace/选股素材/.tmp_med_ppt_edit/final";

const C = {
  white: "#FFFFFF",
  ink: "#101828",
  muted: "#667085",
  panel: "#F2F4F7",
  rule: "#D0D5DD",
  blue: "#2F6BFF",
  blueLight: "#EAF0FF",
  cyan: "#6DCBF4",
  amberLight: "#FFF5DF",
};
const FONT = "STHeiti";

function byName(slide, name) {
  const found = slide.shapes.items.find((item) => item.name === name);
  if (!found) throw new Error(`Missing shape: ${name}`);
  return found;
}

function setText(slide, name, value) {
  byName(slide, name).text = value;
}

const deck = await PresentationFile.importPptx(await FileBlob.load(INPUT));
await fs.mkdir(OUT_DIR, { recursive: true });

const beforeInspect = await deck.inspect({ kind: "slide,textbox,shape,chart,table,notes,layout", maxChars: 30000 });
await fs.writeFile(`${OUT_DIR}/before-inspect.ndjson`, beforeInspect.ndjson);

for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `before-slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1.5 });
  await fs.writeFile(`${OUT_DIR}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${OUT_DIR}/${stem}.layout.json`, await layout.text());
}

// Slide 1: user-specified Davis double play wording.
const slide1 = deck.slides.getItem(0);
setText(slide1, "thesis-1", "行业Beta成立：2026年开始交易盈利与估值的“戴维斯双击”");
slide1.speakerNotes.textFrame.setText(`核心讲法：行业Beta成立之后，2026年不再只是交易产业想象力，而是订单和现金流驱动盈利上修、盈利上修再推动估值抬升的“戴维斯双击”。\n\n[Sources]\n- https://www.nhsa.gov.cn/art/2025/7/1/art_104_17058.html\n- https://www.nhsa.gov.cn/art/2026/4/14/art_53_20215.html\n- https://data.eastmoney.com/report/zw_industry.jshtml?infocode=AP202607051826728220\n- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results\n- https://finance.sina.com.cn/wm/2026-07-13/doc-inihspyt4282488.shtml\n- IMA：嘉实基金郝淼交流，2026-08-21（私域资料）\n[/Sources]`);

// Slide 2: replace the return-only chart with a four-dimensional evidence matrix.
const slide2 = deck.slides.getItem(1);
setText(slide2, "subtitle-2", "持续Alpha不是“涨得多”，而是同时满足：独立于大盘、盈利持续上修、机构资金扩散");
setText(slide2, "chart-caption-2", "四维证据｜为什么2025更像轮动，2026更可能形成持续Alpha");

const oldChart = slide2.charts.items[0];
if (!oldChart) throw new Error("Slide 2 chart not found");
slide2.charts.deleteById(oldChart.id);

const table = slide2.tables.add({
  rows: 5,
  columns: 4,
  left: 42,
  top: 206,
  width: 660,
  height: 405,
  columnWidths: [92, 185, 238, 145],
  values: [
    ["检验", "2025Q3", "2026本轮", "指向"],
    ["市场环境", "沪深300 +20.8%\n医药 +14.9%", "沪深300 -5.6%\n医药 +9.9%", "轮动 → Alpha"],
    ["行情节奏", "CXO 7月 +29.3%\n8–9月降至低个位数", "创新药6–8月连续为正\n+4.5% / +4.8% / +5.9%", "单月 → 延续"],
    ["产业盈利", "政策+BD打开预期\nCXO订单初现拐点", "BD规模约2.1×\n收入+48% / 现金流+41%", "预期 → 兑现"],
    ["机构交易", "主动基金医药仓位\nQ3环比 -0.39pp", "医药总仓位6.54%低位\n但CXO内部占28.2%", "有空间 / 需扩散"],
  ],
});
table.rows[0].height = 43;
for (let r = 1; r < 5; r += 1) table.rows[r].height = 90.5;
table.borders.assign({ style: "solid", fill: C.rule, width: 1 });

const all = table.cells.block({ row: 0, column: 0, rowCount: 5, columnCount: 4 });
all.textStyle.fontSize = 15;
all.textStyle.color = C.ink;
all.textStyle.typeface = FONT;
all.margins = { top: 7, right: 7, bottom: 7, left: 7 };
all.anchor = "middle";

const header = table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 4 });
header.fill = C.ink;
header.textStyle.color = C.white;
header.textStyle.bold = true;
header.textStyle.fontSize = 16;

const firstCol = table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 1 });
firstCol.fill = C.panel;
firstCol.textStyle.bold = true;
firstCol.textStyle.color = C.ink;

const currentCol = table.cells.block({ row: 1, column: 2, rowCount: 4, columnCount: 1 });
currentCol.fill = C.blueLight;
currentCol.textStyle.bold = true;

const meaningCol = table.cells.block({ row: 1, column: 3, rowCount: 4, columnCount: 1 });
meaningCol.fill = C.panel;
meaningCol.textStyle.bold = true;
meaningCol.textStyle.color = C.blue;
meaningCol.textStyle.fontSize = 14;

setText(slide2, "logic-title-1", "① 独立于大盘");
setText(slide2, "logic-main-1", "已满足  ✓");
setText(slide2, "logic-sub-1", "大盘-5.6%，医药+9.9%；超额+15.5pp");
setText(slide2, "logic-title-2", "② 盈利持续上修");
setText(slide2, "logic-main-2", "已满足  ✓");
setText(slide2, "logic-sub-2", "BD翻倍，收入与现金流进入报表");
setText(slide2, "logic-title-3", "③ 机构资金扩散");
setText(slide2, "logic-main-3", "尚待验证  △");
setText(slide2, "logic-sub-3", "总仓位低，但CXO已局部拥挤\n持续性取决于创新药接力");
setText(slide2, "source-2", "来源：同花顺iFinD；国金证券（2026/7/5）；药明康德2026H1；国信证券26Q2；华源证券25Q3");

slide2.speakerNotes.textFrame.setText(`判断2026是否能形成持续Alpha，不能只看阶段涨幅，需要三道检验：\n1. 独立于大盘：已经满足。2025/6—9沪深300上涨20.8%、医药上涨14.9%，医药跑输；2026/6—8.21沪深300下跌5.6%、医药上涨9.9%，形成约15.5个百分点超额。\n2. 盈利持续上修：已经满足。2026H1创新药BD约为2025H1的2.1倍；药明康德持续经营收入增长48%、经营现金流增长41.3%，并上调全年指引。\n3. 机构资金扩散：尚待验证。医药总仓位处于阶段低位，具备增配空间；但现有资金已集中CXO，真正的持续Alpha需要盈利型创新药接力并带动医药总仓位回升。\n\n结论：2026具备比2025更强的产业基础，但“持续Alpha”仍是条件式判断，不是无条件线性外推。\n\n注：2025与2026基金持仓报告样本口径不同，不直接比较绝对仓位，只使用各自报告中的变动方向与内部结构。\n\n[Sources]\n- 同花顺iFinD：000300.SH、000808.CSI、931152.CSI、884244.TI；区间2025-06-01至2025-09-30、2026-06-01至2026-08-21\n- https://www.drugtimes.cn/2025/07/02/chao48448yimeiyuan2025nianshangbannianzhongguochuangxinyaoch/\n- https://data.eastmoney.com/report/zw_industry.jshtml?infocode=AP202607051826728220\n- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results\n- https://data.eastmoney.com/report/info/AP202607301827476211.html\n- https://field.10jqka.com.cn/20251104/c672228873.shtml\n[/Sources]`);

for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `final-slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1.5 });
  await fs.writeFile(`${OUT_DIR}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${OUT_DIR}/${stem}.layout.json`, await layout.text());
}

const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(`${OUT_DIR}/final-montage.webp`, new Uint8Array(await montage.arrayBuffer()));
const afterInspect = await deck.inspect({ kind: "slide,textbox,shape,chart,table,notes,layout", maxChars: 40000 });
await fs.writeFile(`${OUT_DIR}/final-inspect.ndjson`, afterInspect.ndjson);

const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUTPUT);

