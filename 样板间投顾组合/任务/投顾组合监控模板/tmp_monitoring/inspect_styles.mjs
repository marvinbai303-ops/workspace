import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load("../样板间投顾组合监控模板-20260716调仓.xlsx"));
for (const [sheetId, range] of [["持仓权重预警","A1:G35"],["看板-产业趋势","B2:G18"],["说明","B2:C19"]]) {
  console.log(`### ${sheetId}`);
  console.log((await wb.inspect({kind:"computedStyle",sheetId,range,maxChars:25000})).ndjson);
}
