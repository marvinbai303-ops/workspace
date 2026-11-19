import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "../2080样板间测算底稿.xlsx";
const snapshotPath = "yellow_input_snapshot.json";
const outputDir = "../outputs/2080_backtest_20260901";
const outputPath = `${outputDir}/2080样板间回测模型.xlsx`;
const previewDir = "final_previews";
const sheetName = "2080回测";
const firstDataRow = 46;
const sourceFirstRow = 4;

const snapshot = JSON.parse(await fs.readFile(snapshotPath, "utf8"));
const lastDataRow = firstDataRow + snapshot.length - 1;
const sourceLastRow = sourceFirstRow + snapshot.length - 1;
const monthCount = 80;
const monthHelperLastRow = firstDataRow + monthCount - 1;

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const input = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(input);
const source = workbook.worksheets.getItem("净值底稿");

// The original P/Q cells contain iFinD add-in formulas. Freeze their cached
// numeric values in the deliverable so the backtest remains portable and
// recalculates without the add-in; the source file itself is not modified.
source.getRange(`P${sourceFirstRow}:Q${sourceLastRow}`).values = snapshot.map((row) => [
  row.bond_nav,
  row.gold_nav,
]);
source.getRange(`P${sourceFirstRow}:Q${sourceLastRow}`).format.numberFormat = "0.0000";

const sheet = workbook.worksheets.add(sheetName);
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(4);
sheet.freezePanes.freezeColumns(1);

const darkBlue = "#2F5597";
const blue = "#4472C4";
const paleBlue = "#D9EAF7";
const paleYellow = "#FFF2CC";
const paleGreen = "#E2F0D9";
const paleRed = "#FCE4D6";
const green = "#008000";
const red = "#C00000";
const gray = "#666666";
const lightBorder = "#B4C6E7";

sheet.getRange("A1:U1").merge();
sheet.getRange("A1").values = [["2080组合回测｜可编辑公式模型"]];
sheet.getRange("A1:U1").format = {
  fill: darkBlue,
  font: { bold: true, color: "#FFFFFF", fontSize: 16, typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange("A1:U1").format.rowHeight = 30;

sheet.getRange("A2:U2").merge();
sheet.getRange("A2").formulas = [[
  `="数据区间："&TEXT($A$${firstDataRow},"yyyy-mm-dd")&" 至 "&TEXT($A$${lastDataRow},"yyyy-mm-dd")&"｜黄色输入列：净值底稿 F / O / P / Q｜净值基准：费后"`,
]];
sheet.getRange("A2:U2").format = {
  fill: "#EAF2F8",
  font: { color: darkBlue, italic: true, fontSize: 10, typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange("A2:U2").format.rowHeight = 22;

const sectionHeaderFormat = {
  fill: blue,
  font: { bold: true, color: "#FFFFFF", fontSize: 11, typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: blue },
};

for (const [range, label] of [
  ["A4:B4", "初始配置"],
  ["D4:E4", "再平衡参数"],
  ["G4:H4", "费率与绩效参数"],
  ["J4:U4", "模型检查与口径"],
]) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[label]];
  sheet.getRange(range).format = sectionHeaderFormat;
}

sheet.getRange("A5:A8").values = [["产业趋势"], ["指增组合"], ["中债新综合"], ["华安黄金"]];
sheet.getRange("B5:B8").values = [[0.10], [0.10], [0.75], [0.05]];
sheet.getRange("D5:D8").values = [["权益目标权重"], ["权益下限"], ["权益上限"], ["最短间隔（日）"]];
sheet.getRange("E5:E8").values = [[0.20], [0.15], [0.25], [7]];
sheet.getRange("G5:G8").values = [["年化费率"], ["年化交易日"], ["无风险收益率"], ["计费日基准"]];
sheet.getRange("H5:H8").values = [[0.005], [250], [0], [365]];

for (const range of ["B5:B8", "E5:E8", "H5:H8"]) {
  sheet.getRange(range).format = {
    fill: paleYellow,
    font: { color: "#0000FF", typeface: "宋体" },
    horizontalAlignment: "right",
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: lightBorder },
  };
}
sheet.getRange("B5:B8").format.numberFormat = "0.00%";
sheet.getRange("E5:E7").format.numberFormat = "0.00%";
sheet.getRange("E8").format.numberFormat = "0";
sheet.getRange("H5").format.numberFormat = "0.00%";
sheet.getRange("H6").format.numberFormat = "0";
sheet.getRange("H7").format.numberFormat = "0.00%";
sheet.getRange("H8").format.numberFormat = "0";

for (const range of ["A5:A8", "D5:D8", "G5:G8"]) {
  sheet.getRange(range).format = {
    fill: "#F7F9FB",
    font: { color: "#333333", typeface: "宋体" },
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: lightBorder },
  };
}

