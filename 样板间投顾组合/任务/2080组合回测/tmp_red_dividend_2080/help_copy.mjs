import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("normalized/2080红利样板间回测模型.xlsx"),
);
console.log(
  workbook.help("*", {
    search: "worksheet|sheet|copy|clone|duplicate",
    include: "index,examples,notes",
    maxChars: 8000,
  }).ndjson,
);
