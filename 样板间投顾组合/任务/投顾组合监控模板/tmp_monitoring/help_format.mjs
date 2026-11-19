import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load("../样板间投顾组合监控模板-20260716调仓.xlsx"));
console.log(wb.help("range.format", {include:"index,examples,notes", maxChars:6000}).ndjson);
