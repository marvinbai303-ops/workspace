import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const workspace = "/Users/yangguang/Documents/Codex/workspace/样板间投顾组合";
const sourcePath = path.join(workspace, "净值序列1.xls");
const outputDir = path.join(workspace, "outputs/20260820-1090-repair");
const outputPath = path.join(outputDir, "1090净值修复对比分析_截至20260818.xlsx");
const previewDir = path.join(workspace, "tmp_1090_repair_20260820/workbook_previews");

const nameMap = {
  "003504.OF": "景顺长城景颐丰利债券",
  "000143.OF": "鹏华双债加利债券",
  "000385.OF": "景顺长城景颐双利债券",
  "002065.OF": "景顺长城景盛双息收益债券",
  "002969.OF": "易方达丰和债券",
  "014088.OF": "永赢稳健增强债券",
  "001751.OF": "华商信用增强债券",
  "014846.OF": "博时恒乐债券",
  "000171.OF": "易方达裕丰回报债券",
  "202101.OF": "南方宝元债券",
  "470010.OF": "汇添富多元收益债券",
  "000406.OF": "汇添富双利增强债券",
  "018595.OF": "华商利欣回报债券",
  "020218.OF": "万家锦利债券发起式",
};

const scaleMap = {
  "003504.OF": 712,
  "000143.OF": 584,
  "000385.OF": 576,
  "002065.OF": 393,
  "002969.OF": 391,
  "014088.OF": 365,
  "001751.OF": 361,
  "014846.OF": 359,
  "000171.OF": 342,
  "202101.OF": 314,
  "000406.OF": 293,
  "018595.OF": 283,
  "470010.OF": 274,
  "020218.OF": 180,
};

const groups = [
  { sourceName: "全市场前十", suffix: "规模前十", rawName: "原始数据-规模前十", metricsName: "指标-规模前十" },
  { sourceName: "全市场增长前十", suffix: "规模增长前十", rawName: "原始数据-增长前十", metricsName: "指标-增长前十" },
];

function excelCol(index1) {
  let n = index1;
  let out = "";
  while (n > 0) {
    n -= 1;
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26);
  }
  return out;
}

function asDate(value) {
  if (value instanceof Date) return value;
  if (typeof value === "number") {
    return new Date(Math.round((value - 25569) * 86400 * 1000));
  }
  return new Date(value);
}

function matrix(rows, cols, fn) {
  return Array.from({ length: rows }, (_, r) =>
    Array.from({ length: cols }, (_, c) => fn(r, c)),
  );
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const sourceBlob = await FileBlob.load(sourcePath);
const sourceWorkbook = await SpreadsheetFile.importXlsx(sourceBlob);
console.log((await sourceWorkbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 })).ndjson);

const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "User" });

