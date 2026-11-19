import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "../2080样板间回测模型.xlsx";
const outputDir = "../outputs/2080_fix_20260901";
const outputPath = `${outputDir}/2080样板间回测模型_修复版.xlsx`;

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir("preview", { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("2080回测");

// Normalize the five source-data links. Quoting the Chinese worksheet name
// avoids treating it as a defined name in stricter spreadsheet engines.
sheet.getRange("A42:E42").formulas = [[
  "='净值底稿'!A4",
  "='净值底稿'!F4",
  "='净值底稿'!O4",
  "='净值底稿'!P4",
  "='净值底稿'!Q4",
]];
sheet.getRange("A42:A1656").fillDown();
sheet.getRange("B42:B1656").fillDown();
sheet.getRange("C42:C1656").fillDown();
sheet.getRange("D42:D1656").fillDown();
sheet.getRange("E42:E1656").fillDown();

// Avoid PRODUCT(1+range), which requires array evaluation in older Excel/WPS.
sheet.getRange("N29").formulas = [[
  "=IF(COUNT(B29:M29)=0,\"\",(1+B29)*(1+C29)*(1+D29)*(1+E29)*(1+F29)*(1+G29)*(1+H29)*(1+I29)*(1+J29)*(1+K29)*(1+L29)*(1+M29)-1)",
]];
sheet.getRange("N29:N35").fillDown();

// Avoid MINIFS and dynamic reference construction, both of which are
// unreliable in older Excel/WPS. These ranges are the contiguous daily rows
// for each year and continue to recalculate whenever model parameters change.
sheet.getRange("P29:P35").formulas = [
  ["=IF(COUNT($AO$42:$AO$284)=0,\"\",MIN($AO$42:$AO$284))"],
  ["=IF(COUNT($AO$285:$AO$527)=0,\"\",MIN($AO$285:$AO$527))"],
  ["=IF(COUNT($AO$528:$AO$769)=0,\"\",MIN($AO$528:$AO$769))"],
  ["=IF(COUNT($AO$770:$AO$1011)=0,\"\",MIN($AO$770:$AO$1011))"],
  ["=IF(COUNT($AO$1012:$AO$1253)=0,\"\",MIN($AO$1012:$AO$1253))"],
  ["=IF(COUNT($AO$1254:$AO$1496)=0,\"\",MIN($AO$1254:$AO$1496))"],
  ["=IF(COUNT($AO$1497:$AO$1656)=0,\"\",MIN($AO$1497:$AO$1656))"],
];

const preview = await workbook.render({
  sheetName: "2080回测",
  range: "A1:U40",
  scale: 1.35,
  format: "png",
});
await fs.writeFile("preview/fixed_dashboard.png", new Uint8Array(await preview.arrayBuffer()));

const check = await workbook.inspect({
  kind: "table",
  range: "2080回测!A27:P36",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 18,
  maxChars: 24000,
});
console.log("CHECK");
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 300 },
  summary: "formula errors after targeted fixes",
});
console.log("ERRORS");
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`OUTPUT ${outputPath}`);
