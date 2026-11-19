import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("normalized/2080红利样板间回测模型.xlsx"),
);
const input = workbook.worksheets.getItem("净值底稿");
const model = workbook.worksheets.getItem("2080回测");

await fs.writeFile("inspect_input/input_top.json", JSON.stringify({
  values: input.getRange("A1:V10").values,
  formulas: input.getRange("A1:V10").formulas,
}, null, 2));

await fs.writeFile("inspect_input/model_top.json", JSON.stringify({
  values: model.getRange("A1:U40").values,
  formulas: model.getRange("A1:U40").formulas,
}, null, 2));

await fs.writeFile("inspect_input/model_daily.json", JSON.stringify({
  values: model.getRange("A41:AT48").values,
  formulas: model.getRange("A41:AT48").formulas,
}, null, 2));

const styles = await workbook.inspect({
  kind: "computedStyle",
  sheetId: "2080回测",
  range: "A1:U40",
  maxChars: 20000,
});
await fs.writeFile("inspect_input/model_styles.ndjson", styles.ndjson ?? "");

console.log("written");
