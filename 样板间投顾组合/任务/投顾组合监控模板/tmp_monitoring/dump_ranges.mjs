import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [path, sheetName, range] = process.argv.slice(2);
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const sheet = wb.worksheets.getItem(sheetName);
const r = sheet.getRange(range);
console.log(JSON.stringify({ values: r.values, formulas: r.formulas, displayFormulas: r.displayFormulas }, null, 2));
