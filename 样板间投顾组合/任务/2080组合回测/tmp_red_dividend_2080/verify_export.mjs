import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("../outputs/01a05c43_red_dividend_2080/2080红利样板间回测模型_可编辑权重版.xlsx"),
);
const key = await workbook.inspect({
  kind: "table",
  range: "2080回测!K8:P18",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
  maxChars: 12000,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 100 },
  summary: "reopened final formula error scan",
});
console.log("REOPEN_KEY");
console.log(key.ndjson);
console.log("REOPEN_ERRORS");
console.log(errors.ndjson);
