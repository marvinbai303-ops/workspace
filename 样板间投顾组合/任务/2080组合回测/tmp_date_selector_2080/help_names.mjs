import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const book = await SpreadsheetFile.importXlsx(await FileBlob.load("../2080样板间回测模型.xlsx"));
console.log(book.help("chart", { search: "blank|empty|gap|plot", include: "index,examples,notes", maxChars: 5000 }).ndjson);
