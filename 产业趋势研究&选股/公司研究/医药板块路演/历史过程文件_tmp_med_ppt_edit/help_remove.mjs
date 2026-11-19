import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const p = await PresentationFile.importPptx(await FileBlob.load("/Users/yangguang/Documents/Codex/workspace/选股素材/.tmp_med_ppt_edit/template-starter.pptx"));
for (const q of ["remove chart", "delete chart", "chart collection remove", "slide elements remove", "table add cell styling"]) {
  const h = p.help("*", { search: q, include: ["index", "examples", "notes"], maxChars: 8000 });
  console.log(`QUERY ${q}\n${h.ndjson ?? h}`);
}
const slide = p.slides.getItem(1);
const chart = slide.charts.items[0];
const objects = { charts: slide.charts, chart, shapes: slide.shapes, tables: slide.tables, slide };
for (const [name, obj] of Object.entries(objects)) {
  const own = Object.getOwnPropertyNames(obj);
  const proto = Object.getOwnPropertyNames(Object.getPrototypeOf(obj));
  console.log(name, JSON.stringify({ own, proto }));
}
