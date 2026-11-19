import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const INPUT = "../2080样板间回测模型.xlsx";
const OUTPUT_DIR = "../outputs/2080_date_selector_20261029";
const OUTPUT = `${OUTPUT_DIR}/2080样板间回测模型_可选截止日.xlsx`;
const FIRST = 42;
const LAST = 1656;
const SOURCE_FIRST = 4;
const SOURCE_LAST = 1618;
const MONTH_LAST = 121;
const ANNUAL = [
  [29, 42, 284], [30, 285, 527], [31, 528, 769], [32, 770, 1011],
  [33, 1012, 1253], [34, 1254, 1496], [35, 1497, 1656],
];

const quote = (name) => `'${name.replaceAll("'", "''")}'`;
const sourceRef = (row) => `${quote("净值底稿")}!A${row}`;
const serial = (year, month, day) => (Date.UTC(year, month - 1, day) - Date.UTC(1899, 11, 30)) / 86400000;
const nearly = (a, b, tolerance = 1e-9) => typeof a === "number" && typeof b === "number" && Math.abs(a - b) <= tolerance;

function contentFormula(originalFormula, originalValue, row, col) {
  let expression;
  if (typeof originalFormula === "string" && originalFormula.startsWith("=")) {
    expression = originalFormula.slice(1);
  } else if (typeof originalValue === "number") {
    expression = String(originalValue);
  } else if (typeof originalValue === "boolean") {
    expression = originalValue ? "TRUE()" : "FALSE()";
  } else if (typeof originalValue === "string") {
    expression = `"${originalValue.replaceAll('"', '""')}"`;
  } else {
    throw new Error(`Unexpected blank daily calculation at row ${row}, column ${col}: formula=${JSON.stringify(originalFormula)}, value=${JSON.stringify(originalValue)}`);
  }
  return `=IF($A${row}="","",${expression})`;
}

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(INPUT));
  const source = workbook.worksheets.getItem("净值底稿");
  const model = workbook.worksheets.getItem("2080回测");
  const lastSourceDate = source.getRange(`A${SOURCE_LAST}`).values[0][0];
  const firstSourceDate = source.getRange(`A${SOURCE_FIRST}`).values[0][0];
  if (typeof lastSourceDate !== "number" || typeof firstSourceDate !== "number") {
    throw new Error("Source dates are not numeric Excel dates");
  }
  const sourceDates = source.getRange(`A${SOURCE_FIRST}:A${SOURCE_LAST}`).values.map((row) => row[0]);
  if (sourceDates.length !== LAST - FIRST + 1 || sourceDates.some((d, i) => typeof d !== "number" || (i > 0 && d <= sourceDates[i - 1]))) {
    throw new Error("Source dates are missing or not strictly increasing");
  }

  // The importer's formula getter omits some formulas whose cached result is blank.
  // Read those exact original expressions from a read-only extraction of the XLSX.
  const originalDaily = JSON.parse(await fs.readFile("daily_original.json", "utf8"));
  if (originalDaily.length !== LAST - FIRST + 1 || originalDaily[0].length !== 42) throw new Error("Original formula extract is incomplete");
  const baselineEndNav = model.getRange(`AD${LAST}`).values[0][0];
  const originalChart = model.charts.items[0];
  const chartBindings = originalChart.series.items.map((series) => ({
    value: series.formula,
    category: series.categoryFormula,
  }));
  console.log(`Input: ${sourceDates.length} dated observations; last NAV ${baselineEndNav}`);

  // The existing sheet has a blank, visible row 3 above its parameter cards.
  model.getRange("H3").values = [["选定截止日"]];
  model.getRange("I3").values = [[lastSourceDate]];
  model.getRange("J3").values = [["实际截止日"]];
  model.getRange("K3").formulas = [[
    `=IF(OR(NOT(ISNUMBER($I$3)),INT($I$3)<${sourceRef(SOURCE_FIRST)}),"",INDEX(${quote("净值底稿")}!$A$${SOURCE_FIRST}:$A$${SOURCE_LAST},MATCH(INT($I$3),${quote("净值底稿")}!$A$${SOURCE_FIRST}:$A$${SOURCE_LAST},1)))`,
  ]];
  model.getRange("L3").values = [["底稿末日"]];
  model.getRange("M3").formulas = [[`=${sourceRef(SOURCE_LAST)}`]];
  model.getRange("N3").values = [["日期状态"]];
  model.mergeCells("O3:S3");
  model.getRange("O3").formulas = [[
    `=IF(NOT(ISNUMBER($I$3)),"请输入有效日期",IF(INT($I$3)<${sourceRef(SOURCE_FIRST)},"早于底稿首日",IF(INT($I$3)>$M$3,"已按底稿末日截取",IF(INT($I$3)<>$K$3,"已按上一有数据日截取","OK"))))`,
  ]];
  model.getRange("T3").values = [["样本天数"]];
  model.getRange("U3").formulas = [[`=IF($K$3="","",MATCH($K$3,${quote("净值底稿")}!$A$${SOURCE_FIRST}:$A$${SOURCE_LAST},0))`]];
  model.getRange("H3:U3").format.rowHeight = 23;
  model.getRange("H3:U3").format = { fill: "#EAF2F8", font: { name: "宋体", size: 9, color: "#2F5597" }, verticalAlignment: "center" };
  model.getRange("I3").format = { fill: "#FFF2CC", font: { name: "宋体", size: 9, bold: true, color: "#0000FF" }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
  model.getRange("K3").format = { fill: "#F7F9FB", font: { name: "宋体", size: 9, color: "#008000" }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
  model.getRange("M3").format = { fill: "#F7F9FB", font: { name: "宋体", size: 9, color: "#008000" }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
  model.getRange("O3:S3").format = { fill: "#F7F9FB", font: { name: "宋体", size: 9, color: "#2F5597" }, horizontalAlignment: "center", verticalAlignment: "center" };
  model.getRange("U3").format = { fill: "#F7F9FB", font: { name: "宋体", size: 9, color: "#000000" }, numberFormat: "0", horizontalAlignment: "center", verticalAlignment: "center" };
  model.getRange("O3").conditionalFormats.add("containsText", { text: "请输入", format: { fill: "#FCE4D6", font: { bold: true, color: "#C00000" } } });
  model.getRange("O3").conditionalFormats.add("containsText", { text: "早于", format: { fill: "#FCE4D6", font: { bold: true, color: "#C00000" } } });
  model.getRange("O3").conditionalFormats.add("containsText", { text: "底稿末日", format: { fill: "#FFF2CC", font: { color: "#9C5700" } } });

  model.getRange("A2").formulas = [[
    `=IF($K$3="","数据区间：请选择有效截止日","数据区间："&TEXT($A$42,"yyyy-mm-dd")&" 至 "&TEXT($K$3,"yyyy-mm-dd")&"｜黄色输入列：净值底稿 F / O / P / Q｜净值基准：费后")`,
  ]];
  model.getRange("B25").formulas = [[
    `=IF($K$3="","数据来源：嘉实财富，iFinD；请选择有效截止日","数据来源：嘉实财富，iFinD；回测区间："&TEXT($A$42,"yyyy-m-d")&" 至 "&TEXT($K$3,"yyyy-m-d"))`,
  ]];
  model.mergeCells("B25:I25");
  model.getRange("B25:I25").format = { font: { name: "宋体", size: 9, color: "#666666" }, horizontalAlignment: "left", verticalAlignment: "center", wrapText: false };
  model.getRange("B25:I25").format.rowHeight = 21;

  console.log("Connecting the daily series to the selected cutoff...");
  model.getRange(`A${FIRST}:A${LAST}`).formulas = sourceDates.map((_, index) => {
    const r = FIRST + index;
    const sourceRow = SOURCE_FIRST + index;
    const ref = sourceRef(sourceRow);
    return [`=IF(AND(ISNUMBER($K$3),${ref}<=$K$3),${ref},"")`];
  });

  function formulaAt(row, col) {
    const index = row - FIRST;
    if (col === 16 && row < LAST) {
      const nextSource = sourceRef(SOURCE_FIRST + index + 1);
      return `=IF($A${row}="","",AND(MONTH($A${row})=12,OR(${nextSource}="",YEAR($A${row})<>YEAR(${nextSource}))))`;
    }
    if (col === 17 && row < LAST) {
      const nextSource = sourceRef(SOURCE_FIRST + index + 1);
      return `=IF($A${row}="","",AND(MOD(MONTH($A${row}),3)=0,OR(${nextSource}="",MONTH($A${row})<>MONTH(${nextSource}))))`;
    }
    if (col === 37) {
      return row === LAST
        ? `=IF($A${row}="","",1)`
        : `=IF($A${row}="","",IF($A${row + 1}="",1,IF(MONTH($A${row})<>MONTH($A${row + 1}),1,0)))`;
    }
    const originalCell = originalDaily[index][col - 2];
    return contentFormula(originalCell, originalCell, row, col);
  }

  // AG42 is deliberately empty in the user's template (no first-day return).
  model.getRange(`B${FIRST}:AF${LAST}`).formulas = Array.from({ length: LAST - FIRST + 1 }, (_, i) => {
    const row = FIRST + i;
    return Array.from({ length: 31 }, (_, j) => formulaAt(row, j + 2));
  });
  model.getRange(`AH${FIRST}:AQ${FIRST}`).formulas = [Array.from({ length: 10 }, (_, j) => formulaAt(FIRST, j + 34))];
  model.getRange(`AG${FIRST + 1}:AQ${LAST}`).formulas = Array.from({ length: LAST - FIRST }, (_, i) => {
    const row = FIRST + 1 + i;
    return Array.from({ length: 11 }, (_, j) => formulaAt(row, j + 33));
  });

  const monthFormulas = [];
  for (let row = FIRST; row <= MONTH_LAST; row += 1) {
    const monthDate = row === FIRST
      ? `=IF($K$3="","",DATE(YEAR(${sourceRef(SOURCE_FIRST)}),MONTH(${sourceRef(SOURCE_FIRST)}),1))`
      : `=IF(OR($AR${row - 1}="",EDATE($AR${row - 1},1)>DATE(YEAR($K$3),MONTH($K$3),1)),"",EDATE($AR${row - 1},1))`;
    monthFormulas.push([
      monthDate,
      `=IF($AR${row}="","",TEXT($AR${row},"yyyy-mm"))`,
      `=IF($AR${row}="",NA(),SUMIFS($AD$${FIRST}:$AD$${LAST},$AI$${FIRST}:$AI$${LAST},YEAR($AR${row}),$AJ$${FIRST}:$AJ$${LAST},MONTH($AR${row}),$AK$${FIRST}:$AK$${LAST},1))`,
    ]);
  }
  model.getRange(`AR${FIRST}:AT${MONTH_LAST}`).formulas = monthFormulas;

  console.log("Updating performance metrics and the annual table...");
  model.getRange("K7").formulas = [[`=IF($U$3="","",AND(COUNT($B$${FIRST}:$E$${LAST})=$U$3*4,MIN($B$${FIRST}:$E$${LAST})>0))`]];
  model.getRange("K8").formulas = [[`=IF($U$3="","请选择有效截止日",IF(AND(ABS($K$5-1)<0.0000001,$K$6,$K$7),"OK","检查参数/数据"))`]];
  model.getRange("K13:K18").formulas = [
    [`=IF($U$3="","",INDEX($AD$${FIRST}:$AD$${LAST},$U$3)/$AD$${FIRST}-1)`],
    [`=IF(OR($U$3="",$U$3<2),"",AVERAGE($AG$${FIRST + 1}:$AG$${LAST})*$H$6)`],
    [`=IF(OR($U$3="",$U$3<3),"",STDEV($AG$${FIRST + 1}:$AG$${LAST})*SQRT($H$6))`],
    [`=IF($U$3="","",MIN($AF$${FIRST}:$AF$${LAST}))`],
    [`=IF(OR(K14="",K15="",K15=0),"",K14/K15)`],
    [`=IF(OR($U$3="",$U$3<2,K16=0),"",(POWER(INDEX($AD$${FIRST}:$AD$${LAST},$U$3)/$AD$${FIRST},$H$8/($K$3-$A$${FIRST}))-1)/ABS(K16))`],
  ];
  model.getRange("K20:K24").formulas = [
    [`=IF($U$3="","",COUNTIF($T$${FIRST}:$T$${LAST},"动态"))`],
    [`=IF($U$3="","",COUNTIF($T$${FIRST}:$T$${LAST},"季度"))`],
    [`=IF($U$3="","",COUNTIF($T$${FIRST}:$T$${LAST},"年末+季度"))`],
    [`=IF($U$3="","",(INDEX($Z$${FIRST}:$Z$${LAST},$U$3)+INDEX($AA$${FIRST}:$AA$${LAST},$U$3))/INDEX($AD$${FIRST}:$AD$${LAST},$U$3))`],
    [`=IF($U$3="","",INDEX($AD$${FIRST}:$AD$${LAST},$U$3))`],
  ];
  model.getRange("B29:M35").formulas = Array.from({ length: 7 }, (_, yearIndex) => {
    const row = 29 + yearIndex;
    return Array.from({ length: 12 }, (_, monthIndex) => {
      const month = monthIndex + 1;
      return `=IF(OR($K$3="",DATE($A${row},${month},1)>$K$3),"",IF(COUNTIFS($AI$${FIRST}:$AI$${LAST},$A${row},$AJ$${FIRST}:$AJ$${LAST},${month},$AK$${FIRST}:$AK$${LAST},1)=0,"",SUMIFS($AM$${FIRST}:$AM$${LAST},$AI$${FIRST}:$AI$${LAST},$A${row},$AJ$${FIRST}:$AJ$${LAST},${month},$AK$${FIRST}:$AK$${LAST},1)))`;
    });
  });
  for (const [summaryRow, yearFirst, yearLast] of ANNUAL) {
    const factors = Array.from({ length: 12 }, (_, monthIndex) => {
      const col = String.fromCharCode(66 + monthIndex);
      return `IF(ISNUMBER(${col}${summaryRow}),1+${col}${summaryRow},1)`;
    });
    model.getRange(`N${summaryRow}`).formulas = [[`=IF(COUNT(B${summaryRow}:M${summaryRow})=0,"",PRODUCT(${factors.join(",")})-1)`]];
    model.getRange(`O${summaryRow}`).formulas = [[`=IF(OR($K$3="",YEAR($K$3)<$A${summaryRow},COUNT(B${summaryRow}:M${summaryRow})=0),"",COUNTIF(B${summaryRow}:M${summaryRow},">0")/COUNT(B${summaryRow}:M${summaryRow}))`]];
    model.getRange(`P${summaryRow}`).formulas = [[`=IF(OR($K$3="",YEAR($K$3)<$A${summaryRow},COUNT($AO$${yearFirst}:$AO$${yearLast})=0),"",MIN($AO$${yearFirst}:$AO$${yearLast}))`]];
  }
  model.getRange("N36:P36").formulas = [[
    `=IF($U$3="","",$K$13)`,
    `=IF(COUNT($AM$${FIRST}:$AM$${LAST})=0,"",COUNTIF($AM$${FIRST}:$AM$${LAST},">0")/COUNT($AM$${FIRST}:$AM$${LAST}))`,
    `=IF($U$3="","",$K$16)`,
  ]];

  // The imported chart's native blank-cell mode is "zero", which draws a
  // false fall to zero after the requested date. A fresh native line chart
  // uses the standard gap behavior while retaining the same bound ranges.
  originalChart.delete();
  const chart = model.charts.add("line", {
    title: "2080组合费后净值走势",
    hasLegend: false,
    from: { row: 11, col: 0 },
    extent: { widthPx: 770, heightPx: 300 },
  });
  const series = chart.series.add("费后净值");
  series.categoryFormula = `${quote("2080回测")}!$AS$${FIRST}:$AS$${MONTH_LAST}`;
  series.formula = `${quote("2080回测")}!$AT$${FIRST}:$AT$${MONTH_LAST}`;
  series.line = { fill: "#5B9BD5", style: "solid", width: 2 };
  chart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 8 } };
  chart.yAxis = { numberFormatCode: "0.0000", numberFormatSourceLinked: false, textStyle: { fontSize: 8 } };
  chart.setPosition("A12", "I24");

  workbook.recalculate();
  const defaultEnd = model.getRange(`AD${LAST}`).values[0][0];
  const defaultKey = model.getRange("K3:U3").values[0];
  const annualValues = model.getRange("N29:P36").values;
  if (!nearly(defaultEnd, baselineEndNav) || !nearly(defaultKey[0], lastSourceDate) || defaultKey[10] !== sourceDates.length) {
    throw new Error(`Default case changed: NAV ${defaultEnd}, cutoff ${defaultKey[0]}, days ${defaultKey[10]}`);
  }
  for (let i = 0; i < 7; i += 1) {
    if (typeof annualValues[i][0] !== "number" || typeof annualValues[i][2] !== "number") {
      throw new Error(`Annual return/drawdown invalid in row ${29 + i}: ${annualValues[i]}`);
    }
  }
  const afterChart = model.charts.items[0];
  const afterBindings = afterChart.series.items.map((series) => ({ value: series.formula, category: series.categoryFormula }));
  if (JSON.stringify(chartBindings) !== JSON.stringify(afterBindings)) {
    throw new Error("The native NAV chart lost its original source binding");
  }
  console.log(`Default check: cutoff ${defaultKey[0]}, days ${defaultKey[10]}, NAV ${defaultEnd}`);

  const selected = serial(2024, 6, 15); // Non-trading day in the middle of the sample.
  let expectedIndex = -1;
  for (let i = 0; i < sourceDates.length; i += 1) if (sourceDates[i] <= selected) expectedIndex = i;
  model.getRange("I3").values = [[selected]];
  workbook.recalculate();
  const actualDate = model.getRange("K3").values[0][0];
  const selectedEndRow = FIRST + expectedIndex;
  const selectedNav = model.getRange(`AD${selectedEndRow}`).values[0][0];
  const nextNav = model.getRange(`AD${selectedEndRow + 1}`).values[0][0];
  const selectedMonthEnd = model.getRange(`AK${selectedEndRow}`).values[0][0];
  const selectedMonthChart = model.getRange("AT95").values[0][0];
  const selectedAnnual = model.getRange("N33").values[0][0];
  const priorYearEndNav = model.getRange("AD1011").values[0][0];
  const selectedCumulative = model.getRange("K13").values[0][0];
  if (!nearly(actualDate, sourceDates[expectedIndex]) || typeof selectedNav !== "number" || nextNav !== "" || selectedMonthEnd !== 1 || !nearly(selectedMonthChart, selectedNav) || !nearly(selectedAnnual, selectedNav / priorYearEndNav - 1) || !nearly(selectedCumulative, selectedNav - 1) || model.getRange("K8").values[0][0] !== "OK") {
    throw new Error(`Selected-date test failed: date ${actualDate}, end NAV ${selectedNav}, following NAV ${nextNav}, month end ${selectedMonthEnd}, chart ${selectedMonthChart}, year ${selectedAnnual}, total ${selectedCumulative}`);
  }
  console.log(`Mid-sample test: requested ${selected}, actual ${actualDate}, last row ${selectedEndRow}, NAV ${selectedNav}, next blank`);
  const selectedPreview = await workbook.render({ sheetName: "2080回测", range: "A1:U40", scale: 1.1, format: "png" });
  await fs.writeFile("selected_date_preview.png", new Uint8Array(await selectedPreview.arrayBuffer()));

  model.getRange("I3").values = [[lastSourceDate]];
  workbook.recalculate();
  if (!nearly(model.getRange("K24").values[0][0], baselineEndNav)) throw new Error("Default case did not restore");
  const key = await workbook.inspect({ kind: "table", range: "2080回测!H3:U24", include: "values,formulas", tableMaxRows: 22, tableMaxCols: 14, maxChars: 16000 });
  console.log("KEY_CHECK\n" + key.ndjson);
  const annualCheck = await workbook.inspect({ kind: "table", range: "2080回测!A28:P36", include: "values,formulas", tableMaxRows: 9, tableMaxCols: 16, maxChars: 16000 });
  console.log("ANNUAL_CHECK\n" + annualCheck.ndjson);
  const errors = await workbook.inspect({
    kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan",
  });
  console.log("ERROR_SCAN\n" + errors.ndjson);
  if (!errors.ndjson.includes("matched 0 entries")) throw new Error("Formula error scan found matches");

  const preview = await workbook.render({ sheetName: "2080回测", range: "A1:U40", scale: 1.1, format: "png" });
  await fs.writeFile("final_preview.png", new Uint8Array(await preview.arrayBuffer()));
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT);
  console.log(`OUTPUT ${OUTPUT}`);
}

main().catch((error) => {
  console.error(error?.stack ?? String(error));
  process.exitCode = 1;
});
