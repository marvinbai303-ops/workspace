import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const INPUT = "normalized/2080红利样板间回测模型.xlsx";
const SOURCE_JSON = "source_cached_values.json";
const OUTPUT_DIR = "../outputs/01a05c43_red_dividend_2080";
const OUTPUT_PATH = `${OUTPUT_DIR}/2080红利样板间回测模型_可编辑权重版.xlsx`;
const PREVIEW_DIR = "final_previews";
const FIRST_DATA_ROW = 42;
const LAST_DATA_ROW = 1656;
const SOURCE_FIRST_ROW = 4;
const SOURCE_LAST_ROW = 1618;

const schemes = [
  { id: "可编辑", short: "红利组合", sheet: "红利2080可编辑", helperCol: "W", weights: [0.3, 0.3, 0.2, 0.1, 0.1], composition: "默认：30%红利低波 + 30%中证红利 + 20%港股通央企红利 + 10%徐彦 + 10%綦缚鹏；可自由修改" },
];

const componentCols = ["G", "H", "I", "J", "K"];
const configWeightCols = ["AG", "AH", "AI", "AJ", "AK"];
const yearDrawdownBounds = [
  [42, 284], [285, 527], [528, 769], [770, 1011],
  [1012, 1253], [1254, 1496], [1497, 1656],
];
const mergeRanges = [
  "A1:U1", "A2:U2", "A4:B4", "D4:E4", "G4:H4", "J4:U4",
  "A39:AQ39", "A40:AQ40", "J19:K19", "J12:K12", "N5:U8",
  "A10:U10", "A27:P27", "B25:K25",
];

function escapeSheet(name) {
  return `'${name.replaceAll("'", "''")}'`;
}

