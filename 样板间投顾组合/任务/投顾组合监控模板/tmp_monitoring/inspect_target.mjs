import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const wb = await SpreadsheetFile.importXlsx(await FileBlob.load("../样板间投顾组合监控模板-20260716调仓.xlsx"));
const specs = [
  ["实盘持仓配置", "A1:AA11"],
  ["实盘净值数据(iFinD公式)", "A1:Y60"],
  ["实盘组合净值", "A1:U61"],
  ["分期持仓明细", "A1:AB22"],
  ["持仓权重预警", "A1:G35"],
  ["说明", "A1:C19"],
];
for (const [sheetId, range] of specs) {
  console.log(`\n### ${sheetId} ${range}`);
  const table = await wb.inspect({kind:"table", sheetId, range, include:"values,formulas", tableMaxRows:100, tableMaxCols:40, tableMaxCellChars:300, maxChars:60000});
  console.log(table.ndjson);
  const formulas = await wb.inspect({kind:"formula", sheetId, range, options:{maxResults:1000}, maxChars:60000});
  console.log("FORMULAS");
  console.log(formulas.ndjson);
}
