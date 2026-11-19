import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const book = await SpreadsheetFile.importXlsx(await FileBlob.load("../2080样板间回测模型.xlsx"));
const overview = await book.inspect({ kind: "workbook,sheet,drawing", maxChars: 6000, tableMaxRows: 3, tableMaxCols: 5 });
console.log(overview.ndjson);
const model = book.worksheets.getItem("2080回测");
for (const cell of ["AM43", "AM44", "AM60", "AG43", "AR43", "AS43", "AT43"]) {
  const range = model.getRange(cell);
  console.log("CELL", cell, JSON.stringify(range.formulas), JSON.stringify(range.displayFormulas), JSON.stringify(range.values));
}
for (const area of ["A1:U8", "J12:P36", "A41:AT44", "A1654:AT1656"]) {
  const result = await book.inspect({ kind: "table", range: `2080回测!${area}`, include: "values,formulas", tableMaxRows: 30, tableMaxCols: 20, maxChars: 14000 });
  console.log(`AREA ${area}\n${result.ndjson}`);
}
const preview = await book.render({ sheetName: "2080回测", range: "A1:U40", scale: 1.1, format: "png" });
await fs.writeFile("before.png", new Uint8Array(await preview.arrayBuffer()));
console.log("before.png");