function buildDailyFormulas(groupCol) {
  const formulas = [];
  for (let row = FIRST_DATA_ROW; row <= LAST_DATA_ROW; row += 1) {
    const sourceRow = SOURCE_FIRST_ROW + row - FIRST_DATA_ROW;
    const next = row + 1;
    if (row === FIRST_DATA_ROW) {
      formulas.push([
        `=${escapeSheet("净值底稿")}!A${sourceRow}`,
        `=${escapeSheet("净值底稿")}!${groupCol}${sourceRow}`,
        `=${escapeSheet("净值底稿")}!T${sourceRow}`,
        `=${escapeSheet("净值底稿")}!U${sourceRow}`,
        `=${escapeSheet("净值底稿")}!V${sourceRow}`,
        "=0", "=0", "=0", "=0",
        "=$B$5", "=$B$6", "=$B$7", "=$B$8",
        `=SUM(J${row}:M${row})`,
        `=IFERROR((J${row}+K${row})/N${row},0)`,
        `=AND(MONTH(A${row})=12,OR(A${next}=\"\",YEAR(A${row})<>YEAR(A${next})))`,
        `=AND(MOD(MONTH(A${row}),3)=0,OR(A${next}=\"\",MONTH(A${row})<>MONTH(A${next})))`,
        `=OR(O${row}>$E$7,O${row}<$E$6)`,
        "=FALSE()",
        `=\"初始配置\"`,
        `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\"),N${row}*$E$5/2,IF(T${row}=\"季度\",(J${row}+K${row})/2,IF(T${row}=\"动态\",N${row}*$E$5*IF(J${row}+K${row}=0,0.5,J${row}/(J${row}+K${row})),J${row})))`,
        `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\"),N${row}*$E$5/2,IF(T${row}=\"季度\",(J${row}+K${row})/2,IF(T${row}=\"动态\",N${row}*$E$5*IF(J${row}+K${row}=0,0.5,K${row}/(J${row}+K${row})),K${row})))`,
        `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\",T${row}=\"动态\"),N${row}*(1-$E$5)*IF(L${row}+M${row}=0,$B$7/($B$7+$B$8),L${row}/(L${row}+M${row})),L${row})`,
        `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\",T${row}=\"动态\"),N${row}*(1-$E$5)*IF(L${row}+M${row}=0,$B$8/($B$7+$B$8),M${row}/(L${row}+M${row})),M${row})`,
        "=1",
        `=U${row}*Y${row}`, `=V${row}*Y${row}`, `=W${row}*Y${row}`, `=X${row}*Y${row}`,
        `=SUM(Z${row}:AC${row})`,
        `=AD${row}`,
        `=AD${row}/AE${row}-1`,
        "=0",
        `=A${row}`,
        `=YEAR(A${row})`,
        `=MONTH(A${row})`,
        `=IF(MONTH(A${row})<>MONTH(A${next}),1,0)`,
        `=AD${row}`,
        `=IF(AK${row},AD${row}/AL${row}-1,\"\")`,
        `=AD${row}`,
        `=AD${row}/AN${row}-1`,
        `=IFERROR(SUM(Z${row}:AC${row})/AD${row},0)`,
        `=AND(B${row}>0,C${row}>0,D${row}>0,E${row}>0)`,
        `=DATE(YEAR($A$${FIRST_DATA_ROW}),MONTH($A$${FIRST_DATA_ROW}),1)`,
        `=TEXT(AR${row},\"yyyy-mm\")`,
        `=IF(AR${row}>DATE(YEAR($A$${LAST_DATA_ROW}),MONTH($A$${LAST_DATA_ROW}),1),\"\",SUMIFS($AD$${FIRST_DATA_ROW}:$AD$${LAST_DATA_ROW},$AI$${FIRST_DATA_ROW}:$AI$${LAST_DATA_ROW},YEAR(AR${row}),$AJ$${FIRST_DATA_ROW}:$AJ$${LAST_DATA_ROW},MONTH(AR${row}),$AK$${FIRST_DATA_ROW}:$AK$${LAST_DATA_ROW},1))`,
      ]);
      continue;
    }

    const previous = row - 1;
    formulas.push([
      `=${escapeSheet("净值底稿")}!A${sourceRow}`,
      `=${escapeSheet("净值底稿")}!${groupCol}${sourceRow}`,
      `=${escapeSheet("净值底稿")}!T${sourceRow}`,
      `=${escapeSheet("净值底稿")}!U${sourceRow}`,
      `=${escapeSheet("净值底稿")}!V${sourceRow}`,
      `=IFERROR(B${row}/B${previous}-1,0)`,
      `=IFERROR(C${row}/C${previous}-1,0)`,
      `=IFERROR(D${row}/D${previous}-1,0)`,
      `=IFERROR(E${row}/E${previous}-1,0)`,
      `=Z${previous}*(1+F${row})`,
      `=AA${previous}*(1+G${row})`,
      `=AB${previous}*(1+H${row})`,
      `=AC${previous}*(1+I${row})`,
      `=SUM(J${row}:M${row})`,
      `=IFERROR((J${row}+K${row})/N${row},0)`,
      `=AND(MONTH(A${row})=12,OR(A${next}=\"\",YEAR(A${row})<>YEAR(A${next})))`,
      `=AND(MOD(MONTH(A${row}),3)=0,OR(A${next}=\"\",MONTH(A${row})<>MONTH(A${next})))`,
      `=OR(O${row}>$E$7,O${row}<$E$6)`,
      `=AND(OR(P${row},Q${row},R${row}),A${row}-AH${previous}>$E$8)`,
      `=IF(NOT(OR(P${row},Q${row},R${row})),\"不调\",IF(NOT(S${row}),\"间隔规则跳过\",IF(P${row},\"年末+季度\",IF(AND(Q${row},R${row}),\"季度+动态\",IF(Q${row},\"季度\",\"动态\")))))`,
      `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\"),N${row}*$E$5/2,IF(T${row}=\"季度\",(J${row}+K${row})/2,IF(T${row}=\"动态\",N${row}*$E$5*IF(J${row}+K${row}=0,0.5,J${row}/(J${row}+K${row})),J${row})))`,
      `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\"),N${row}*$E$5/2,IF(T${row}=\"季度\",(J${row}+K${row})/2,IF(T${row}=\"动态\",N${row}*$E$5*IF(J${row}+K${row}=0,0.5,K${row}/(J${row}+K${row})),K${row})))`,
      `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\",T${row}=\"动态\"),N${row}*(1-$E$5)*IF(L${row}+M${row}=0,$B$7/($B$7+$B$8),L${row}/(L${row}+M${row})),L${row})`,
      `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\",T${row}=\"动态\"),N${row}*(1-$E$5)*IF(L${row}+M${row}=0,$B$8/($B$7+$B$8),M${row}/(L${row}+M${row})),M${row})`,
      `=POWER(1-$H$5,(A${row}-A${previous})/$H$8)`,
      `=U${row}*Y${row}`, `=V${row}*Y${row}`, `=W${row}*Y${row}`, `=X${row}*Y${row}`,
      `=SUM(Z${row}:AC${row})`,
      `=MAX(AE${previous},AD${row})`,
      `=AD${row}/AE${row}-1`,
      `=AD${row}/AD${previous}-1`,
      `=IF(OR(T${row}=\"年末+季度\",T${row}=\"季度+动态\",T${row}=\"季度\",T${row}=\"动态\"),A${row},AH${previous})`,
      `=YEAR(A${row})`,
      `=MONTH(A${row})`,
      `=IF(MONTH(A${row})<>MONTH(A${next}),1,0)`,
      `=IF(AK${previous},AD${previous},AL${previous})`,
      `=IF(AK${row},AD${row}/AL${row}-1,\"\")`,
      `=IF(AI${row}<>AI${previous},AD${row},MAX(AN${previous},AD${row}))`,
      `=AD${row}/AN${row}-1`,
      `=IFERROR(SUM(Z${row}:AC${row})/AD${row},0)`,
      `=AND(B${row}>0,C${row}>0,D${row}>0,E${row}>0)`,
      `=EDATE(AR${previous},1)`,
      `=TEXT(AR${row},\"yyyy-mm\")`,
      `=IF(AR${row}>DATE(YEAR($A$${LAST_DATA_ROW}),MONTH($A$${LAST_DATA_ROW}),1),\"\",SUMIFS($AD$${FIRST_DATA_ROW}:$AD$${LAST_DATA_ROW},$AI$${FIRST_DATA_ROW}:$AI$${LAST_DATA_ROW},YEAR(AR${row}),$AJ$${FIRST_DATA_ROW}:$AJ$${LAST_DATA_ROW},MONTH(AR${row}),$AK$${FIRST_DATA_ROW}:$AK$${LAST_DATA_ROW},1))`,
    ]);
  }
  return formulas;
}