sheet.getRange("B5:B8").dataValidation = { rule: { type: "decimal", operator: "between", formula1: 0, formula2: 1 } };
sheet.getRange("E5:E7").dataValidation = { rule: { type: "decimal", operator: "between", formula1: 0, formula2: 1 } };
sheet.getRange("E8").dataValidation = { rule: { type: "whole", operator: "between", formula1: 0, formula2: 365 } };
sheet.getRange("H5").dataValidation = { rule: { type: "decimal", operator: "between", formula1: 0, formula2: 0.20 } };
sheet.getRange("H6").dataValidation = { rule: { type: "whole", operator: "between", formula1: 1, formula2: 366 } };
sheet.getRange("H7").dataValidation = { rule: { type: "decimal", operator: "between", formula1: -0.20, formula2: 0.50 } };
sheet.getRange("H8").dataValidation = { rule: { type: "whole", operator: "between", formula1: 300, formula2: 366 } };

sheet.getRange("J5:J8").values = [["初始权重合计"], ["阈值关系"], ["黄色数据完整性"], ["模型状态"]];
sheet.getRange("K5").formulas = [["=SUM($B$5:$B$8)"]];
sheet.getRange("K6").formulas = [["=AND($E$6<$E$5,$E$5<$E$7)"]];
sheet.getRange("K7").formulas = [[`=AND(COUNT($B$${firstDataRow}:$E$${lastDataRow})=ROWS($B$${firstDataRow}:$B$${lastDataRow})*4,MIN($B$${firstDataRow}:$E$${lastDataRow})>0)`]];
sheet.getRange("K8").formulas = [["=IF(AND(ABS($K$5-1)<0.0000001,$K$6,$K$7),\"OK\",\"检查参数/数据\")"]];
sheet.getRange("L5:L8").values = [["应为100%"], ["下限 < 目标 < 上限"], ["四列全为正数"], ["仅OK时使用结果"]];
sheet.getRange("J5:L8").format = {
  borders: { preset: "all", style: "thin", color: lightBorder },
  verticalAlignment: "center",
  font: { typeface: "宋体" },
};
sheet.getRange("K5").format.numberFormat = "0.00%";
sheet.getRange("K5:K8").format.fill = paleGreen;
sheet.getRange("K5:K8").format.horizontalAlignment = "center";
sheet.getRange("K8").conditionalFormats.add("containsText", { text: "OK", format: { fill: paleGreen, font: { color: green, bold: true } } });
sheet.getRange("K8").conditionalFormats.add("containsText", { text: "检查", format: { fill: paleRed, font: { color: red, bold: true } } });

sheet.getRange("N5:U8").merge();
sheet.getRange("N5").values = [[
  "口径：日终先根据资产涨跌计算调前权重，再判断年末、季末与15%/25%动态阈值。动态触发后权益合计回到目标权重，两只权益策略按触发当日比例缩放；季末再校准为1:1。年末与季末同日合并为一次调仓。中债/黄金不做内部定期再平衡，外层调整时保留当日相对比例。",
]];
sheet.getRange("N5:U8").format = {
  fill: "#F2F2F2",
  font: { color: "#404040", fontSize: 9, typeface: "宋体" },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: lightBorder },
};

sheet.getRange("A10:U10").merge();
sheet.getRange("A10").values = [[
  "可编辑说明：黄底蓝字为参数输入；绿字为对“净值底稿”的链接；黑字为计算公式。绩效及图表会随参数自动更新。",
]];
sheet.getRange("A10:U10").format = {
  fill: paleBlue,
  font: { color: darkBlue, fontSize: 9, typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: lightBorder },
};

sheet.getRange("Q12:U12").merge();
sheet.getRange("Q12").values = [["绩效表"]];
sheet.getRange("Q12:U12").format = sectionHeaderFormat;
sheet.getRange("Q13:S13").values = [["指标", "结果", "计算口径"]];
sheet.getRange("Q13:S13").format = {
  fill: paleBlue,
  font: { bold: true, color: darkBlue, typeface: "宋体" },
  horizontalAlignment: "center",
  borders: { preset: "all", style: "thin", color: lightBorder },
};
sheet.getRange("Q14:Q19").values = [["累计收益率"], ["算术年化收益率"], ["年化波动率"], ["最大回撤"], ["Sharpe Ratio"], ["Calmar Ratio"]];
sheet.getRange("R14").formulas = [[`=$AD$${lastDataRow}/$AD$${firstDataRow}-1`]];
sheet.getRange("R15").formulas = [[`=AVERAGE($AG$${firstDataRow + 1}:$AG$${lastDataRow})*$H$6`]];
sheet.getRange("R16").formulas = [[`=STDEV.S($AG$${firstDataRow + 1}:$AG$${lastDataRow})*SQRT($H$6)`]];
sheet.getRange("R17").formulas = [[`=MIN($AF$${firstDataRow}:$AF$${lastDataRow})`]];
sheet.getRange("R18").formulas = [["=IFERROR((R15-$H$7)/R16,\"\")"]];
sheet.getRange("R19").formulas = [[`=IFERROR((POWER($AD$${lastDataRow}/$AD$${firstDataRow},$H$8/($A$${lastDataRow}-$A$${firstDataRow}))-1)/ABS(R17),"")`]];
sheet.getRange("S14:S19").values = [["期末净值/期初净值-1"], ["日收益均值×年化交易日"], ["日收益标准差×√年化交易日"], ["日净值相对历史峰值的最小值"], ["(算术年化-无风险)/年化波动"], ["CAGR / |最大回撤|"]];
sheet.getRange("Q14:S19").format = {
  borders: { preset: "all", style: "thin", color: lightBorder },
  verticalAlignment: "center",
  font: { typeface: "宋体" },
};
sheet.getRange("R14:R17").format.numberFormat = "0.00%;[Red](0.00%);-";
sheet.getRange("R18:R19").format.numberFormat = "0.00x;[Red](0.00x);-";
sheet.getRange("R14:R19").format.font = { bold: true, color: darkBlue, typeface: "宋体" };

