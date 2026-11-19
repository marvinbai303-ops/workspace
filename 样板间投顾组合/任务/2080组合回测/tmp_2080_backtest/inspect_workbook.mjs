import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "../2080样板间测算底稿.xlsx";
const outDir = "inspect_output";

await fs.mkdir(outDir, { recursive: true });
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,table,drawing,definedName",
  maxChars: 20000,
  tableMaxRows: 8,
  tableMaxCols: 12,
  tableMaxCellChars: 100,
});
console.log(summary.ndjson);

for (let i = 0; i < workbook.worksheets.items.length; i += 1) {
  const sheet = workbook.worksheets.getItemAt(i);
  const used = sheet.getUsedRange();
  const name = sheet.name;
  console.log(`USED\t${i}\t${name}\t${used?.address ?? "(none)"}`);
  const region = await workbook.inspect({
    kind: "region",
    sheetId: name,
    range: used?.address ?? "A1:A1",
    maxChars: 12000,
    tableMaxRows: 20,
    tableMaxCols: 20,
    tableMaxCellChars: 100,
  });
  await fs.writeFile(`${outDir}/sheet_${i}_region.ndjson`, region.ndjson ?? "", "utf8");

  if (name === "净值底稿") {
    const preview = await workbook.render({
      sheetName: name,
      range: "A1:Q25",
      scale: 1.5,
      format: "png",
    });
    await fs.writeFile(`${outDir}/source_preview.png`, new Uint8Array(await preview.arrayBuffer()));

    const styles = await workbook.inspect({
      kind: "computedStyle",
      sheetId: name,
      range: "A1:Q8",
      maxChars: 20000,
    });
    await fs.writeFile(`${outDir}/styles_A1_Q8.ndjson`, styles.ndjson ?? "", "utf8");

    const formulas = await workbook.inspect({
      kind: "formula",
      sheetId: name,
      range: "A1:Q1618",
      maxChars: 30000,
      options: { maxResults: 200 },
    });
    await fs.writeFile(`${outDir}/formulas.ndjson`, formulas.ndjson ?? "", "utf8");

    const top = sheet.getRange("A1:Q12");
    const bottom = sheet.getRange("A1608:Q1619");
    await fs.writeFile(`${outDir}/top_values_formulas.json`, JSON.stringify({ values: top.values, formulas: top.formulas, displayFormulas: top.displayFormulas }, null, 2), "utf8");
    await fs.writeFile(`${outDir}/bottom_values_formulas.json`, JSON.stringify({ values: bottom.values, formulas: bottom.formulas, displayFormulas: bottom.displayFormulas }, null, 2), "utf8");
  }
}
