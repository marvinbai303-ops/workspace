import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const INPUT = "normalized/2080红利样板间回测模型.xlsx";
const SOURCE_JSON = "source_cached_values.json";
const OUTPUT_DIR = "../outputs/01a05c43_red_dividend_2080";
const OUTPUT_PATH = `${OUTPUT_DIR}/2080红利样板间回测模型_可编辑权重版.xlsx`;
const PREVIEW_DIR = "final_previews_fast";
const FIRST = 42;
const LAST = 1656;
const SOURCE_FIRST = 4;
const SOURCE_LAST = 1618;
const YEARS = [
  [29, 42, 284], [30, 285, 527], [31, 528, 769], [32, 770, 1011],
  [33, 1012, 1253], [34, 1254, 1496], [35, 1497, 1656],
];

function q(name) {
  return `'${name.replaceAll("'", "''")}'`;
}

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  const cached = JSON.parse(await fs.readFile(SOURCE_JSON, "utf8"));
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(INPUT));
  const source = workbook.worksheets.getItem("净值底稿");
  const sheet = workbook.worksheets.getItem("2080回测");

  console.log("恢复用户文件中黄底净值数据…");
  const rows = cached.rows;
  source.getRange(`G${SOURCE_FIRST}:K${SOURCE_LAST}`).clear({ applyTo: "contents" });
  source.getRange(`T${SOURCE_FIRST}:V${SOURCE_LAST}`).clear({ applyTo: "contents" });
  source.getRange(`G${SOURCE_FIRST}:K${SOURCE_LAST}`).values = rows.map((row) => row.slice(1, 6));
  source.getRange(`T${SOURCE_FIRST}:V${SOURCE_LAST}`).values = rows.map((row) => row.slice(6, 9));

  console.log("建立可编辑红利组合净值…");
  source.getRange("W3").values = [["可编辑红利组合归一净值"]];
  source.getRange("W3").format = {
    fill: "#4472C4", font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", wrapText: true,
  };
  source.getRange("W1").format.columnWidth = 20;
  source.getRange(`W${SOURCE_FIRST}:W${SOURCE_LAST}`).formulas = Array.from(
    { length: SOURCE_LAST - SOURCE_FIRST + 1 },
    (_, index) => {
      const row = SOURCE_FIRST + index;
      return [[`=${q("2080回测")}!$O$13*G${row}/$G$${SOURCE_FIRST}+${q("2080回测")}!$O$14*H${row}/$H$${SOURCE_FIRST}+${q("2080回测")}!$O$15*I${row}/$I$${SOURCE_FIRST}+${q("2080回测")}!$O$16*J${row}/$J$${SOURCE_FIRST}+${q("2080回测")}!$O$17*K${row}/$K$${SOURCE_FIRST}`]];
    },
  ).map((row) => row[0]);
  source.getRange(`W${SOURCE_FIRST}:W${SOURCE_LAST}`).format = {
    numberFormat: "0.000000", font: { color: "#000000" },
  };

  console.log("将现有测算页转换为单页红利2080可编辑版…");
  sheet.getRange("A1").values = [["可编辑红利组合｜2080回测模型"]];
  sheet.getRange("A2").formulas = [[`="数据区间："&TEXT($A$42,"yyyy-mm-dd")&" 至 "&TEXT($A$1656,"yyyy-mm-dd")&"｜红利输入：净值底稿 W｜指增/债券/黄金：T/U/V｜净值基准：费后"`]];
  sheet.getRange("A5:A8").values = [["红利组合（可编辑）"], ["指增组合"], ["中债新综合"], ["黄金"]];
  sheet.getRange("B5:B8").values = [[0.10], [0.10], [0.75], [0.05]];
  sheet.getRange("N5").values = [["只需修改下方黄底蓝字的5项红利持仓权重，合计必须为100%。红利组合按起始权重买入并持有；2080外层仍按年末、季末和15%/25%权益阈值触发再平衡，年化费率0.5%。"]];

  sheet.mergeCells("N12:P12");
  sheet.getRange("N12").values = [["红利持仓权重（可编辑）"]];
  sheet.getRange("N12:P12").format = {
    fill: "#4472C4", font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", verticalAlignment: "center",
  };
  sheet.getRange("N13:P17").values = [
    ["红利低波", 0.30, "净值底稿 G列"],
    ["中证红利", 0.30, "净值底稿 H列"],
    ["港股通央企红利", 0.20, "净值底稿 I列"],
    ["徐彦", 0.10, "净值底稿 J列"],
    ["綦缚鹏", 0.10, "净值底稿 K列"],
  ];
  sheet.getRange("N18:P18").values = [["权重合计", null, null]];
  sheet.getRange("O18").formulas = [["=SUM(O13:O17)"]];
  sheet.getRange("P18").formulas = [["=IF(ABS(O18-1)<0.0000001,\"OK\",\"权重需=100%\")"]];
  sheet.mergeCells("N19:P20");
  sheet.getRange("N19").values = [["修改权重后，红利组合净值、2080费后净值、绩效指标和年/月度统计会自动重算。"]];
  sheet.getRange("N13:N18").format = { fill: "#EAF2F8", font: { color: "#2F5597" } };
  sheet.getRange("O13:O17").format = {
    fill: "#FFF2CC", font: { color: "#0000FF", bold: true },
    numberFormat: "0.00%", horizontalAlignment: "right",
  };
  sheet.getRange("O13:O17").dataValidation = {
    rule: { type: "decimal", operator: "between", formula1: 0, formula2: 1 },
  };
  sheet.getRange("O18").format = { fill: "#F2F2F2", font: { bold: true }, numberFormat: "0.00%" };
  sheet.getRange("P13:P17").format = { fill: "#F7F9FB", font: { color: "#666666" } };
  sheet.getRange("P18").format = { fill: "#E2F0D9", font: { bold: true, color: "#2E7D32" }, horizontalAlignment: "center" };
  sheet.getRange("N13:P18").format.borders = { preset: "all", style: "thin", color: "#B4C6E7" };
  sheet.getRange("N19:P20").format = { fill: "#F2F2F2", font: { size: 9, italic: true, color: "#666666" }, wrapText: true };
  sheet.getRange("N1").format.columnWidth = 18;
  sheet.getRange("O1").format.columnWidth = 13;
  sheet.getRange("P1").format.columnWidth = 18;
  sheet.getRange("P18").conditionalFormats.add("containsText", { text: "OK", format: { fill: "#E2F0D9", font: { bold: true, color: "#2E7D32" } } });
  sheet.getRange("P18").conditionalFormats.add("containsText", { text: "100%", format: { fill: "#FCE4D6", font: { bold: true, color: "#C00000" } } });

  sheet.getRange("K8").formulas = [["=IF(AND(ABS($K$5-1)<0.0000001,$K$6,$K$7,ABS($O$18-1)<0.0000001),\"OK\",\"检查参数/数据\")"]];
  sheet.getRange("K13:K18").formulas = [
    ["=$AD$1656/$AD$42-1"],
    ["=AVERAGE($AG$43:$AG$1656)*$H$6"],
    ["=STDEV($AG$43:$AG$1656)*SQRT($H$6)"],
    ["=MIN($AF$42:$AF$1656)"],
    ["=IFERROR((K14-$H$7)/K15,\"\")"],
    ["=IFERROR((POWER($AD$1656/$AD$42,$H$8/($A$1656-$A$42))-1)/ABS(K16),\"\")"],
  ];

  // 只替换四条底层输入；其余逐日调仓公式保留用户模板原式。
  sheet.getRange(`A${FIRST}:E${LAST}`).formulas = Array.from({ length: LAST - FIRST + 1 }, (_, index) => {
    const sourceRow = SOURCE_FIRST + index;
    return [
      `=${q("净值底稿")}!A${sourceRow}`,
      `=${q("净值底稿")}!W${sourceRow}`,
      `=${q("净值底稿")}!T${sourceRow}`,
      `=${q("净值底稿")}!U${sourceRow}`,
      `=${q("净值底稿")}!V${sourceRow}`,
    ];
  });

  // 显式乘法和固定年度行区间，兼容不支持动态数组/MINIFS的旧版 Excel。
  for (const [row, start, end] of YEARS) {
    sheet.getRange(`N${row}`).formulas = [[`=IF(COUNT(B${row}:M${row})=0,"",(1+B${row})*(1+C${row})*(1+D${row})*(1+E${row})*(1+F${row})*(1+G${row})*(1+H${row})*(1+I${row})*(1+J${row})*(1+K${row})*(1+L${row})*(1+M${row})-1)`]];
    sheet.getRange(`P${row}`).formulas = [[`=IF(COUNT($AO$${start}:$AO$${end})=0,"",MIN($AO$${start}:$AO$${end}))`]];
  }
  sheet.getRange("N36:P36").formulas = [[
    "=$AD$1656/$AD$42-1",
    "=IFERROR(COUNTIF($AM$42:$AM$1656,\">0\")/COUNT($AM$42:$AM$1656),\"\")",
    "=MIN($AF$42:$AF$1656)",
  ]];

  sheet.charts.deleteAll();
  const chart = sheet.charts.add("line", {
    title: "可编辑红利组合与红利2080费后净值",
    titleTextStyle: { fontSize: 12, bold: true },
    hasLegend: true,
    legend: { position: "bottom" },
    from: { row: 11, col: 1 },
    extent: { widthPx: 690, heightPx: 300 },
  });
  const sleeve = chart.series.add("红利组合归一净值");
  sleeve.categoryFormula = `${q("2080回测")}!$A$${FIRST}:$A$${LAST}`;
  sleeve.formula = `${q("2080回测")}!$B$${FIRST}:$B$${LAST}`;
  sleeve.line = { fill: "#ED7D31", style: "solid", width: 1.5 };
  const portfolio = chart.series.add("红利2080费后净值");
  portfolio.categoryFormula = `${q("2080回测")}!$A$${FIRST}:$A$${LAST}`;
  portfolio.formula = `${q("2080回测")}!$AD$${FIRST}:$AD$${LAST}`;
  portfolio.line = { fill: "#4472C4", style: "solid", width: 2.5 };
  chart.xAxis = { axisType: "dateAxis", numberFormatCode: "yyyy-mm", textStyle: { fontSize: 8 } };
  chart.yAxis = { numberFormatCode: "0.0000", textStyle: { fontSize: 8 } };
  chart.setPosition("B12", "I24");

  console.log("校验公式与数值…");
  for (const col of ["G", "H", "I", "J", "K", "T", "U", "V"]) {
    const stat = cached.stats[col];
    if (stat.count !== 1615 || stat.missing !== 0 || stat.min <= 0) throw new Error(`净值列 ${col} 不完整`);
  }
  const key = await workbook.inspect({
    kind: "table", range: "2080回测!A4:P36", include: "values,formulas",
    tableMaxRows: 40, tableMaxCols: 18, maxChars: 30000,
  });
  console.log("KEY_CHECK");
  console.log(key.ndjson);
  const errors = await workbook.inspect({
    kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
    options: { useRegex: true, maxResults: 500 }, summary: "final workbook formula error scan",
  });
  console.log("ERROR_SCAN");
  console.log(errors.ndjson);

  console.log("渲染两个保留的用户工作表…");
  const renders = [
    ["净值底稿", "A1:W30", "01_净值底稿.png"],
    ["2080回测", "A1:U40", "02_红利2080可编辑.png"],
  ];
  for (const [name, range, file] of renders) {
    const preview = await workbook.render({ sheetName: name, range, scale: 1.05, format: "png" });
    await fs.writeFile(`${PREVIEW_DIR}/${file}`, new Uint8Array(await preview.arrayBuffer()));
    console.log(`Rendered ${name}`);
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT_PATH);
  console.log(`OUTPUT ${OUTPUT_PATH}`);
}

main().catch((error) => {
  console.error(`FAIL: ${error?.stack ?? error}`);
  process.exitCode = 1;
});