for (const group of groups) {
  const sourceSheet = sourceWorkbook.worksheets.getItem(group.sourceName);
  const sourceValues = sourceSheet.getUsedRange(true).values;
  const sourceHeaders = sourceValues[0].map((v) => String(v ?? "").trim());

  // Select date, 1090, and the ten fund columns. The unrelated portfolio column is intentionally excluded.
  const selectedIndexes = [0, 2, ...Array.from({ length: 10 }, (_, i) => i + 3)];
  // Imported spreadsheet dates are UTC-midnight values. Use end-of-day UTC so 8/18 is included and 8/19 is excluded.
  const cutoff = new Date("2026-08-18T23:59:59Z");
  const datedRows = sourceValues.slice(1)
    .filter((row) => row[0] != null)
    .map((row) => [asDate(row[0]), ...selectedIndexes.slice(1).map((idx) => Number(row[idx]))])
    .filter((row) => row[0] <= cutoff);

  const codes = ["1090", ...selectedIndexes.slice(2).map((idx) => sourceHeaders[idx])];
  const labels = ["1090组合", ...codes.slice(1).map((code) => nameMap[code] ?? code)];
  const metricItems = [
    { code: "1090", label: "1090组合", scale: null, rawSeriesIndex: 0 },
    ...codes.slice(1).map((code, idx) => ({
      code,
      label: labels[idx + 1],
      scale: scaleMap[code],
      rawSeriesIndex: idx + 1,
    })).sort((a, b) => b.scale - a.scale),
  ];
  const rawHeaders = ["日期", ...labels];
  const rawSheet = workbook.worksheets.add(group.rawName);
  rawSheet.showGridLines = false;
  rawSheet.freezePanes.freezeRows(4);
  rawSheet.freezePanes.freezeColumns(1);

  rawSheet.mergeCells("A1:AJ1");
  rawSheet.getRange("A1").values = [[`1090与全市场Q2${group.suffix}固收+净值数据及计算辅助`]];
  rawSheet.getRange("A1:AJ1").format = {
    fill: "#8B0000",
    font: { name: "Arial", size: 16, bold: true, color: "#FFFFFF" },
    rowHeight: 28,
    verticalAlignment: "center",
  };
  rawSheet.mergeCells("A2:AJ2");
  rawSheet.getRange("A2").values = [["口径：2026-06-18至2026-08-18；各序列归一化起点=1；原文件8月19日数据未纳入。"]];
  rawSheet.getRange("A2:AJ2").format = {
    font: { name: "Arial", size: 10, color: "#667085" },
    rowHeight: 20,
  };
  rawSheet.getRange("A4:L4").values = [rawHeaders];
  rawSheet.getRange("N4:X4").values = [[...labels]];
  rawSheet.getRange("Z4:AJ4").values = [[...labels]];
  rawSheet.getRange("N3:X3").merge();
  rawSheet.getRange("N3").values = [["归一化净值（起点=1）"]];
  rawSheet.getRange("Z3:AJ3").merge();
  rawSheet.getRange("Z3").values = [["回撤序列"]];

  const dataValues = datedRows.map((row) => [row[0], ...row.slice(1)]);
  const firstDataRow = 5;
  const lastDataRow = firstDataRow + dataValues.length - 1;
  rawSheet.getRange(`A${firstDataRow}:L${lastDataRow}`).values = dataValues;
  rawSheet.getRange(`A${firstDataRow}:A${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";
  rawSheet.getRange(`B${firstDataRow}:L${lastDataRow}`).format.numberFormat = "0.000000";

  const normFormulas = matrix(dataValues.length, 11, (r, c) => {
    const rawCol = excelCol(c + 2);
    return `='${group.rawName}'!${rawCol}${firstDataRow + r}/'${group.rawName}'!${rawCol}$${firstDataRow}`;
  });
  rawSheet.getRange(`N${firstDataRow}:X${lastDataRow}`).formulas = normFormulas;
  rawSheet.getRange(`N${firstDataRow}:X${lastDataRow}`).format.numberFormat = "0.0000";

  const drawdownFormulas = matrix(dataValues.length, 11, (r, c) => {
    const normCol = excelCol(c + 14);
    return `='${group.rawName}'!${normCol}${firstDataRow + r}/MAX('${group.rawName}'!${normCol}$${firstDataRow}:${normCol}${firstDataRow + r})-1`;
  });
  rawSheet.getRange(`Z${firstDataRow}:AJ${lastDataRow}`).formulas = drawdownFormulas;
  rawSheet.getRange(`Z${firstDataRow}:AJ${lastDataRow}`).format.numberFormat = "0.00%";

  for (const headerRange of ["A4:L4", "N3:X4", "Z3:AJ4"]) {
    rawSheet.getRange(headerRange).format = {
      fill: "#F3F6FA",
      font: { name: "Arial", size: 10, bold: true, color: "#344054" },
      horizontalAlignment: "center",
      verticalAlignment: "center",
      wrapText: true,
      borders: { preset: "all", style: "thin", color: "#D0D5DD" },
    };
  }
  rawSheet.getRange(`A${firstDataRow}:AJ${lastDataRow}`).format.font = { name: "Arial", size: 9, color: "#344054" };
  rawSheet.getRange(`A${firstDataRow}:AJ${lastDataRow}`).format.borders = { preset: "inside", style: "thin", color: "#EAECF0" };
  rawSheet.getRange(`A4:A${lastDataRow}`).format.columnWidth = 12;
  rawSheet.getRange(`B4:L${lastDataRow}`).format.columnWidth = 18;
  rawSheet.getRange(`N3:AJ${lastDataRow}`).format.columnWidth = 15;
  workbook.comments.addThread({ cell: rawSheet.getRange("A2") }, "数据源：净值序列1.xls；截止日按用户口径固定为2026-08-18。");

  const metricsSheet = workbook.worksheets.add(group.metricsName);
  metricsSheet.showGridLines = false;
  metricsSheet.freezePanes.freezeRows(5);
  metricsSheet.mergeCells("A1:H1");
  metricsSheet.getRange("A1").values = [[`1090与全市场Q2${group.suffix}固收+：回撤与修复指标`]];
  metricsSheet.getRange("A1:H1").format = {
    fill: "#8B0000",
    font: { name: "Arial", size: 18, bold: true, color: "#FFFFFF" },
    rowHeight: 30,
    verticalAlignment: "center",
  };
  metricsSheet.mergeCells("A2:H2");
  metricsSheet.getRange("A2").values = [["基金按26Q2规模从大到小排列；累计修复幅度=自区间最低点反弹至8月18日的涨幅÷|区间最大回撤|。"]];
  metricsSheet.getRange("A2:H2").format = { font: { name: "Arial", size: 10, color: "#667085" }, rowHeight: 22 };
  const headers = ["组合/基金", "代码", "26Q2规模（亿元）", "成立以来", "最大回撤", "离最高点距离", "自最低点反弹", "累计修复幅度"];
  metricsSheet.getRange("A4:H4").values = [headers];
  metricsSheet.getRange("A4:H4").format = {
    fill: "#F3F6FA",
    font: { name: "Arial", size: 11, bold: true, color: "#344054" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    rowHeight: 34,
    borders: { preset: "all", style: "thin", color: "#98A2B3" },
  };
  const metricRows = metricItems.map((item) => [item.label, item.code, item.scale, null, null, null, null, null]);
  metricsSheet.getRange("A5:H15").values = metricRows;
  const metricFormulas = matrix(11, 5, (r, c) => {
    const rawCol = excelCol(metricItems[r].rawSeriesIndex + 2);
    const ddCol = excelCol(metricItems[r].rawSeriesIndex + 26);
    const row = r + 5;
    if (c === 0) return `='${group.rawName}'!${rawCol}${lastDataRow}/'${group.rawName}'!${rawCol}${firstDataRow}-1`;
    if (c === 1) return `=MIN('${group.rawName}'!${ddCol}${firstDataRow}:${ddCol}${lastDataRow})`;
    if (c === 2) return `='${group.rawName}'!${rawCol}${lastDataRow}/MAX('${group.rawName}'!${rawCol}${firstDataRow}:${rawCol}${lastDataRow})-1`;
    if (c === 3) return `='${group.rawName}'!${rawCol}${lastDataRow}/MIN('${group.rawName}'!${rawCol}${firstDataRow}:${rawCol}${lastDataRow})-1`;
    return `=IF(ABS(E${row})<0.000000000001,999999,G${row}/ABS(E${row}))`;
  });
  metricsSheet.getRange("D5:H15").formulas = metricFormulas;
  metricsSheet.getRange("C5:C15").format.numberFormat = "0";
  metricsSheet.getRange("D5:H15").format.numberFormat = "0.00%";
  metricsSheet.getRange("A5:H15").format = {
    font: { name: "Arial", size: 10, color: "#344054" },
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: "#D0D5DD" },
    rowHeight: 26,
  };
  metricsSheet.getRange("A5:H5").format = {
    fill: "#FFF4F2",
    font: { name: "Arial", size: 10, bold: true, color: "#8B0000" },
    borders: { preset: "all", style: "medium", color: "#8B0000" },
    rowHeight: 28,
  };
  metricsSheet.getRange("A5:A15").format.columnWidth = 30;
  metricsSheet.getRange("B5:B15").format.columnWidth = 13;
  metricsSheet.getRange("C4:C15").format.columnWidth = 14;
  metricsSheet.getRange("D4:H15").format.columnWidth = 15;
  metricsSheet.getRange("A5:B15").format.horizontalAlignment = "left";
  metricsSheet.getRange("C5:H15").format.horizontalAlignment = "center";
  workbook.comments.addThread({ cell: metricsSheet.getRange("C4") }, "26Q2规模来自工作区已核验的《固收+基金三榜单汇总及代码匹配.xlsx》，单位：亿元。");
  workbook.comments.addThread({ cell: metricsSheet.getRange("H4") }, "累计修复幅度=（8月18日净值/区间最低净值-1）÷ ABS（区间最大回撤）。");
}

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

for (const group of groups) {
  const metricsPreview = await workbook.render({ sheetName: group.metricsName, range: "A1:H15", scale: 1.5, format: "png" });
  await fs.writeFile(path.join(previewDir, `${group.metricsName}.png`), new Uint8Array(await metricsPreview.arrayBuffer()));
  const rawPreview = await workbook.render({ sheetName: group.rawName, range: "A1:AJ18", scale: 0.75, format: "png" });
  await fs.writeFile(path.join(previewDir, `${group.rawName}.png`), new Uint8Array(await rawPreview.arrayBuffer()));
}

for (const group of groups) {
  console.log((await workbook.inspect({
    kind: "table",
    sheetId: group.metricsName,
    range: "A1:H15",
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 10,
    maxChars: 12000,
  })).ndjson);
}
console.log((await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
  maxChars: 3000,
})).ndjson);
console.log(JSON.stringify({ outputPath, previewDir }));
