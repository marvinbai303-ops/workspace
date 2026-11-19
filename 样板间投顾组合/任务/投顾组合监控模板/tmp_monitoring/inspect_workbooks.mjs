import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = process.argv.slice(2);
for (const path of files) {
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  const sheets = await wb.inspect({ kind: "sheet", include: "id,name", maxChars: 12000 });
  console.log(`\n### ${path}`);
  console.log(sheets.ndjson);
  const summary = await wb.inspect({
    kind: "workbook,sheet,table,definedName,drawing",
    maxChars: 30000,
    tableMaxRows: 8,
    tableMaxCols: 12,
    tableMaxCellChars: 120,
  });
  console.log(summary.ndjson);
}
