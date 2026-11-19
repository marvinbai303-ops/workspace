import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";
const wb=Workbook.create();const s=wb.worksheets.add("S");
s.getRange("A1:B5").values=[["Month","NAV"],["Jan",1],["Feb",1.1],["Mar",null],["Apr",null]];
s.getRange("B4:B5").formulas=[["=NA()"],["=NA()"]];
const c=s.charts.add("line",s.getRange("A1:B5"));c.title="Test NA";c.setPosition("A8:H20");
const p=await wb.render({sheetName:"S",range:"A1:H21",format:"png"});await fs.writeFile("na_chart.png",new Uint8Array(await p.arrayBuffer()));
const x=await SpreadsheetFile.exportXlsx(wb);await x.save("na_chart.xlsx");
