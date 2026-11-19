import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("../outputs/2080_backtest_20260901/2080样板间回测模型.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);

for (const range of ["2080回测!A46:AQ70", "2080回测!A1645:AQ1660", "2080回测!AR45:AT55"]) {
  const check = await workbook.inspect({
    kind: "table",
    range,
    include: "values,formulas",
    tableMaxRows: 30,
    tableMaxCols: 50,
    maxChars: 30000,
  });
  console.log(`RANGE ${range}`);
  console.log(check.ndjson);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 100 },
  summary: "diagnostic formula scan",
});
console.log("ERRORS");
console.log(errors.ndjson);
