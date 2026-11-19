import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputPath, outputDir, contactName = "contact.png"] = process.argv.slice(2);
await fs.mkdir(outputDir, { recursive: true });
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheetInfo = JSON.parse(`[${(await wb.inspect({kind:"sheet", include:"id,name", maxChars:50000})).ndjson.split("\n").filter(Boolean).join(",")}]`);
const rendered = [];
for (const item of sheetInfo) {
  const ranges = {
    "实盘净值数据(iFinD公式)": "A1:Y65",
    "偏离度监控": "A1:L47",
  };
  const renderOptions = ranges[item.name]
    ? { sheetName: item.name, range: ranges[item.name], scale: 0.75, format: "png" }
    : { sheetName: item.name, autoCrop: "all", scale: 0.75, format: "png" };
  const blob = await wb.render(renderOptions);
  const safe = item.name.replace(/[\\/:*?"<>|]/g, "_");
  const file = path.join(outputDir, `${String(item.index + 1).padStart(2, "0")}_${safe}.png`);
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(file, bytes);
  const body = await sharp(bytes).resize({ width: 560, height: 360, fit: "inside", background: "#FFFFFF" }).png().toBuffer();
  const meta = await sharp(body).metadata();
  const thumb = await sharp({ create: { width: 568, height: 400, channels: 4, background: "#FFFFFF" } })
    .composite([
      {input: body, top: 36 + Math.floor((360 - meta.height) / 2), left: 4 + Math.floor((560 - meta.width) / 2)},
      {input: Buffer.from(`<svg width="560" height="36"><text x="8" y="24" font-family="Arial" font-size="18" fill="#1f2937">${item.index + 1}. ${item.name}</text></svg>`), top: 0, left: 4},
    ]).png().toBuffer();
  rendered.push(thumb);
}
const cols = 2;
const tileW = 568;
const tileH = 400;
const rows = Math.ceil(rendered.length / cols);
const composites = rendered.map((input, i) => ({ input, left: (i % cols) * tileW, top: Math.floor(i / cols) * tileH }));
await sharp({ create: { width: cols * tileW, height: rows * tileH, channels: 4, background: "#ECEFF3" } })
  .composite(composites)
  .png()
  .toFile(path.join(outputDir, contactName));
console.log(path.join(outputDir, contactName));
