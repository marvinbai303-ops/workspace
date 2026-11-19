import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("normalized/2080红利样板间回测模型.xlsx"),
);
const source = workbook.worksheets.getItem("2080回测");
const target = workbook.worksheets.add("复制测试");
target.getRange("A1:AT1656").copyFrom(source.getRange("A1:AT1656"), "all");
const preview = await workbook.render({
  sheetName: "复制测试",
  range: "A1:U40",
  scale: 1.05,
  format: "png",
});
await fs.writeFile("copy_test.png", new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({
  values: target.getRange("H1:U36").values,
  formulas: target.getRange("H1:U36").formulas,
}, null, 2));