function applyColumnWidths(sheet) {
  const widths = {
    A: 13, B: 13, C: 13, D: 13, E: 13, F: 13, G: 13, H: 13, I: 13,
    J: 14.90625, K: 13, L: 13, M: 13, N: 13, O: 13, P: 13,
    Q: 20, R: 13, S: 34, T: 13, U: 13, V: 13, W: 13, X: 13,
    Y: 13, Z: 13, AA: 13, AB: 13, AC: 13, AD: 13, AE: 13, AF: 13,
    AG: 13, AH: 13, AI: 13, AJ: 13, AK: 13, AL: 13, AM: 13, AN: 13,
    AO: 13, AP: 13, AQ: 13, AR: 12, AS: 12, AT: 12,
  };
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}1`).format.columnWidth = width;
  }
}

function applyDailyFormatting(sheet) {
  sheet.getRange(`A${FIRST_DATA_ROW}:AT${LAST_DATA_ROW}`).format = {
    font: { name: "宋体", size: 9, color: "#000000" },
    verticalAlignment: "center",
  };
  sheet.getRange(`A${FIRST_DATA_ROW}:E${LAST_DATA_ROW}`).format.font = { name: "宋体", size: 9, color: "#008000" };
  sheet.getRange(`A${FIRST_DATA_ROW}:A${LAST_DATA_ROW}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`B${FIRST_DATA_ROW}:E${LAST_DATA_ROW}`).format.numberFormat = "0.000000";
  sheet.getRange(`F${FIRST_DATA_ROW}:I${LAST_DATA_ROW}`).format.numberFormat = "0.000%";
  sheet.getRange(`J${FIRST_DATA_ROW}:N${LAST_DATA_ROW}`).format.numberFormat = "0.000000";
  sheet.getRange(`O${FIRST_DATA_ROW}:O${LAST_DATA_ROW}`).format.numberFormat = "0.00%";
  sheet.getRange(`U${FIRST_DATA_ROW}:AE${LAST_DATA_ROW}`).format.numberFormat = "0.000000";
  sheet.getRange(`AF${FIRST_DATA_ROW}:AG${LAST_DATA_ROW}`).format.numberFormat = "0.000%";
  sheet.getRange(`AH${FIRST_DATA_ROW}:AH${LAST_DATA_ROW}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`AM${FIRST_DATA_ROW}:AM${LAST_DATA_ROW}`).format.numberFormat = "0.00%;[Red](0.00%);-";
  sheet.getRange(`AO${FIRST_DATA_ROW}:AP${LAST_DATA_ROW}`).format.numberFormat = "0.00%;[Red](0.00%);-";
  sheet.getRange(`AR${FIRST_DATA_ROW}:AR${LAST_DATA_ROW}`).format.numberFormat = "yyyy-mm";
  sheet.getRange(`AT${FIRST_DATA_ROW}:AT${LAST_DATA_ROW}`).format.numberFormat = "0.0000";
}

function addDetailChart(sheet, scheme) {
  const chart = sheet.charts.add("line", {
    title: "可编辑红利组合与红利2080费后净值",
    titleTextStyle: { fontSize: 12, bold: true },
    hasLegend: true,
    legend: { position: "bottom" },
    from: { row: 11, col: 1 },
    extent: { widthPx: 690, heightPx: 300 },
  });
  const sleeve = chart.series.add("红利组合归一净值");
  sleeve.categoryFormula = `${escapeSheet(sheet.name)}!$A$${FIRST_DATA_ROW}:$A$${LAST_DATA_ROW}`;
  sleeve.formula = `${escapeSheet(sheet.name)}!$B$${FIRST_DATA_ROW}:$B$${LAST_DATA_ROW}`;
  sleeve.line = { fill: "#ED7D31", style: "solid", width: 1.5 };
  const portfolio = chart.series.add("红利2080费后净值");
  portfolio.categoryFormula = `${escapeSheet(sheet.name)}!$A$${FIRST_DATA_ROW}:$A$${LAST_DATA_ROW}`;
  portfolio.formula = `${escapeSheet(sheet.name)}!$AD$${FIRST_DATA_ROW}:$AD$${LAST_DATA_ROW}`;
  portfolio.line = { fill: "#4472C4", style: "solid", width: 2.5 };
  chart.xAxis = { axisType: "dateAxis", numberFormatCode: "yyyy-mm", textStyle: { fontSize: 8 } };
  chart.yAxis = { numberFormatCode: "0.0000", textStyle: { fontSize: 8 } };
  chart.setPosition("B12", "I24");
}

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  const cached = JSON.parse(await fs.readFile(SOURCE_JSON, "utf8"));
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(INPUT));
  const source = workbook.worksheets.getItem("净值底稿");
  const template = workbook.worksheets.getItem("2080回测");
  workbook.worksheets.add(schemes[0].sheet);

  console.log("Restoring the eight yellow source series from the user's cached values...");
  const sourceRows = cached.rows;
  source.getRange(`G${SOURCE_FIRST_ROW}:K${SOURCE_LAST_ROW}`).values = sourceRows.map((row) => row.slice(1, 6));
  source.getRange(`T${SOURCE_FIRST_ROW}:V${SOURCE_LAST_ROW}`).values = sourceRows.map((row) => row.slice(6, 9));

  source.getRange("W3").values = [["可编辑红利组合归一净值"]];
  source.getRange("AF3:AK3").values = [["方案", "红利低波", "中证红利", "港股央企红利", "徐彦", "綦缚鹏"]];
  source.getRange("AF4:AK4").formulas = [[
    `=${escapeSheet(schemes[0].sheet)}!$A$5`,
    `=${escapeSheet(schemes[0].sheet)}!$O$13`,
    `=${escapeSheet(schemes[0].sheet)}!$O$14`,
    `=${escapeSheet(schemes[0].sheet)}!$O$15`,
    `=${escapeSheet(schemes[0].sheet)}!$O$16`,
    `=${escapeSheet(schemes[0].sheet)}!$O$17`,
  ]];
  source.getRange("AF13:AK14").merge();
  source.getRange("AF13").values = [["红利组合口径：五条黄色底层净值自2020-01-02起归一化，按方案初始权重买入并持有，组内不另做定期再平衡。"]];

  const groupFormulas = [];
  for (let row = SOURCE_FIRST_ROW; row <= SOURCE_LAST_ROW; row += 1) {
    groupFormulas.push([`=${componentCols.map((column, componentIndex) => `${escapeSheet(schemes[0].sheet)}!$O$${13 + componentIndex}*${column}${row}/$${column}$${SOURCE_FIRST_ROW}`).join("+")}`]);
  }
  source.getRange(`W${SOURCE_FIRST_ROW}:W${SOURCE_LAST_ROW}`).formulas = groupFormulas;
  source.getRange("W3").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
  source.getRange(`W${SOURCE_FIRST_ROW}:W${SOURCE_LAST_ROW}`).format = { numberFormat: "0.0000", font: { color: "#000000" } };
  source.getRange("AF3:AK3").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
  source.getRange("AG4:AK4").format = { fill: "#FFF2CC", font: { color: "#008000" }, numberFormat: "0%", horizontalAlignment: "center" };
  source.getRange("AF4").format = { fill: "#EAF2F8", font: { bold: true, color: "#008000" }, horizontalAlignment: "center" };
  source.getRange("AF13:AK14").format = { fill: "#F2F2F2", font: { italic: true, color: "#666666" }, wrapText: true, verticalAlignment: "center" };
  source.getRange("AF13:AK14").format.rowHeight = 28;
  source.getRange("W1").format.columnWidth = 18;
  source.getRange("AF1").format.columnWidth = 10;
  for (const col of configWeightCols) source.getRange(`${col}1`).format.columnWidth = 14;

  console.log("Normalizing the existing industry-trend reference sheet for old Excel compatibility...");
  template.getRange("A2").formulas = [[`=\"数据区间：\"&TEXT($A$42,\"yyyy-mm-dd\")&\" 至 \"&TEXT($A$1656,\"yyyy-mm-dd\")&\"｜输入列：净值底稿 F / T / U / V｜净值基准：费后\"`]];
  template.getRange("A42:E1656").formulas = Array.from({ length: 1615 }, (_, index) => {
    const sourceRow = 4 + index;
    return [
      `=${escapeSheet("净值底稿")}!A${sourceRow}`, `=${escapeSheet("净值底稿")}!F${sourceRow}`,
      `=${escapeSheet("净值底稿")}!T${sourceRow}`, `=${escapeSheet("净值底稿")}!U${sourceRow}`,
      `=${escapeSheet("净值底稿")}!V${sourceRow}`,
    ];
  });
  template.getRange("K15").formulas = [["=STDEV($AG$43:$AG$1656)*SQRT($H$6)"]];

  console.log("Creating the editable red-dividend 2080 sheet...");

  for (const scheme of schemes) {
    const sheet = workbook.worksheets.getItem(scheme.sheet);
    sheet.showGridLines = false;
    sheet.getRange("A1:U40").copyFrom(template.getRange("A1:U40"), "all");
    sheet.getRange("A41:AT41").copyFrom(template.getRange("A41:AT41"), "all");
    for (const address of mergeRanges) sheet.mergeCells(address);
    applyColumnWidths(sheet);
    sheet.getRange("A1:AT26").format.rowHeight = 20;
    sheet.getRange("A27:AT27").format.rowHeight = 24;
    sheet.getRange("A28:AT28").format.rowHeight = 30;
    sheet.getRange("A29:AT36").format.rowHeight = 22;
    sheet.getRange("A41:AT41").format.rowHeight = 36;
    sheet.freezePanes.freezeRows(41);

    sheet.getRange("A1").values = [["可编辑红利组合｜2080回测模型"]];
    sheet.getRange("A2").formulas = [[`=\"数据区间：\"&TEXT($A$42,\"yyyy-mm-dd\")&\" 至 \"&TEXT($A$1656,\"yyyy-mm-dd\")&\"｜红利输入：净值底稿 ${scheme.helperCol}｜指增/债券/黄金：T/U/V｜净值基准：费后\"`]];
    sheet.getRange("A5").values = [["红利组合（可编辑）"]];
    sheet.getRange("A6").values = [["指增组合"]];
    sheet.getRange("A7").values = [["中债新综合"]];
    sheet.getRange("A8").values = [["黄金"]];
    sheet.getRange("B5:B8").values = [[0.1], [0.1], [0.75], [0.05]];
    sheet.getRange("N5").values = [[`默认构成：${scheme.composition}。口径：红利组内按起始权重买入持有；2080外层日终判断年末、季末与15%/25%动态阈值。触发后权益合计回到20%，季度把红利/指增校准为1:1；债券/黄金外层调整时保留当日相对比例。`]];

    sheet.mergeCells("N12:P12");
    sheet.getRange("N12").values = [["红利持仓权重（可编辑）"]];
    sheet.getRange("N12:P12").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
    sheet.getRange("N13:P17").values = [
      ["红利低波", 0.3, "净值底稿 G列"],
      ["中证红利", 0.3, "净值底稿 H列"],
      ["港股通央企红利", 0.2, "净值底稿 I列"],
      ["徐彦", 0.1, "净值底稿 J列"],
      ["綦缚鹏", 0.1, "净值底稿 K列"],
    ];
    sheet.getRange("N18:P18").values = [["权重合计", null, null]];
    sheet.getRange("O18").formulas = [["=SUM(O13:O17)"]];
    sheet.getRange("P18").formulas = [["=IF(ABS(O18-1)<0.0000001,\"OK\",\"权重需=100%\")"]];
    sheet.mergeCells("N19:P20");
    sheet.getRange("N19").values = [["只修改黄底蓝字权重；权重合计必须为100%。红利组合归一净值、2080组合、绩效和年度表会自动重算。"]];
    sheet.getRange("N13:N18").format = { fill: "#EAF2F8", font: { color: "#2F5597" }, horizontalAlignment: "left" };
    sheet.getRange("O13:O17").format = { fill: "#FFF2CC", font: { color: "#0000FF", bold: true }, numberFormat: "0.00%", horizontalAlignment: "right" };
    sheet.getRange("O18").format = { fill: "#F2F2F2", font: { bold: true }, numberFormat: "0.00%", horizontalAlignment: "right" };
    sheet.getRange("P13:P17").format = { fill: "#F7F9FB", font: { color: "#666666" }, horizontalAlignment: "left" };
    sheet.getRange("P18").format = { fill: "#E2F0D9", font: { bold: true, color: "#2E7D32" }, horizontalAlignment: "center" };
    sheet.getRange("N13:P18").format.borders = { preset: "all", style: "thin", color: "#B4C6E7" };
    sheet.getRange("N19:P20").format = { fill: "#F2F2F2", font: { size: 9, italic: true, color: "#666666" }, wrapText: true, verticalAlignment: "center" };
    sheet.getRange("P18").conditionalFormats.add("containsText", { text: "OK", format: { fill: "#E2F0D9", font: { bold: true, color: "#2E7D32" } } });
    sheet.getRange("P18").conditionalFormats.add("containsText", { text: "100%", format: { fill: "#FCE4D6", font: { bold: true, color: "#C00000" } } });
    sheet.getRange("N1").format.columnWidth = 18;
    sheet.getRange("O1").format.columnWidth = 13;
    sheet.getRange("P1").format.columnWidth = 18;

    sheet.getRange("K8").formulas = [["=IF(AND(ABS($K$5-1)<0.0000001,$K$6,$K$7,ABS($O$18-1)<0.0000001),\"OK\",\"检查参数/数据\")"]];

    sheet.getRange("K13:K18").formulas = [
      ["=$AD$1656/$AD$42-1"],
      ["=AVERAGE($AG$43:$AG$1656)*$H$6"],
      ["=STDEV($AG$43:$AG$1656)*SQRT($H$6)"],
      ["=MIN($AF$42:$AF$1656)"],
      ["=IFERROR((K14-$H$7)/K15,\"\")"],
      ["=IFERROR((POWER($AD$1656/$AD$42,$H$8/($A$1656-$A$42))-1)/ABS(K16),\"\")"],
    ];
    sheet.getRange("K20:K24").formulas = [
      ["=COUNTIF($T$42:$T$1656,\"动态\")"],
      ["=COUNTIF($T$42:$T$1656,\"季度\")"],
      ["=COUNTIF($T$42:$T$1656,\"年末+季度\")"],
      ["=($Z$1656+$AA$1656)/$AD$1656"],
      ["=$AD$1656"],
    ];

    const daily = buildDailyFormulas(scheme.helperCol);
    sheet.getRange(`A${FIRST_DATA_ROW}:AT${LAST_DATA_ROW}`).formulas = daily;
    applyDailyFormatting(sheet);

    for (let yearIndex = 0; yearIndex < 7; yearIndex += 1) {
      const row = 29 + yearIndex;
      const [start, end] = yearDrawdownBounds[yearIndex];
      sheet.getRange(`N${row}`).formulas = [[`=IF(COUNT(B${row}:M${row})=0,\"\",(1+B${row})*(1+C${row})*(1+D${row})*(1+E${row})*(1+F${row})*(1+G${row})*(1+H${row})*(1+I${row})*(1+J${row})*(1+K${row})*(1+L${row})*(1+M${row})-1)`]];
      sheet.getRange(`P${row}`).formulas = [[`=IF(COUNT($AO$${start}:$AO$${end})=0,\"\",MIN($AO$${start}:$AO$${end}))`]];
    }
    sheet.getRange("N36:P36").formulas = [[
      "=$AD$1656/$AD$42-1",
      "=IFERROR(COUNTIF($AM$42:$AM$1656,\">0\")/COUNT($AM$42:$AM$1656),\"\")",
      "=MIN($AF$42:$AF$1656)",
    ]];

    sheet.getRange("B29:N35").conditionalFormats.add("cellIs", { operator: "greaterThanOrEqual", formula: 0, format: { fill: "#FCE4D6", font: { color: "#E53935" } } });
    sheet.getRange("B29:N35").conditionalFormats.add("cellIs", { operator: "lessThan", formula: 0, format: { fill: "#E2F0D9", font: { color: "#2E7D32" } } });
    sheet.getRange("P29:P36").conditionalFormats.add("cellIs", { operator: "lessThan", formula: 0, format: { fill: "#E2F0D9", font: { color: "#2E7D32" } } });
    sheet.getRange("K8").conditionalFormats.add("containsText", { text: "OK", format: { fill: "#E2F0D9", font: { color: "#2E7D32", bold: true } } });
    addDetailChart(sheet, scheme);
    console.log(`Built ${scheme.sheet}`);
  }

  console.log("Running checks and rendering the three retained user-facing sheets...");
  const editableInputStats = cached.stats;
  for (const col of ["G", "H", "I", "J", "K", "T", "U", "V"]) {
    if (editableInputStats[col].count !== 1615 || editableInputStats[col].missing !== 0 || editableInputStats[col].min <= 0) {
      throw new Error(`Source completeness check failed for ${col}`);
    }
  }
  const editableSheet = workbook.worksheets.getItem(schemes[0].sheet);
  if (editableSheet.getRange("K8").values[0][0] !== "OK") {
    throw new Error(`Editable model status is not OK: ${editableSheet.getRange("K8").values[0][0]}`);
  }
  const editableKeyCheck = await workbook.inspect({
    kind: "table",
    range: `${schemes[0].sheet}!A4:P36`,
    include: "values,formulas",
    tableMaxRows: 40,
    tableMaxCols: 18,
    maxChars: 28000,
  });
  console.log("KEY_CHECK");
  console.log(editableKeyCheck.ndjson);
  const editableErrors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
    options: { useRegex: true, maxResults: 500 },
    summary: "final workbook formula error scan",
  });
  console.log("ERROR_SCAN");
  console.log(editableErrors.ndjson);

  const editableRenderTargets = [
    { name: "净值底稿", range: "A1:AK30" },
    { name: "2080回测", range: "A1:U40" },
    { name: schemes[0].sheet, range: "A1:U40" },
  ];
  for (let index = 0; index < editableRenderTargets.length; index += 1) {
    const target = editableRenderTargets[index];
    const preview = await workbook.render({ sheetName: target.name, range: target.range, scale: 1.05, format: "png" });
    await fs.writeFile(`${PREVIEW_DIR}/${String(index + 1).padStart(2, "0")}_${target.name}.png`, new Uint8Array(await preview.arrayBuffer()));
    console.log(`Rendered ${target.name}`);
  }
  const editableOutput = await SpreadsheetFile.exportXlsx(workbook);
  await editableOutput.save(OUTPUT_PATH);
  console.log(`OUTPUT ${OUTPUT_PATH}`);
  return;

  const finalRatios = componentCols.map((_, index) => {
    const sourceIndex = 1 + index;
    return sourceRows.at(-1)[sourceIndex] / sourceRows[0][sourceIndex];
  });
  const rankings = schemes.map((scheme) => ({
    ...scheme,
    sleeveFinal: scheme.weights.reduce((sum, weight, index) => sum + weight * finalRatios[index], 0),
  })).sort((a, b) => b.sleeveFinal - a.sleeveFinal);
  const topTwo = rankings.slice(0, 2);
  const topTwoIds = new Set(topTwo.map((item) => item.id));

  console.log("Creating the comparison dashboard...");
  const summary = workbook.worksheets.add("红利方案对比");
  summary.showGridLines = false;
  summary.mergeCells("A1:T1");
  summary.getRange("A1").values = [["8组红利配置方案与红利2080回测对比"]];
  summary.getRange("A1:T1").format = { fill: "#4472C4", font: { name: "微软雅黑", size: 14, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
  summary.getRange("A1:T1").format.rowHeight = 28;
  summary.mergeCells("A2:T2");
  summary.getRange("A2").values = [[`当前样本内红利对照组累计收益前两名：${topTwo[0].id} ${topTwo[0].short}（${((topTwo[0].sleeveFinal - 1) * 100).toFixed(2)}%）、${topTwo[1].id} ${topTwo[1].short}（${((topTwo[1].sleeveFinal - 1) * 100).toFixed(2)}%）。排名口径：截至样本末日的红利组内归一化累计收益，不含2080外层与费用。`]];
  summary.getRange("A2:T2").format = { fill: "#D9EAF7", font: { name: "微软雅黑", size: 10, bold: true, color: "#2F5597" }, horizontalAlignment: "left", verticalAlignment: "center", wrapText: true };
  summary.getRange("A2:T2").format.rowHeight = 30;

  summary.mergeCells("N4:T4");
  summary.getRange("N4").values = [["红利组内初始权重与当前累计收益"]];
  summary.getRange("N4:T4").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
  summary.getRange("N5:T5").values = [["方案", "红利低波", "中证红利", "港股央企", "徐彦", "綦缚鹏", "累计收益"]];
  summary.getRange("N5:T5").format = { fill: "#5B9BD5", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
  summary.getRange("N6:T13").values = schemes.map((scheme) => [scheme.id, ...scheme.weights, null]);
  for (let index = 0; index < schemes.length; index += 1) {
    const row = 6 + index;
    summary.getRange(`T${row}`).formulas = [[`=${escapeSheet("净值底稿")}!${schemes[index].helperCol}$${SOURCE_LAST_ROW}-1`]];
    if (topTwoIds.has(schemes[index].id)) summary.getRange(`N${row}:T${row}`).format.fill = "#FFF2CC";
  }
  summary.getRange("O6:T13").format.numberFormat = "0.00%";
  summary.getRange("N5:T13").format.borders = { preset: "all", style: "thin", color: "#B4C6E7" };

  summary.mergeCells("A20:K20");
  summary.getRange("A20").values = [["8组红利2080组合最终绩效对比"]];
  summary.getRange("A20:K20").format = { fill: "#4472C4", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
  summary.getRange("A21:K21").values = [["方案", "累计收益率", "算术年化收益率", "年化波动率", "最大回撤", "Sharpe", "Calmar", "动态再平衡", "季度再平衡", "年末+季度", "状态"]];
  summary.getRange("A21:K21").format = { fill: "#5B9BD5", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  summary.getRange("A21:K21").format.rowHeight = 30;
  for (let index = 0; index < schemes.length; index += 1) {
    const row = 22 + index;
    const scheme = schemes[index];
    summary.getRange(`A${row}:K${row}`).formulas = [[
      `=${escapeSheet(scheme.sheet)}!$A$5`,
      `=${escapeSheet(scheme.sheet)}!$K$13`,
      `=${escapeSheet(scheme.sheet)}!$K$14`,
      `=${escapeSheet(scheme.sheet)}!$K$15`,
      `=${escapeSheet(scheme.sheet)}!$K$16`,
      `=${escapeSheet(scheme.sheet)}!$K$17`,
      `=${escapeSheet(scheme.sheet)}!$K$18`,
      `=${escapeSheet(scheme.sheet)}!$K$20`,
      `=${escapeSheet(scheme.sheet)}!$K$21`,
      `=${escapeSheet(scheme.sheet)}!$K$22`,
      `=${escapeSheet(scheme.sheet)}!$K$8`,
    ]];
    if (topTwoIds.has(scheme.id)) summary.getRange(`A${row}:K${row}`).format.fill = "#EAF2F8";
  }
  summary.getRange("B22:E29").format.numberFormat = "0.00%;[Red](0.00%);-";
  summary.getRange("F22:G29").format.numberFormat = "0.00";
  summary.getRange("H22:J29").format.numberFormat = "0";
  summary.getRange("A21:K29").format.borders = { preset: "all", style: "thin", color: "#B4C6E7" };
  summary.getRange("A22:A29").format.font = { bold: true, color: "#2F5597" };
  summary.getRange("K22:K29").conditionalFormats.add("containsText", { text: "OK", format: { fill: "#E2F0D9", font: { bold: true, color: "#2E7D32" } } });

  const chart = summary.charts.add("line", {
    title: "8组红利配置方案归一化净值（前两名高亮）",
    titleTextStyle: { fontSize: 13, bold: true },
    hasLegend: true,
    legend: { position: "bottom" },
    from: { row: 3, col: 0 },
    extent: { widthPx: 1000, heightPx: 330 },
  });
  const mutedColors = ["#B7C9E2", "#C9C9C9", "#AFC6A5", "#D7C6A5", "#C8B6D9", "#9FB7C7"];
  const highlightColors = ["#1F4E79", "#ED7D31"];
  let mutedIndex = 0;
  let highlightIndex = 0;
  const chartOrder = [...schemes.filter((scheme) => !topTwoIds.has(scheme.id)), ...schemes.filter((scheme) => topTwoIds.has(scheme.id))];
  for (const scheme of chartOrder) {
    const series = chart.series.add(`${scheme.id} ${scheme.short}`);
    series.categoryFormula = `${escapeSheet("净值底稿")}!$A$${SOURCE_FIRST_ROW}:$A$${SOURCE_LAST_ROW}`;
    series.formula = `${escapeSheet("净值底稿")}!$${scheme.helperCol}$${SOURCE_FIRST_ROW}:$${scheme.helperCol}$${SOURCE_LAST_ROW}`;
    const highlighted = topTwoIds.has(scheme.id);
    const color = highlighted ? highlightColors[highlightIndex++] : mutedColors[mutedIndex++ % mutedColors.length];
    series.line = { fill: color, style: "solid", width: highlighted ? 3 : 1 };
  }
  chart.xAxis = { axisType: "dateAxis", numberFormatCode: "yyyy-mm", textStyle: { fontSize: 8 } };
  chart.yAxis = { numberFormatCode: "0.00", textStyle: { fontSize: 8 } };
  chart.setPosition("A4", "M18");

  const summaryWidths = { A: 22, B: 15, C: 17, D: 15, E: 15, F: 11, G: 11, H: 14, I: 14, J: 14, K: 12, L: 3, M: 3, N: 10, O: 12, P: 12, Q: 12, R: 10, S: 10, T: 14 };
  for (const [col, width] of Object.entries(summaryWidths)) summary.getRange(`${col}1`).format.columnWidth = width;
  summary.freezePanes.freezeRows(2);

  console.log("Running finance checks...");
  const inputStats = cached.stats;
  for (const col of ["G", "H", "I", "J", "K", "T", "U", "V"]) {
    if (inputStats[col].count !== 1615 || inputStats[col].missing !== 0 || inputStats[col].min <= 0) {
      throw new Error(`Source completeness check failed for ${col}`);
    }
  }
  for (const scheme of schemes) {
    const values = workbook.worksheets.getItem(scheme.sheet).getRange("K5:K24").values;
    if (values[3][0] !== "OK") throw new Error(`${scheme.sheet} model status is not OK: ${values[3][0]}`);
  }

  const keyCheck = await workbook.inspect({
    kind: "table",
    range: "红利方案对比!A20:K29",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 12,
    maxChars: 24000,
  });
  console.log("PERFORMANCE_CHECK");
  console.log(keyCheck.ndjson);

  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
    options: { useRegex: true, maxResults: 500 },
    summary: "final workbook formula error scan",
  });
  console.log("ERROR_SCAN");
  console.log(errors.ndjson);

  console.log("Rendering all user-facing sheets for visual QA...");
  const renderTargets = [
    { name: "净值底稿", range: "A1:AK30" },
    { name: "2080回测", range: "A1:U40" },
    { name: "红利方案对比", range: "A1:T31" },
    ...schemes.map((scheme) => ({ name: scheme.sheet, range: "A1:U40" })),
  ];
  for (let index = 0; index < renderTargets.length; index += 1) {
    const target = renderTargets[index];
    const preview = await workbook.render({ sheetName: target.name, range: target.range, scale: 1.05, format: "png" });
    await fs.writeFile(`${PREVIEW_DIR}/${String(index + 1).padStart(2, "0")}_${target.name}.png`, new Uint8Array(await preview.arrayBuffer()));
    console.log(`Rendered ${target.name}`);
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT_PATH);
  console.log(`OUTPUT ${OUTPUT_PATH}`);
}

main().catch((error) => {
  console.error(`FAIL: ${error?.message ?? error}`);
  process.exitCode = 1;
});
