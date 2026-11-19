import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load("../样板间投顾组合监控模板-20260716调仓.xlsx"));
console.log(wb.help("fx.XMATCH", {include:"index,examples,notes", maxChars:4000}).ndjson);