sheet.getRange("Q21:U21").merge();
sheet.getRange("Q21").values = [["再平衡统计"]];
sheet.getRange("Q21:U21").format = sectionHeaderFormat;
sheet.getRange("Q22:Q28").values = [["动态"], ["季度"], ["季度+动态"], ["年末+季度"], ["7日规则跳过"], ["期末权益权重"], ["期末费后净值"]];
sheet.getRange("R22").formulas = [[`=COUNTIF($T$${firstDataRow}:$T$${lastDataRow},"动态")`]];
sheet.getRange("R23").formulas = [[`=COUNTIF($T$${firstDataRow}:$T$${lastDataRow},"季度")`]];
sheet.getRange("R24").formulas = [[`=COUNTIF($T$${firstDataRow}:$T$${lastDataRow},"季度+动态")`]];
sheet.getRange("R25").formulas = [[`=COUNTIF($T$${firstDataRow}:$T$${lastDataRow},"年末+季度")`]];
sheet.getRange("R26").formulas = [[`=COUNTIF($T$${firstDataRow}:$T$${lastDataRow},"间隔规则跳过")`]];
sheet.getRange("R27").formulas = [[`=($Z$${lastDataRow}+$AA$${lastDataRow})/$AD$${lastDataRow}`]];
sheet.getRange("R28").formulas = [[`=$AD$${lastDataRow}`]];
sheet.getRange("Q22:R28").format = {
  borders: { preset: "all", style: "thin", color: lightBorder },
  verticalAlignment: "center",
  font: { typeface: "宋体" },
};
sheet.getRange("R22:R26").format.numberFormat = "0";
sheet.getRange("R27").format.numberFormat = "0.00%";
sheet.getRange("R28").format.numberFormat = "0.0000";

