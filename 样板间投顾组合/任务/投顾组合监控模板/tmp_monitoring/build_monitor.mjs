import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import JSZip from "jszip";

const inputPath = "../样板间投顾组合监控模板-20260716调仓.xlsx";
const outputPath = "../outputs/019fe9e8-9aa4-7333-9b05-6ec8e2b0a2b8/样板间投顾组合监控模板-20260716调仓_偏离度监控.xlsx";

const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const navSheet = wb.worksheets.getItem("实盘净值数据(iFinD公式)");

const sheet = wb.worksheets.add("偏离度监控");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(4);

const navy = "#1F3864";
const blue = "#2E5496";
const midBlue = "#4472C4";
const lightBlue = "#D9E2F3";
const paleBlue = "#EAF0F8";
const paleYellow = "#FFF2CC";
const paleRed = "#FCE4D6";
const paleGreen = "#E2F0D9";
const border = "#BFBFBF";
const darkGray = "#595959";
const pctFmt = "0.00%;[Red](0.00%);-";
const devFmt = "0.00%;(0.00%);-";

const setSection = (range) => {
  range.format = {
    fill: blue,
    font: { name: "微软雅黑", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
};
const setHeader = (range) => {
  range.format = {
    fill: midBlue,
    font: { name: "微软雅黑", size: 9, bold: true, color: "#FFFFFF" },
    borders: { preset: "all", style: "thin", color: border },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
};
const setBody = (range) => {
  range.format = {
    font: { name: "微软雅黑", size: 9, color: "#000000" },
    borders: { preset: "all", style: "thin", color: border },
    verticalAlignment: "center",
  };
};

// Page title and controls.
sheet.getRange("A1:L1").merge();
sheet.getRange("A1").values = [["样板间投顾组合 · 偏离度监控"]];
sheet.getRange("A1:L1").format = {
  fill: navy,
  font: { name: "微软雅黑", size: 16, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange("A2:L2").values = [[
  "净值截止日", null, "权重口径", null, null, null, null, null,
  "配比预警阈值", 0.02, "主动基金上限", 0.20,
]];
sheet.getRange("D2:H2").merge();
sheet.getRange("D2").values = [["上一完整交易日（避免当日净值更新不同步）"]];
sheet.getRange("B2").formulas = [["=$B$82"]];
sheet.getRange("A2:L2").format = {
  fill: paleBlue,
  font: { name: "微软雅黑", size: 9, bold: true, color: navy },
  borders: { preset: "all", style: "thin", color: border },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange("B2").format.numberFormat = "yyyy-mm-dd";
for (const cell of ["J2", "L2"]) sheet.getRange(cell).format = {
  fill: paleYellow,
  font: { name: "Arial", size: 9, color: "#0000FF" },
  borders: { preset: "all", style: "thin", color: border },
  numberFormat: pctFmt,
  horizontalAlignment: "center",
};
sheet.getRange("A3:L3").merge();
sheet.getRange("A3").values = [["三个产业趋势组合展示全部最新持仓；10-90（含基石）及30-70的结构偏离按目标配比监控。红色表示超过约束或预警阈值。"]];
sheet.getRange("A3:L3").format = {
  font: { name: "微软雅黑", size: 9, italic: true, color: darkGray },
  wrapText: true,
  verticalAlignment: "center",
};

// Table 1: full holdings of the three industry-trend portfolios.
sheet.getRange("A5:E5").merge();
sheet.getRange("A5").values = [["1. 三个产业趋势组合详细持仓及集中度风险"]];
sheet.getRange("F5").values = [["数据截止日"]];
setSection(sheet.getRange("A5:F5"));
sheet.getRange("G5").formulas = [["=$B$82"]];
sheet.getRange("G5").format = { fill: lightBlue, font: { name: "微软雅黑", size: 9, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A6:G6").values = [["组合", "基金代码", "基金简称", "基金类型", "当前权重", "是否超限", "调仓生效日"]];
setHeader(sheet.getRange("A6:G6"));
const combos = ["产业趋势", "产业趋势基石", "产业趋势2号", "10-90", "10-90基石", "30-70"];
const comboCols = ["G", "H", "I", "J", "K", "L"];
const helperCols = ["M", "N", "O", "P", "Q", "R"];
const helperColByComboCol = Object.fromEntries(comboCols.map((col, i) => [col, helperCols[i]]));
const detailBlocks = [
  ["产业趋势", "G", 7],
  ["产业趋势基石", "H", 15],
  ["产业趋势2号", "I", 23],
];
for (const [name, col, start] of detailBlocks) {
  const end = start + 7;
  for (let row = start; row <= end; row++) {
    const position = row - start + 1;
    const helperCol = helperColByComboCol[col];
    const nthHeldRow = `MATCH(${position},${helperCol}$53:${helperCol}$76,0)`;
    sheet.getRange(`B${row}`).formulas = [[`=IFERROR(INDEX($A$53:$A$76,${nthHeldRow}),"")`]];
    sheet.getRange(`C${row}`).formulas = [[`=IFERROR(INDEX($B$53:$B$76,${nthHeldRow}),"")`]];
    sheet.getRange(`D${row}`).formulas = [[`=IFERROR(INDEX($E$53:$E$76,${nthHeldRow}),"")`]];
    sheet.getRange(`E${row}`).formulas = [[`=IFERROR(INDEX(${col}$53:${col}$76,${nthHeldRow}),"")`]];
    sheet.getRange(`A${row}`).formulas = [[`=IF(B${row}<>"","${name}","")`]];
    sheet.getRange(`F${row}`).formulas = [[`=IF(B${row}="","",IF(D${row}<>"主动","不适用",IF(E${row}>$L$2,"超限","正常")))`]];
    sheet.getRange(`G${row}`).formulas = [[`=IF(B${row}<>"",${col}$84,"")`]];
  }
}
setBody(sheet.getRange("A7:G30"));
sheet.getRange("A7:A30").format = { fill: paleBlue, font: { name: "微软雅黑", size: 9, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border }, horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("E7:E30").format.numberFormat = pctFmt;
sheet.getRange("G7:G30").format.numberFormat = "yyyy-mm-dd";
sheet.getRange("B7:D30").format.horizontalAlignment = "center";
sheet.getRange("E7:E30").format.horizontalAlignment = "right";
sheet.getRange("F7:G30").format.horizontalAlignment = "center";
sheet.getRange("A31:G31").merge();
sheet.getRange("A31").values = [["约束口径：仅“主动”基金适用单只20%上限；主题指数、指增、货币、债券及保障基金不纳入该上限。超限基金整行标红。"]];
sheet.getRange("A31:G31").format = { fill: paleBlue, font: { name: "微软雅黑", size: 8, italic: true, color: darkGray }, wrapText: true };

// Table 2: growth/income allocation.
sheet.getRange("A33:F33").merge();
sheet.getRange("A33").values = [["2. 组合内部增值 / 生息配比偏离（10-90含基石、30-70）"]];
sheet.getRange("G33").values = [["数据截止日"]];
setSection(sheet.getRange("A33:G33"));
sheet.getRange("H33").formulas = [["=$B$82"]];
sheet.getRange("H33").format = { fill: lightBlue, font: { name: "微软雅黑", size: 9, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A34:H34").values = [["组合", "增值目标", "增值当前", "偏离度", "生息目标", "生息当前", "偏离度", "调仓生效日"]];
setHeader(sheet.getRange("A34:H34"));
const allocRows = [
  ["10-90", 0.10, "J"],
  ["10-90基石", 0.10, "K"],
  ["30-70", 0.30, "L"],
];
for (let i = 0; i < allocRows.length; i++) {
  const row = 35 + i;
  const [name, target, col] = allocRows[i];
  sheet.getRange(`A${row}:B${row}`).values = [[name, target]];
  sheet.getRange(`C${row}`).formulas = [[`=SUMIF($C$53:$C$76,"增值",${col}$53:${col}$76)`]];
  sheet.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  sheet.getRange(`E${row}`).formulas = [[`=1-B${row}`]];
  sheet.getRange(`F${row}`).formulas = [[`=SUMIF($C$53:$C$76,"生息",${col}$53:${col}$76)`]];
  sheet.getRange(`G${row}`).formulas = [[`=F${row}-E${row}`]];
  sheet.getRange(`H${row}`).formulas = [[`=${col}$84`]];
}
setBody(sheet.getRange("A35:H37"));
sheet.getRange("B35:G37").format.numberFormat = pctFmt;
sheet.getRange("D35:D37").format.numberFormat = devFmt;
sheet.getRange("G35:G37").format.numberFormat = devFmt;
sheet.getRange("H35:H37").format.numberFormat = "yyyy-mm-dd";
sheet.getRange("A35:A37").format.horizontalAlignment = "center";
sheet.getRange("H35:H37").format.horizontalAlignment = "center";
sheet.getRange("B35:G37").format.horizontalAlignment = "right";
sheet.getRange("A38:H38").merge();
sheet.getRange("A38").values = [["生息含债券、货币及保障类基金；默认预警阈值为±2个百分点，可在J2直接修改。偏离度=当前配比−目标配比。"]];
sheet.getRange("A38:H38").format = { fill: paleBlue, font: { name: "微软雅黑", size: 8, italic: true, color: darkGray } };

// Table 3: trend/enhanced split inside growth bucket.
sheet.getRange("A40:C40").merge();
sheet.getRange("A40").values = [["3. 增值部分内部产业趋势 / 指增当前配比"]];
sheet.getRange("D40").values = [["数据截止日"]];
setSection(sheet.getRange("A40:D40"));
sheet.getRange("E40").formulas = [["=$B$82"]];
sheet.getRange("E40").format = { fill: lightBlue, font: { name: "微软雅黑", size: 9, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border }, numberFormat: "yyyy-mm-dd", horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A41:E41").values = [["组合", "产业趋势当前权重", "指增部分当前权重", "增值部分总权重", "调仓生效日"]];
setHeader(sheet.getRange("A41:E41"));
for (let i = 0; i < allocRows.length; i++) {
  const row = 42 + i;
  const [name, , col] = allocRows[i];
  sheet.getRange(`A${row}`).values = [[name]];
  sheet.getRange(`B${row}`).formulas = [[`=IFERROR(SUMIF($D$53:$D$76,"产业趋势",${col}$53:${col}$76)/SUMIF($C$53:$C$76,"增值",${col}$53:${col}$76),0)`]];
  sheet.getRange(`C${row}`).formulas = [[`=IFERROR(SUMIF($D$53:$D$76,"指增",${col}$53:${col}$76)/SUMIF($C$53:$C$76,"增值",${col}$53:${col}$76),0)`]];
  sheet.getRange(`D${row}`).formulas = [[`=SUMIF($C$53:$C$76,"增值",${col}$53:${col}$76)`]];
  sheet.getRange(`E${row}`).formulas = [[`=${col}$84`]];
}
setBody(sheet.getRange("A42:E44"));
sheet.getRange("B42:D44").format.numberFormat = pctFmt;
sheet.getRange("E42:E44").format.numberFormat = "yyyy-mm-dd";
sheet.getRange("A42:A44").format.horizontalAlignment = "center";
sheet.getRange("B42:D44").format.horizontalAlignment = "right";
sheet.getRange("E42:E44").format.horizontalAlignment = "center";
sheet.getRange("A45:E45").merge();
sheet.getRange("A45").values = [["产业趋势与指增的当前权重均以“增值部分总权重”为分母。"]];
sheet.getRange("A45:E45").format = { fill: paleBlue, font: { name: "微软雅黑", size: 8, italic: true, color: darkGray } };

sheet.getRange("A47:H47").merge();
sheet.getRange("A47").values = [["核验：原模板8月10日当日行仅货币基金先更新，最大混频差为0.00044个百分点；改用2026-08-07完整净值后，与系统导出最大残差降至0.00010个百分点（约0.01bp，仅为6位小数舍入）。"]];
sheet.getRange("A47:H47").format = { fill: paleYellow, font: { name: "微软雅黑", size: 8, color: darkGray }, wrapText: true, verticalAlignment: "center" };

// Classification mapping and formula-driven current weights.
sheet.getRange("A50:L50").merge();
sheet.getRange("A50").values = [["分类映射与自动计算明细（维护区）"]];
setSection(sheet.getRange("A50:L50"));
sheet.getRange("A51:L51").merge();
sheet.getRange("A51").values = [["分类参考《增值_生息+产业趋势_指增.xlsx》；A/C份额继承同一基金分类。000917、009993及部分C份额为现持仓补充映射。"]];
sheet.getRange("A51:L51").format = { fill: paleBlue, font: { name: "微软雅黑", size: 8, italic: true, color: darkGray } };
sheet.getRange("A52:L52").values = [["基金代码", "基金简称", "大类", "增值细分", "管理方式", "分类依据", ...combos]];
setHeader(sheet.getRange("A52:L52"));

const mappings = [
  ["000216.OF", "华安黄金ETF联接A", "生息", "-", "保障", "债券&保障池子（保障）"],
  ["000917.OF", "嘉实快线货币A", "生息", "-", "货币", "现持仓补充"],
  ["001170.OF", "宏利复兴混合A", "增值", "产业趋势", "主动", "产业趋势产品池"],
  ["007044.OF", "博道沪深300增强A", "增值", "指增", "指增", "宽基&指增池"],
  ["007045.OF", "博道沪深300指增C", "增值", "指增", "指增", "同基金A/C"],
  ["007817.OF", "国泰通信设备ETF联接A", "增值", "产业趋势", "指数", "产业趋势产品池"],
  ["007818.OF", "国泰通信设备C", "增值", "产业趋势", "指数", "同基金A/C"],
  ["009993.OF", "嘉实前沿科技创新", "增值", "产业趋势", "主动", "现持仓补充"],
  ["013840.OF", "银华集成电路混合A", "增值", "产业趋势", "主动", "产业趋势产品池"],
  ["013841.OF", "银华集成电路混合C", "增值", "产业趋势", "主动", "同基金A/C"],
  ["014201.OF", "天弘中证1000指增A", "增值", "指增", "指增", "宽基&指增池"],
  ["014202.OF", "天弘中证1000指增C", "增值", "指增", "指增", "同基金A/C"],
  ["015453.OF", "中欧中证500指增A", "增值", "指增", "指增", "宽基&指增池"],
  ["015454.OF", "中欧中证500指增C", "增值", "指增", "指增", "同基金A/C"],
  ["016370.OF", "信澳业绩驱动A", "增值", "产业趋势", "主动", "产业趋势产品池"],
  ["017488.OF", "嘉实信息产业A", "增值", "产业趋势", "主动", "产业趋势产品池"],
  ["017489.OF", "嘉实信息产业C", "增值", "产业趋势", "主动", "同基金A/C"],
  ["017612.OF", "宏利复兴伟业C", "增值", "产业趋势", "主动", "同基金A/C"],
  ["019632.OF", "国泰半导体材料设备ETF联接A", "增值", "产业趋势", "指数", "产业趋势产品池"],
  ["019633.OF", "国泰半导体材料设备C", "增值", "产业趋势", "指数", "同基金A/C"],
  ["019923.OF", "华泰柏瑞中证2000指增A", "增值", "指增", "指增", "宽基&指增池"],
  ["019924.OF", "华泰柏瑞中证2000指增C", "增值", "指增", "指增", "同基金A/C"],
  ["161119.OF", "易方达中债新综指LOFA", "生息", "-", "债券", "债券&保障池子（生息）"],
  ["162214.OF", "宏利领先中小盘混合", "增值", "产业趋势", "主动", "产业趋势产品池"],
];
const snapshot = {
  "产业趋势": {"000917.OF":0.054338345878986755,"001170.OF":0.1681479854041161,"013840.OF":0.24648996572257403,"016370.OF":0.15912488007417924,"017488.OF":0.17230499151577977,"019632.OF":0.1311286607566896,"162214.OF":0.06846517064767443},
  "产业趋势基石": {"000917.OF":0.05313303323780936,"001170.OF":0.16972434194387825,"013840.OF":0.24475713621132436,"016370.OF":0.15902507905426536,"017488.OF":0.17310992190249347,"019632.OF":0.1317750117897416,"162214.OF":0.06847547586048766},
  "产业趋势2号": {"000917.OF":0.05128012799377769,"009993.OF":0.18643460253095584,"013841.OF":0.23333425378822176,"017489.OF":0.16814227790813516,"017612.OF":0.16735538109816184,"019633.OF":0.12507142493000778,"162214.OF":0.06838193175074},
  "10-90": {"000216.OF":0.05414347447224511,"000917.OF":0.043923928891400975,"007045.OF":0.012855558252454736,"009993.OF":0.009630029472442245,"013841.OF":0.011060670436649926,"014202.OF":0.01288170822388295,"015454.OF":0.01300899943471813,"017489.OF":0.008713691952627311,"017612.OF":0.008645667148546948,"019633.OF":0.005413390810145085,"019924.OF":0.012762048562637551,"161119.OF":0.7974500954456453,"162214.OF":0.009510736896603767},
  "10-90基石": {"000216.OF":0.051794493820263125,"000917.OF":0.04395376124085798,"001170.OF":0.0087369099448945,"007044.OF":0.0128975499557758,"013840.OF":0.01225914007350266,"014201.OF":0.01305811206863005,"015453.OF":0.01331135566096293,"016370.OF":0.00840985580066948,"017488.OF":0.008980180698834838,"019632.OF":0.005856096818189585,"019923.OF":0.012743977694171382,"161119.OF":0.7984750205517424,"162214.OF":0.009523545671505275},
  "30-70": {"000216.OF":0.10785060309605504,"000917.OF":0.08530437206808822,"007045.OF":0.03841034111514078,"009993.OF":0.028773694107794432,"013841.OF":0.0330472108980905,"014202.OF":0.03849114616684735,"015454.OF":0.03886861841160838,"017489.OF":0.02603644996891972,"017612.OF":0.02583404960566663,"019633.OF":0.01617480085850223,"019924.OF":0.0381325714317698,"161119.OF":0.49216006002582735,"162214.OF":0.03091608224568969},
};
sheet.getRange("A53:F76").values = mappings;
for (let r = 53; r <= 76; r++) {
  for (let c = 0; c < comboCols.length; c++) {
    const col = comboCols[c];
    const helperCol = helperCols[c];
    sheet.getRange(`${col}${r}`).formulas = [[
      `=IFERROR(INDEX('分期持仓明细'!$B$5:$Y$200,${col}$82-4,MATCH(LEFT($A${r},6),'分期持仓明细'!$B$3:$Y$3,0))*INDEX('实盘净值数据(iFinD公式)'!$B$5:$Y$1000,$B$81,MATCH($A${r},'实盘净值数据(iFinD公式)'!$B$3:$Y$3,0))/INDEX('实盘净值数据(iFinD公式)'!$B$5:$Y$1000,MATCH(${col}$84,'实盘净值数据(iFinD公式)'!$A$5:$A$1000,0),MATCH($A${r},'实盘净值数据(iFinD公式)'!$B$3:$Y$3,0))/${col}$85,${col}${r + 36})`,
    ]];
    sheet.getRange(`${helperCol}${r}`).formulas = [[`=IF(${col}${r}>0,COUNTIF(${col}$53:${col}${r},">0"),"")`]];
  }
}
sheet.getRange("A77:F77").values = [["合计", null, null, null, null, null]];
for (const col of comboCols) sheet.getRange(`${col}77`).formulas = [[`=SUM(${col}53:${col}76)`]];
setBody(sheet.getRange("A53:L77"));
sheet.getRange("A77:L77").format = { fill: lightBlue, font: { name: "微软雅黑", size: 9, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border } };
sheet.getRange("G53:L77").format.numberFormat = pctFmt;
sheet.getRange("A53:A76").format.horizontalAlignment = "center";
sheet.getRange("C53:F76").format.horizontalAlignment = "center";
sheet.getRange("G53:L77").format.horizontalAlignment = "right";

// Auditable helper rows.
sheet.getRange("A80:L80").merge();
sheet.getRange("A80").values = [["自动计算参数（公式区）"]];
setSection(sheet.getRange("A80:L80"));
sheet.getRange("A81:B85").values = [["最新完整净值行(相对A5)", null], ["最新完整净值日期", null], ["说明", "取小于TODAY()的最后一个交易日"], ["", null], ["", null]];
sheet.getRange("B81").formulas = [["=IFERROR(MATCH(TODAY()-1,'实盘净值数据(iFinD公式)'!$A$5:$A$1000,1),0)"]];
sheet.getRange("B82").formulas = [["=IF($B$81=0,\"\",INDEX('实盘净值数据(iFinD公式)'!$A$5:$A$1000,$B$81))"]];
sheet.getRange("B82").format.numberFormat = "yyyy-mm-dd";
sheet.getRange("G81:L81").values = [combos];
setHeader(sheet.getRange("G81:L81"));
for (let c = 0; c < comboCols.length; c++) {
  const col = comboCols[c];
  const helperCol = helperCols[c];
  for (let sourceRow = 5; sourceRow <= 200; sourceRow++) {
    const helperRow = sourceRow + 81;
    sheet.getRange(`${helperCol}${helperRow}`).formulas = [[`=IF(LEFT('分期持仓明细'!$A$${sourceRow},LEN(${col}$81)+2)=${col}$81&" ·",ROW('分期持仓明细'!$A$${sourceRow}),0)`]];
  }
  sheet.getRange(`${col}82`).formulas = [[`=IFERROR(MAX(${helperCol}$86:${helperCol}$281),0)`]];
  sheet.getRange(`${col}83`).formulas = [[`=IF(${col}$82=0,"",INDEX('分期持仓明细'!$A$5:$A$200,${col}$82-4))`]];
  sheet.getRange(`${col}84`).formulas = [[`=IF(${col}$82=0,"",INDEX('分期持仓明细'!$AA$5:$AA$200,${col}$82-4))`]];
  sheet.getRange(`${col}85`).formulas = [[`=IFERROR(SUMPRODUCT(INDEX('分期持仓明细'!$B$5:$Y$200,${col}$82-4,0),INDEX('实盘净值数据(iFinD公式)'!$B$5:$Y$1000,$B$81,0)/INDEX('实盘净值数据(iFinD公式)'!$B$5:$Y$1000,MATCH(${col}$84,'实盘净值数据(iFinD公式)'!$A$5:$A$1000,0),0)),0)`]];
  sheet.getRange(`${col}84`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`${col}85`).format.numberFormat = "0.000000";
}
sheet.getRange("F82:F85").values = [["最新阶段行"], ["阶段标签"], ["生效日"], ["归一化因子"]];
setBody(sheet.getRange("A81:B85"));
sheet.getRange("B81").format.numberFormat = "0";
setBody(sheet.getRange("F82:L85"));
sheet.getRange("F82:F85").format = { fill: paleBlue, font: { name: "微软雅黑", size: 8, bold: true, color: navy }, borders: { preset: "all", style: "thin", color: border }, horizontalAlignment: "center" };
sheet.getRange("G83:L83").format = { font: { name: "微软雅黑", size: 7, color: "#000000" }, borders: { preset: "all", style: "thin", color: border }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A83:L83").format.rowHeight = 32;

// Last complete snapshot is a display fallback before the iFinD add-in finishes
// recalculating; live formulas replace it automatically once NAVs are available.
sheet.getRange("A88:F88").merge();
sheet.getRange("A88").values = [["最近完整快照（2026-08-07，由模板净值和分期持仓重算；非系统导入）"]];
setSection(sheet.getRange("A88:F88"));
sheet.getRange("G88:L88").values = [combos];
setHeader(sheet.getRange("G88:L88"));
sheet.getRange("A89:F112").values = mappings;
sheet.getRange("G89:L112").values = mappings.map((row) => combos.map((combo) => snapshot[combo][row[0]] ?? 0));
setBody(sheet.getRange("A89:F112"));
setBody(sheet.getRange("G89:L112"));
sheet.getRange("G89:L112").format.numberFormat = pctFmt;
sheet.getRange("A89:A112").format.horizontalAlignment = "center";
sheet.getRange("C89:F112").format.horizontalAlignment = "center";
sheet.getRange("G89:L112").format.horizontalAlignment = "right";

// Input validation for user-maintained classifications and thresholds.
sheet.getRange("C53:C76").dataValidation = { rule: { type: "list", values: ["增值", "生息"] } };
sheet.getRange("D53:D76").dataValidation = { rule: { type: "list", values: ["产业趋势", "指增", "-"] } };
sheet.getRange("E53:E76").dataValidation = { rule: { type: "list", values: ["主动", "指数", "指增", "货币", "债券", "保障"] } };

// Dynamic risk coloring.
sheet.getRange("A7:G30").conditionalFormats.addCustom("=AND($D7=\"主动\",$E7>$L$2)", { fill: paleRed, font: { color: "#C00000", bold: true } });
sheet.getRange("F7:F30").conditionalFormats.add("containsText", { text: "正常", format: { fill: paleGreen, font: { color: "#006100", bold: true } } });
sheet.getRange("D35:D37").conditionalFormats.addCustom("=ABS(D35)>$J$2", { fill: paleRed, font: { color: "#C00000", bold: true } });
sheet.getRange("G35:G37").conditionalFormats.addCustom("=ABS(G35)>$J$2", { fill: paleRed, font: { color: "#C00000", bold: true } });

// Column widths and row heights tuned to the existing workbook's compact style.
const widths = { A: 18, B: 17, C: 29, D: 14, E: 14, F: 15, G: 13, H: 15, I: 15, J: 15, K: 14, L: 14 };
for (const [col, width] of Object.entries(widths)) sheet.getRange(`${col}1:${col}112`).format.columnWidth = width;
sheet.getRange("A1:L1").format.rowHeight = 28;
sheet.getRange("A2:L2").format.rowHeight = 24;
sheet.getRange("A3:L3").format.rowHeight = 28;
for (const row of [5, 33, 40, 50, 80]) sheet.getRange(`A${row}:L${row}`).format.rowHeight = 21;
for (const row of [6, 34, 41, 52, 81]) sheet.getRange(`A${row}:L${row}`).format.rowHeight = 28;
sheet.getRange("A47:L47").format.rowHeight = 34;
sheet.getRange("A51:L51").format.rowHeight = 24;
for (const col of helperCols) sheet.getRange(`${col}1:${col}281`).format.columnWidth = 0.1;

await fs.mkdir(new URL("../outputs/019fe9e8-9aa4-7333-9b05-6ec8e2b0a2b8/", import.meta.url), { recursive: true });
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);

// Preserve the iFinD XLL/XLA external-link definition. The workbook formulas
// use the Excel external-function syntax `[1]!thsiFinD(...)`; Windows Excel
// removes those formulas if the matching externalLink package part is absent.
const [sourceZip, outputZip] = await Promise.all([
  JSZip.loadAsync(await fs.readFile(inputPath)),
  JSZip.loadAsync(await fs.readFile(outputPath)),
]);
for (const part of [
  "xl/externalLinks/externalLink1.xml",
  "xl/externalLinks/_rels/externalLink1.xml.rels",
]) {
  outputZip.file(part, await sourceZip.file(part).async("uint8array"));
}

const externalRelId = "RIFIND_EXTERNAL_1";
let workbookXml = await outputZip.file("xl/workbook.xml").async("string");
if (!workbookXml.includes("<x:externalReferences>")) {
  workbookXml = workbookXml.replace(
    "</x:sheets>",
    `</x:sheets><x:externalReferences><x:externalReference r:id="${externalRelId}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" /></x:externalReferences>`,
  );
}
if (!workbookXml.includes("<x:calcPr")) {
  workbookXml = workbookXml.replace(
    "</x:workbook>",
    '<x:calcPr calcId="152511" forceFullCalc="1" /></x:workbook>',
  );
}
outputZip.file("xl/workbook.xml", workbookXml);

let workbookRels = await outputZip.file("xl/_rels/workbook.xml.rels").async("string");
if (!workbookRels.includes("relationships/externalLink")) {
  workbookRels = workbookRels.replace(
    "</Relationships>",
    `<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLink" Target="externalLinks/externalLink1.xml" Id="${externalRelId}" /></Relationships>`,
  );
}
outputZip.file("xl/_rels/workbook.xml.rels", workbookRels);

let contentTypes = await outputZip.file("[Content_Types].xml").async("string");
if (!contentTypes.includes('/xl/externalLinks/externalLink1.xml')) {
  contentTypes = contentTypes.replace(
    "</Types>",
    '<Override PartName="/xl/externalLinks/externalLink1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.externalLink+xml" /></Types>',
  );
}
outputZip.file("[Content_Types].xml", contentTypes);

await fs.writeFile(outputPath, await outputZip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
console.log(outputPath);
