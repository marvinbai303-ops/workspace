import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("../outputs/2080_fix_20260901/2080样板间回测模型_修复版.xlsx"),
);
const sheet = workbook.worksheets.getItem("2080回测");

const years = sheet.getRange("AI42:AI1656").values.flat();
const bounds = {};
for (let index = 0; index < years.length; index += 1) {
  const year = years[index];
  if (year === null || year === "") continue;
  if (!bounds[year]) bounds[year] = { start: 42 + index, end: 42 + index };
  bounds[year].end = 42 + index;
}
console.log(JSON.stringify(bounds, null, 2));
console.log(JSON.stringify({
  formulas: sheet.getRange("N29:P35").formulas,
  values: sheet.getRange("N29:P35").values,
}, null, 2));

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 300 },
  summary: "exported workbook formula errors",
});
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "2080回测",
  range: "A1:U40",
  scale: 1.35,
  format: "png",
});
await fs.writeFile("preview/reopened_dashboard.png", new Uint8Array(await preview.arrayBuffer()));