sheet.getRange("A31:P31").merge();
sheet.getRange("A31").values = [["年度收益、月度胜率与年内最大回撤"]];
sheet.getRange("A31:P31").format = sectionHeaderFormat;
sheet.getRange("A32:P32").values = [["年份", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月", "年收益", "月胜率", "最大回撤"]];
sheet.getRange("A32:P32").format = {
  fill: blue,
  font: { bold: true, color: "#FFFFFF", typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#FFFFFF" },
};

const firstYear = 2020;
const lastYear = 2026;
for (let year = firstYear; year <= lastYear; year += 1) {
  const row = 33 + (year - firstYear);
  sheet.getRange(`A${row}`).values = [[year]];
  sheet.getRange(`B${row}`).formulas = [[
    `=IF(COUNTIFS($AI$${firstDataRow}:$AI$${lastDataRow},$A${row},$AJ$${firstDataRow}:$AJ$${lastDataRow},COLUMN()-1,$AK$${firstDataRow}:$AK$${lastDataRow},1)=0,"",SUMIFS($AM$${firstDataRow}:$AM$${lastDataRow},$AI$${firstDataRow}:$AI$${lastDataRow},$A${row},$AJ$${firstDataRow}:$AJ$${lastDataRow},COLUMN()-1,$AK$${firstDataRow}:$AK$${lastDataRow},1))`,
  ]];
  sheet.getRange(`B${row}:M${row}`).fillRight();
  sheet.getRange(`N${row}`).formulas = [[`=IF(COUNT(B${row}:M${row})=0,"",PRODUCT(1+B${row}:M${row})-1)`]];
  sheet.getRange(`O${row}`).formulas = [[`=IFERROR(COUNTIF(B${row}:M${row},">0")/COUNT(B${row}:M${row}),"")`]];
  sheet.getRange(`P${row}`).formulas = [[`=IFERROR(MINIFS($AO$${firstDataRow}:$AO$${lastDataRow},$AI$${firstDataRow}:$AI$${lastDataRow},$A${row}),"")`]];
}
sheet.getRange("A40").values = [["成立以来"]];
sheet.getRange("N40").formulas = [["=$R$14"]];
sheet.getRange("O40").formulas = [[`=IFERROR(COUNTIF($AM$${firstDataRow}:$AM$${lastDataRow},">0")/COUNT($AM$${firstDataRow}:$AM$${lastDataRow}),"")`]];
sheet.getRange("P40").formulas = [["=$R$17"]];
sheet.getRange("A33:P40").format = {
  borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  verticalAlignment: "center",
  horizontalAlignment: "center",
  font: { typeface: "宋体" },
};
sheet.getRange("B33:P40").format.numberFormat = "0.00%;[Red](0.00%);-";
sheet.getRange("A40:P40").format = {
  fill: paleBlue,
  font: { bold: true, color: darkBlue, typeface: "宋体" },
  borders: { preset: "all", style: "thin", color: lightBorder },
  horizontalAlignment: "center",
};
sheet.getRange("B33:N40").conditionalFormats.add("cellIs", { operator: "greaterThan", formula: 0, format: { fill: paleRed, font: { color: red } } });
sheet.getRange("B33:N40").conditionalFormats.add("cellIs", { operator: "lessThan", formula: 0, format: { fill: paleGreen, font: { color: green } } });
sheet.getRange("P33:P40").conditionalFormats.add("cellIs", { operator: "lessThan", formula: 0, format: { fill: paleGreen, font: { color: green } } });

sheet.getRange("A43:AQ43").merge();
sheet.getRange("A43").values = [["逐日回测计算（全公式，可追溯）"]];
sheet.getRange("A43:AQ43").format = sectionHeaderFormat;
sheet.getRange("A44:AQ44").merge();
sheet.getRange("A44").values = [[
  "流程：读取黄色净值→计算单资产日收益→当日涨跌后权重→再平衡判断→持仓调整→按实际日历天数扣费→费后净值与回撤。",
]];
sheet.getRange("A44:AQ44").format = { fill: "#F2F2F2", font: { color: gray, fontSize: 9, typeface: "宋体" }, wrapText: true };

const calcHeaders = [
  "日期", "产业净值", "指增净值", "中债净值", "黄金净值",
  "产业日收益", "指增日收益", "中债日收益", "黄金日收益",
  "产业调前持仓", "指增调前持仓", "中债调前持仓", "黄金调前持仓",
  "费前组合价值", "调前权益权重", "年末标记", "季末标记", "动态触发", "间隔允许", "再平衡动作",
  "产业调后费前", "指增调后费前", "中债调后费前", "黄金调后费前", "扣费因子",
  "产业费后持仓", "指增费后持仓", "中债费后持仓", "黄金费后持仓", "费后净值",
  "历史峰值", "回撤", "组合日收益", "最近调仓日", "年", "月", "月末标记", "上月末净值", "月收益", "年内峰值", "年内回撤", "权重合计", "数据有效",
];
sheet.getRange("A45:AQ45").values = [calcHeaders];
sheet.getRange("A45:AQ45").format = {
  fill: darkBlue,
  font: { bold: true, color: "#FFFFFF", fontSize: 9, typeface: "宋体" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#FFFFFF" },
};
sheet.getRange("A45:AQ45").format.rowHeight = 36;

sheet.getRange(`A${firstDataRow}:E${firstDataRow}`).formulas = [[
  `='净值底稿'!A${sourceFirstRow}`,
  `='净值底稿'!F${sourceFirstRow}`,
  `='净值底稿'!O${sourceFirstRow}`,
  `='净值底稿'!P${sourceFirstRow}`,
  `='净值底稿'!Q${sourceFirstRow}`,
]];
sheet.getRange(`A${firstDataRow}:E${lastDataRow}`).fillDown();

sheet.getRange(`F${firstDataRow}:I${firstDataRow}`).values = [[0, 0, 0, 0]];
sheet.getRange(`F${firstDataRow + 1}:I${firstDataRow + 1}`).formulas = [[
  `=IFERROR(B${firstDataRow + 1}/B${firstDataRow}-1,0)`,
  `=IFERROR(C${firstDataRow + 1}/C${firstDataRow}-1,0)`,
  `=IFERROR(D${firstDataRow + 1}/D${firstDataRow}-1,0)`,
  `=IFERROR(E${firstDataRow + 1}/E${firstDataRow}-1,0)`,
]];
sheet.getRange(`F${firstDataRow + 1}:I${lastDataRow}`).fillDown();

sheet.getRange(`J${firstDataRow}:M${firstDataRow}`).formulas = [["=$B$5", "=$B$6", "=$B$7", "=$B$8"]];
sheet.getRange(`J${firstDataRow + 1}:M${firstDataRow + 1}`).formulas = [[
  `=Z${firstDataRow}*(1+F${firstDataRow + 1})`,
  `=AA${firstDataRow}*(1+G${firstDataRow + 1})`,
  `=AB${firstDataRow}*(1+H${firstDataRow + 1})`,
  `=AC${firstDataRow}*(1+I${firstDataRow + 1})`,
]];
sheet.getRange(`J${firstDataRow + 1}:M${lastDataRow}`).fillDown();

sheet.getRange(`N${firstDataRow}`).formulas = [[`=SUM(J${firstDataRow}:M${firstDataRow})`]];
sheet.getRange(`N${firstDataRow}:N${lastDataRow}`).fillDown();
sheet.getRange(`O${firstDataRow}`).formulas = [[`=IFERROR((J${firstDataRow}+K${firstDataRow})/N${firstDataRow},0)`]];
sheet.getRange(`O${firstDataRow}:O${lastDataRow}`).fillDown();
sheet.getRange(`P${firstDataRow}`).formulas = [[`=AND(MONTH(A${firstDataRow})=12,OR(A${firstDataRow + 1}="",YEAR(A${firstDataRow})<>YEAR(A${firstDataRow + 1})))`]];
sheet.getRange(`P${firstDataRow}:P${lastDataRow}`).fillDown();
sheet.getRange(`P${lastDataRow}`).values = [[false]];
sheet.getRange(`Q${firstDataRow}`).formulas = [[`=AND(MOD(MONTH(A${firstDataRow}),3)=0,OR(A${firstDataRow + 1}="",MONTH(A${firstDataRow})<>MONTH(A${firstDataRow + 1})))`]];
sheet.getRange(`Q${firstDataRow}:Q${lastDataRow}`).fillDown();
sheet.getRange(`Q${lastDataRow}`).values = [[false]];
sheet.getRange(`R${firstDataRow}`).formulas = [[`=OR(O${firstDataRow}>$E$7,O${firstDataRow}<$E$6)`]];
sheet.getRange(`R${firstDataRow}:R${lastDataRow}`).fillDown();
sheet.getRange(`S${firstDataRow}`).values = [[false]];
sheet.getRange(`S${firstDataRow + 1}`).formulas = [[`=AND(OR(P${firstDataRow + 1},Q${firstDataRow + 1},R${firstDataRow + 1}),A${firstDataRow + 1}-AH${firstDataRow}>$E$8)`]];
sheet.getRange(`S${firstDataRow + 1}:S${lastDataRow}`).fillDown();
sheet.getRange(`T${firstDataRow}`).values = [["初始配置"]];
sheet.getRange(`T${firstDataRow + 1}`).formulas = [[
  `=IF(NOT(OR(P${firstDataRow + 1},Q${firstDataRow + 1},R${firstDataRow + 1})),"不调",IF(NOT(S${firstDataRow + 1}),"间隔规则跳过",IF(P${firstDataRow + 1},"年末+季度",IF(AND(Q${firstDataRow + 1},R${firstDataRow + 1}),"季度+动态",IF(Q${firstDataRow + 1},"季度","动态")))))`,
]];
sheet.getRange(`T${firstDataRow + 1}:T${lastDataRow}`).fillDown();

sheet.getRange(`U${firstDataRow}:U${firstDataRow}`).formulas = [[
  `=IF(OR(T${firstDataRow}="年末+季度",T${firstDataRow}="季度+动态"),N${firstDataRow}*$E$5/2,IF(T${firstDataRow}="季度",(J${firstDataRow}+K${firstDataRow})/2,IF(T${firstDataRow}="动态",N${firstDataRow}*$E$5*IF(J${firstDataRow}+K${firstDataRow}=0,0.5,J${firstDataRow}/(J${firstDataRow}+K${firstDataRow})),J${firstDataRow})))`,
]];
sheet.getRange(`U${firstDataRow}:U${lastDataRow}`).fillDown();
sheet.getRange(`V${firstDataRow}:V${firstDataRow}`).formulas = [[
  `=IF(OR(T${firstDataRow}="年末+季度",T${firstDataRow}="季度+动态"),N${firstDataRow}*$E$5/2,IF(T${firstDataRow}="季度",(J${firstDataRow}+K${firstDataRow})/2,IF(T${firstDataRow}="动态",N${firstDataRow}*$E$5*IF(J${firstDataRow}+K${firstDataRow}=0,0.5,K${firstDataRow}/(J${firstDataRow}+K${firstDataRow})),K${firstDataRow})))`,
]];
sheet.getRange(`V${firstDataRow}:V${lastDataRow}`).fillDown();
sheet.getRange(`W${firstDataRow}:W${firstDataRow}`).formulas = [[
  `=IF(OR(T${firstDataRow}="年末+季度",T${firstDataRow}="季度+动态",T${firstDataRow}="动态"),N${firstDataRow}*(1-$E$5)*IF(L${firstDataRow}+M${firstDataRow}=0,$B$7/($B$7+$B$8),L${firstDataRow}/(L${firstDataRow}+M${firstDataRow})),L${firstDataRow})`,
]];
sheet.getRange(`W${firstDataRow}:W${lastDataRow}`).fillDown();
sheet.getRange(`X${firstDataRow}:X${firstDataRow}`).formulas = [[
  `=IF(OR(T${firstDataRow}="年末+季度",T${firstDataRow}="季度+动态",T${firstDataRow}="动态"),N${firstDataRow}*(1-$E$5)*IF(L${firstDataRow}+M${firstDataRow}=0,$B$8/($B$7+$B$8),M${firstDataRow}/(L${firstDataRow}+M${firstDataRow})),M${firstDataRow})`,
]];
sheet.getRange(`X${firstDataRow}:X${lastDataRow}`).fillDown();

sheet.getRange(`Y${firstDataRow}`).values = [[1]];
sheet.getRange(`Y${firstDataRow + 1}`).formulas = [[`=POWER(1-$H$5,(A${firstDataRow + 1}-A${firstDataRow})/$H$8)`]];
sheet.getRange(`Y${firstDataRow + 1}:Y${lastDataRow}`).fillDown();
sheet.getRange(`Z${firstDataRow}:AC${firstDataRow}`).formulas = [[
  `=U${firstDataRow}*Y${firstDataRow}`,
  `=V${firstDataRow}*Y${firstDataRow}`,
  `=W${firstDataRow}*Y${firstDataRow}`,
  `=X${firstDataRow}*Y${firstDataRow}`,
]];
sheet.getRange(`Z${firstDataRow}:AC${lastDataRow}`).fillDown();
sheet.getRange(`AD${firstDataRow}`).formulas = [[`=SUM(Z${firstDataRow}:AC${firstDataRow})`]];
sheet.getRange(`AD${firstDataRow}:AD${lastDataRow}`).fillDown();
sheet.getRange(`AE${firstDataRow}`).formulas = [[`=AD${firstDataRow}`]];
sheet.getRange(`AE${firstDataRow + 1}`).formulas = [[`=MAX(AE${firstDataRow},AD${firstDataRow + 1})`]];
sheet.getRange(`AE${firstDataRow + 1}:AE${lastDataRow}`).fillDown();
sheet.getRange(`AF${firstDataRow}`).formulas = [[`=AD${firstDataRow}/AE${firstDataRow}-1`]];
sheet.getRange(`AF${firstDataRow}:AF${lastDataRow}`).fillDown();
sheet.getRange(`AG${firstDataRow}`).values = [[null]];
sheet.getRange(`AG${firstDataRow + 1}`).formulas = [[`=AD${firstDataRow + 1}/AD${firstDataRow}-1`]];
sheet.getRange(`AG${firstDataRow + 1}:AG${lastDataRow}`).fillDown();
sheet.getRange(`AH${firstDataRow}`).formulas = [[`=A${firstDataRow}`]];
sheet.getRange(`AH${firstDataRow + 1}`).formulas = [[
  `=IF(OR(T${firstDataRow + 1}="年末+季度",T${firstDataRow + 1}="季度+动态",T${firstDataRow + 1}="季度",T${firstDataRow + 1}="动态"),A${firstDataRow + 1},AH${firstDataRow})`,
]];
sheet.getRange(`AH${firstDataRow + 1}:AH${lastDataRow}`).fillDown();
sheet.getRange(`AI${firstDataRow}:AJ${firstDataRow}`).formulas = [[`=YEAR(A${firstDataRow})`, `=MONTH(A${firstDataRow})`]];
sheet.getRange(`AI${firstDataRow}:AJ${lastDataRow}`).fillDown();
sheet.getRange(`AK${firstDataRow}`).formulas = [[`=IF(MONTH(A${firstDataRow})<>MONTH(A${firstDataRow + 1}),1,0)`]];
sheet.getRange(`AK${firstDataRow}:AK${lastDataRow}`).fillDown();
sheet.getRange(`AK${lastDataRow}`).values = [[1]];
sheet.getRange(`AL${firstDataRow}`).formulas = [[`=AD${firstDataRow}`]];
sheet.getRange(`AL${firstDataRow + 1}`).formulas = [[`=IF(AK${firstDataRow},AD${firstDataRow},AL${firstDataRow})`]];
sheet.getRange(`AL${firstDataRow + 1}:AL${lastDataRow}`).fillDown();
sheet.getRange(`AM${firstDataRow}`).formulas = [[`=IF(AK${firstDataRow},AD${firstDataRow}/AL${firstDataRow}-1,"")`]];
sheet.getRange(`AM${firstDataRow}:AM${lastDataRow}`).fillDown();
sheet.getRange(`AN${firstDataRow}`).formulas = [[`=AD${firstDataRow}`]];
sheet.getRange(`AN${firstDataRow + 1}`).formulas = [[`=IF(AI${firstDataRow + 1}<>AI${firstDataRow},AD${firstDataRow + 1},MAX(AN${firstDataRow},AD${firstDataRow + 1}))`]];
sheet.getRange(`AN${firstDataRow + 1}:AN${lastDataRow}`).fillDown();
sheet.getRange(`AO${firstDataRow}`).formulas = [[`=AD${firstDataRow}/AN${firstDataRow}-1`]];
sheet.getRange(`AO${firstDataRow}:AO${lastDataRow}`).fillDown();
sheet.getRange(`AP${firstDataRow}`).formulas = [[`=IFERROR(SUM(Z${firstDataRow}:AC${firstDataRow})/AD${firstDataRow},0)`]];
sheet.getRange(`AP${firstDataRow}:AP${lastDataRow}`).fillDown();
sheet.getRange(`AQ${firstDataRow}`).formulas = [[`=AND(B${firstDataRow}>0,C${firstDataRow}>0,D${firstDataRow}>0,E${firstDataRow}>0)`]];
sheet.getRange(`AQ${firstDataRow}:AQ${lastDataRow}`).fillDown();

sheet.getRange(`A${firstDataRow}:AQ${lastDataRow}`).format = {
  font: { fontSize: 9, typeface: "宋体" },
  verticalAlignment: "center",
};
sheet.getRange(`A${firstDataRow}:A${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";
sheet.getRange(`B${firstDataRow}:E${lastDataRow}`).format.numberFormat = "0.0000";
sheet.getRange(`B${firstDataRow}:E${lastDataRow}`).format.font = { color: green, fontSize: 9, typeface: "宋体" };
sheet.getRange(`F${firstDataRow}:I${lastDataRow}`).format.numberFormat = "0.000%";
sheet.getRange(`J${firstDataRow}:N${lastDataRow}`).format.numberFormat = "0.000000";
sheet.getRange(`O${firstDataRow}:O${lastDataRow}`).format.numberFormat = "0.00%";
sheet.getRange(`U${firstDataRow}:AE${lastDataRow}`).format.numberFormat = "0.000000";
sheet.getRange(`AF${firstDataRow}:AG${lastDataRow}`).format.numberFormat = "0.000%";
sheet.getRange(`AH${firstDataRow}:AH${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";
sheet.getRange(`AI${firstDataRow}:AJ${lastDataRow}`).format.numberFormat = "0";
sheet.getRange(`AL${firstDataRow}:AL${lastDataRow}`).format.numberFormat = "0.000000";
sheet.getRange(`AM${firstDataRow}:AM${lastDataRow}`).format.numberFormat = "0.00%";
sheet.getRange(`AN${firstDataRow}:AN${lastDataRow}`).format.numberFormat = "0.000000";
sheet.getRange(`AO${firstDataRow}:AO${lastDataRow}`).format.numberFormat = "0.00%";
sheet.getRange(`AP${firstDataRow}:AP${lastDataRow}`).format.numberFormat = "0.0000";
sheet.getRange(`A${firstDataRow}:AQ${lastDataRow}`).conditionalFormats.add("expression", {
  formula: `=MOD(ROW(),2)=0`,
  format: { fill: "#F8FAFC" },
});
sheet.getRange(`T${firstDataRow}:T${lastDataRow}`).conditionalFormats.add("containsText", { text: "动态", format: { fill: paleYellow, font: { color: red, bold: true } } });
sheet.getRange(`T${firstDataRow}:T${lastDataRow}`).conditionalFormats.add("containsText", { text: "季度", format: { fill: paleBlue, font: { color: darkBlue, bold: true } } });
sheet.getRange(`T${firstDataRow}:T${lastDataRow}`).conditionalFormats.add("containsText", { text: "跳过", format: { fill: "#F2F2F2", font: { color: gray } } });

sheet.getRange(`AR45:AT45`).values = [["月份日期", "月份标签", "月末费后净值"]];
sheet.getRange(`AR${firstDataRow}`).formulas = [[`=DATE(YEAR($A$${firstDataRow}),MONTH($A$${firstDataRow}),1)`]];
sheet.getRange(`AR${firstDataRow + 1}`).formulas = [[`=EDATE(AR${firstDataRow},1)`]];
sheet.getRange(`AR${firstDataRow + 1}:AR${monthHelperLastRow}`).fillDown();
sheet.getRange(`AS${firstDataRow}`).formulas = [[`=TEXT(AR${firstDataRow},"yyyy-mm")`]];
sheet.getRange(`AS${firstDataRow}:AS${monthHelperLastRow}`).fillDown();
sheet.getRange(`AT${firstDataRow}`).formulas = [[
  `=IF(AR${firstDataRow}>DATE(YEAR($A$${lastDataRow}),MONTH($A$${lastDataRow}),1),"",SUMIFS($AD$${firstDataRow}:$AD$${lastDataRow},$AI$${firstDataRow}:$AI$${lastDataRow},YEAR(AR${firstDataRow}),$AJ$${firstDataRow}:$AJ$${lastDataRow},MONTH(AR${firstDataRow}),$AK$${firstDataRow}:$AK$${lastDataRow},1))`,
]];
sheet.getRange(`AT${firstDataRow}:AT${monthHelperLastRow}`).fillDown();
sheet.getRange(`AR${firstDataRow}:AR${monthHelperLastRow}`).format.numberFormat = "yyyy-mm";
sheet.getRange(`AT${firstDataRow}:AT${monthHelperLastRow}`).format.numberFormat = "0.0000";

const chart = sheet.charts.add("line", sheet.getRange(`AS45:AT${monthHelperLastRow}`));
chart.title = "2080组合费后净值走势";
chart.titleTextStyle.fontSize = 13;
chart.hasLegend = false;
chart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
chart.yAxis = { numberFormatCode: "0.00", textStyle: { fontSize: 9 } };
chart.setPosition("A12", "O29");
if (chart.series.items.length > 0) {
  chart.series.items[0].fill = blue;
}

sheet.getRange("A1:AT40").format.font.typeface = "宋体";
sheet.getRange("A1:AQ40").format.rowHeight = 20;
sheet.getRange("A31:P31").format.rowHeight = 24;
sheet.getRange("A32:P32").format.rowHeight = 30;
sheet.getRange("A33:P40").format.rowHeight = 22;
sheet.getRange("A1:AQ44").format.wrapText = true;

const widthMap = [
  ["A1:AQ1", 13],
  ["B1:M1660", 9],
  ["N1:P1660", 13],
  ["Q1:Q1660", 20],
  ["R1:R1660", 14],
  ["S1:S1660", 36],
  ["T1:T1660", 15],
  ["U1:AC1660", 13],
  ["AD1:AO1660", 13],
  ["AP1:AQ1660", 11],
  ["AR1:AT1660", 12],
];
for (const [range, width] of widthMap) {
  sheet.getRange(range).format.columnWidth = width;
}
sheet.getRange("A1:AQ1").format.columnWidth = 13;
sheet.getRange("A1:A1660").format.columnWidth = 13;
sheet.getRange("Q1:Q1660").format.columnWidth = 20;
sheet.getRange("S1:S1660").format.columnWidth = 34;

workbook.comments.setSelf({ displayName: "User" });
workbook.comments.addThread({ cell: sheet.getRange("E5") }, "动态阈值触发时，权益合计调整到该目标，默认20%。单个权益策略不强制回到10%，季末再单独校准为1:1。");
workbook.comments.addThread({ cell: sheet.getRange("H5") }, "年化费率按相邻净值日的实际日历天数折算：POWER(1-年费率, 间隔天数/计费日基准)。");
workbook.comments.addThread({ cell: sheet.getRange("H6") }, "用于算术年化收益率、年化波动率和Sharpe Ratio，默认250个交易日。");
workbook.comments.addThread({ cell: source.getRange("P2") }, "输出文件已将原iFinD公式的已缓存数值固化，以保证无插件时回测仍可重算。原始底稿未被修改。");
workbook.comments.addThread({ cell: source.getRange("Q2") }, "输出文件已将原iFinD公式的已缓存数值固化，以保证无插件时回测仍可重算。原始底稿未被修改。");

const dashboard = await workbook.render({ sheetName, range: "A1:U40", scale: 1.35, format: "png" });
await fs.writeFile(`${previewDir}/dashboard.png`, new Uint8Array(await dashboard.arrayBuffer()));
const calcPreview = await workbook.render({ sheetName, range: "A43:AQ60", scale: 1.0, format: "png" });
await fs.writeFile(`${previewDir}/calculation.png`, new Uint8Array(await calcPreview.arrayBuffer()));
const sourcePreview = await workbook.render({ sheetName: "净值底稿", range: "A1:Q15", scale: 1.2, format: "png" });
await fs.writeFile(`${previewDir}/source.png`, new Uint8Array(await sourcePreview.arrayBuffer()));

const keyCheck = await workbook.inspect({
  kind: "table",
  range: `${sheetName}!Q12:S28`,
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 5,
  maxChars: 12000,
});
console.log("KEY_CHECK");
console.log(keyCheck.ndjson);

const annualCheck = await workbook.inspect({
  kind: "table",
  range: `${sheetName}!A31:P40`,
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 18,
  maxChars: 20000,
});
console.log("ANNUAL_CHECK");
console.log(annualCheck.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(formulaErrors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`OUTPUT\t${outputPath}`);
console.log(`DATA_ROWS\t${snapshot.length}`);
console.log(`SOURCE_LAST_ROW\t${sourceLastRow}`);
console.log(`MODEL_LAST_ROW\t${lastDataRow}`);
