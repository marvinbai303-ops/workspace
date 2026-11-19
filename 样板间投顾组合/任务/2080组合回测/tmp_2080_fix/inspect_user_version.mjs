import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

await fs.mkdir("inspect", { recursive: true });
const input = await FileBlob.load("../2080样板间回测模型.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,drawing",
  maxChars: 8000,
  tableMaxRows: 8,
  tableMaxCols: 12,
});
console.log("SUMMARY");
console.log(summary.ndjson);

const annual = await workbook.inspect({
  kind: "table",
  range: "2080回测!A31:P40",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 18,
  maxChars: 24000,
});
console.log("ANNUAL");
console.log(annual.ndjson);

const formulas = await workbook.inspect({
  kind: "formula",
  sheetId: "2080回测",
  range: "N33:P40",
  maxChars: 12000,
  options: { maxResults: 100 },
});
console.log("FORMULAS");
console.log(formulas.ndjson);

const target = workbook.worksheets.getItem("2080回测").getRange("A27:P36");
await fs.writeFile("inspect/target_values_formulas.json", JSON.stringify({
  values: target.values,
  formulas: target.formulas,
  displayFormulas: target.displayFormulas,
}, null, 2), "utf8");

const styles = await workbook.inspect({
  kind: "computedStyle",
  sheetId: "2080回测",
  range: "N32:P40",
  maxChars: 16000,
});
await fs.writeFile("inspect/styles.ndjson", styles.ndjson ?? "", "utf8");

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 300 },
  summary: "input workbook formula errors",
});
console.log("ERRORS");
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "2080回测",
  range: "A1:U40",
  scale: 1.35,
  format: "png",
});
await fs.writeFile("inspect/input_dashboard.png", new Uint8Array(await preview.arrayBuffer()));
