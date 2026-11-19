import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

async function main() {
await fs.mkdir("inspect_input", { recursive: true });
const workbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load("normalized/2080红利样板间回测模型.xlsx"),
);

const summary = await workbook.inspect({
  kind: "workbook,sheet,drawing,definedName",
  include: "id,name,visibility,address,type,formula",
  maxChars: 30000,
  tableMaxRows: 8,
  tableMaxCols: 12,
});
console.log("SUMMARY");
console.log(summary.ndjson);

const sheetNames = ["净值底稿", "2080回测"];
for (let i = 0; i < sheetNames.length; i += 1) {
  const sheet = workbook.worksheets.getItem(sheetNames[i]);
  const used = sheet.getUsedRange();
  console.log(`SHEET ${i + 1}: ${sheet.name} USED=${used?.address ?? "none"}`);

  const formulaReport = await workbook.inspect({
    kind: "formula",
    sheetId: sheet.name,
    maxChars: 7000,
    options: { maxResults: 100 },
  });
  await fs.writeFile(
    `inspect_input/${String(i + 1).padStart(2, "0")}_${sheet.name.replaceAll("/", "_")}_formulas.ndjson`,
    formulaReport.ndjson ?? "",
    "utf8",
  );

  const preview = await workbook.render({
    sheetName: sheet.name,
    range: sheet.name === "净值底稿" ? "A1:V55" : "A1:U40",
    scale: 1.05,
    format: "png",
  });
  await fs.writeFile(
    `inspect_input/${String(i + 1).padStart(2, "0")}_${sheet.name.replaceAll("/", "_")}.png`,
    new Uint8Array(await preview.arrayBuffer()),
  );

  if (sheet.name === "净值底稿") {
    const tailPreview = await workbook.render({
      sheetName: sheet.name,
      range: "A1560:V1619",
      scale: 1.05,
      format: "png",
    });
    await fs.writeFile(
      "inspect_input/01_净值底稿_tail.png",
      new Uint8Array(await tailPreview.arrayBuffer()),
    );
  }
}

await fs.writeFile("inspect_input/sheet_names.json", JSON.stringify(sheetNames, null, 2));

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 500 },
  summary: "input formula error scan",
});
console.log("ERRORS");
console.log(errors.ndjson);
}

main().catch((error) => {
  console.error(`FAIL: ${error?.message ?? error}`);
  process.exitCode = 1;
});
