import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "../outputs/019fe9e8-9aa4-7333-9b05-6ec8e2b0a2b8/样板间投顾组合监控模板-20260716调仓_偏离度监控.xlsx";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
console.log((await wb.inspect({kind:"table",sheetId:"偏离度监控",range:"A5:H44",include:"values,formulas",tableMaxRows:45,tableMaxCols:8,tableMaxCellChars:120,maxChars:16000})).ndjson);
console.log("NEW_SHEET_ERRORS");
console.log((await wb.inspect({kind:"match",sheetId:"偏离度监控",range:"A1:L112",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#SPILL!",options:{useRegex:true,maxResults:300},maxChars:12000})).ndjson);
for (const [name, range] of [["monitor_top","A1:L47"],["monitor_detail","A50:L85"],["monitor_snapshot","A88:L112"]]) {
  const blob = await wb.render({sheetName:"偏离度监控",range,scale:1.5,format:"png"});
  await fs.writeFile(`previews_after/${name}.png`,new Uint8Array(await blob.arrayBuffer()));
}
