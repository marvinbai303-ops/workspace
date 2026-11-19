import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

process.on("uncaughtException", (error) => {
  console.error(`ERR_MSG: ${error?.message ?? error}`);
  process.exitCode = 1;
});
process.on("unhandledRejection", (error) => {
  console.error(`ERR_REJECTION: ${error?.message ?? error}`);
  process.exitCode = 1;
});

const inputPath = "/Users/yangguang/Documents/Codex/workspace/样板间投顾组合/outputs/账户思维 穿越周期的财富管理之道-88财富节-上海.pptx";
const outputDir = "/Users/yangguang/Documents/Codex/workspace/样板间投顾组合/tmp_ppt_20260818/style_ref";
await fs.mkdir(outputDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(inputPath));
const deckSummary = await presentation.inspect({
  kind: "deck,slide,layout",
  maxChars: 30000,
});
console.log("=== DECK SUMMARY ===");
console.log(deckSummary.ndjson);

const slideRecords = deckSummary.ndjson
  .split("\\n")
  .filter(Boolean)
  .map((line) => JSON.parse(line))
  .filter((record) => record.kind === "slide");
const targetRecord = slideRecords.find((record) => record.slide === 28);
if (!targetRecord) throw new Error("Slide 28 not found");

const slide = presentation.resolve(targetRecord.id);
const slideSnapshot = await presentation.inspect({
  target: { id: targetRecord.id, beforeLines: 0, afterLines: 1000 },
  kind: "slide,textbox,textrange,shape,image,table,chart,notes,layout",
  maxChars: 60000,
});
console.log("=== SLIDE 28 SNAPSHOT ===");
console.log(slideSnapshot.ndjson);
await fs.writeFile(`${outputDir}/slide-28-inspect.ndjson`, slideSnapshot.ndjson);

const png = await presentation.export({ slide, format: "png", scale: 2 });
await fs.writeFile(`${outputDir}/slide-28.png`, new Uint8Array(await png.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(`${outputDir}/slide-28.layout.json`, await layout.text());
console.log("=== TARGET ===");
console.log(JSON.stringify({
  slideId: targetRecord.id,
  outputPng: `${outputDir}/slide-28.png`,
  outputLayout: `${outputDir}/slide-28.layout.json`,
}, null, 2));
