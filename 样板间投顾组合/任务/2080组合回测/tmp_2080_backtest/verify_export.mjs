import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "../outputs/2080_backtest_20260901/2080样板间回测模型.xlsx";
const input = await FileBlob.load(path);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 });
console.log("SHEETS");
console.log(sheets.ndjson);

const key = await workbook.inspect({
  kind: "table",
  range: "2080回测!Q12:S19",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 4,
  maxChars: 6000,
});
console.log("KEY");
console.log(key.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 300 },
  summary: "reopened final workbook error scan",
});
console.log("ERRORS");
console.log(errors.ndjson);

for (const [sheetName, range, name, scale] of [
  ["2080回测", "A1:U40", "reopened_dashboard.png", 1.35],
  ["2080回测", "A43:AQ60", "reopened_calculation.png", 1.0],
  ["净值底稿", "A1:Q15", "reopened_source.png", 1.2],
]) {
  const preview = await workbook.render({ sheetName, range, scale, format: "png" });
  await fs.writeFile(`final_previews/${name}`, new Uint8Array(await preview.arrayBuffer()));
}
