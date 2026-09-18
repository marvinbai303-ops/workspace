import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = path.resolve("君君美债利率模型_20260917");
await fs.mkdir(outputDir, { recursive: true });

const wb = Workbook.create();
const dash = wb.worksheets.add("模型总览");
const engine = wb.worksheets.add("因子引擎");
const risk = wb.worksheets.add("风险资产");
const scen = wb.worksheets.add("场景与阈值");
const dict = wb.worksheets.add("数据字典");
const method = wb.worksheets.add("方法与信源");
const audit = wb.worksheets.add("审计");

const FONT = "Arial";
const NAVY = "#16324F";
const BLUE = "#2F75B5";
const TEAL = "#1B7F79";
const RED = "#C0504D";
const ORANGE = "#ED7D31";
const GREEN = "#70AD47";
const LIGHT_BLUE = "#D9EAF7";
const LIGHT_TEAL = "#DDEFEA";
const LIGHT_ORANGE = "#FCE4D6";
const LIGHT_RED = "#F4CCCC";
const LIGHT_GREEN = "#E2F0D9";
const LIGHT_GRAY = "#F2F4F7";
const MID_GRAY = "#D9E1F2";
const DARK = "#1F2937";
const WHITE = "#FFFFFF";
const INPUT_BLUE = "#DDEBF7";

function baseSheet(sheet, widthRange = "A:O") {
  sheet.showGridLines = false;
  sheet.getRange(widthRange).format.font = { name: FONT, size: 10, color: DARK };
}

function title(sheet, range, text, subtitleRange, subtitle) {
  sheet.mergeCells(range);
  sheet.getRange(range).values = [[text]];
  sheet.getRange(range).format = {
    fill: NAVY,
    font: { name: FONT, size: 20, bold: true, color: WHITE },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
  sheet.getRange(range).format.rowHeight = 31;
  sheet.mergeCells(subtitleRange);
  sheet.getRange(subtitleRange).values = [[subtitle]];
  sheet.getRange(subtitleRange).format = {
    fill: LIGHT_BLUE,
    font: { name: FONT, size: 10, color: NAVY, italic: true },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
}

function section(sheet, range, text, fill = NAVY) {
  sheet.mergeCells(range);
  sheet.getRange(range).values = [[text]];
  sheet.getRange(range).format = {
    fill,
    font: { name: FONT, size: 11, bold: true, color: WHITE },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
}

function header(sheet, range) {
  sheet.getRange(range).format = {
    fill: NAVY,
    font: { name: FONT, size: 10, bold: true, color: WHITE },
    verticalAlignment: "center",
    horizontalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#B4C6E7" },
  };
}

function bordered(sheet, range) {
  sheet.getRange(range).format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
}

function scoreLabelFormula(cellRef) {
  return `=IF(${cellRef}>=65,"高压",IF(${cellRef}>=55,"偏紧",IF(${cellRef}>=45,"中性",IF(${cellRef}>=35,"偏松","宽松"))))`;
}

function environmentLabelFormula(cellRef) {
  return `=IF(${cellRef}>=65,"明显有利",IF(${cellRef}>=55,"偏有利",IF(${cellRef}>=45,"中性",IF(${cellRef}>=35,"偏不利","明显不利"))))`;
}

// ---------------- 因子引擎 ----------------
baseSheet(engine, "A:O");
title(engine, "A1:O2", "君君美债利率模型｜因子引擎", "A3:O3", "名义利率 = 预期政策路径 + 通胀补偿 + 期限溢价；风险资产压力再经过市场传导门控。蓝色单元格为可更新输入。 数据截至 2026-09-16。 ");
engine.freezePanes.freezeRows(4);
engine.getRange("A4:O4").values = [["模块", "指标", "正向=收紧", "权重", "当前值", "单位", "5年均值/中枢", "5年标准差/尺度", "标准化Z", "压力分", "数据日期", "可得性(1-5)", "准确性(1-5)", "口径与局限", "主要来源"]];
header(engine, "A4:O4");

const rows = [
  [5,"政策路径","2Y-有效联邦基金利率利差",1,0.45,1.04,"百分点",0.0017077,0.8294249,"2026-09-15",5,4,"可交易的政策路径代理；仍混有2Y期限溢价","FRED: DGS2-DFF"],
  [6,"政策路径","2Y美债20日变动",1,0.40,0.47,"百分点",0.0464860,0.2391424,"2026-09-15",5,4,"捕捉政策路径重定价；事件窗口内最有用","FRED: DGS2"],
  [7,"政策路径","有效联邦基金利率20日变动",1,0.15,0.00,"百分点",0.0388725,0.1951424,"2026-09-15",5,5,"实际政策动作，离散且滞后于市场定价","FRED: DFF"],
  [10,"市场通胀","5Y盈亏平衡通胀水平",1,0.35,2.35,"%",2.4457966,0.2887521,"2026-09-16",5,3,"含通胀风险与TIPS流动性溢价，不是纯预期","FRED: T5YIE"],
  [11,"市场通胀","5Y盈亏平衡通胀20日变动",1,0.35,0.04,"百分点",-0.0015380,0.1527151,"2026-09-16",5,3,"适合看边际再定价，不宜单独解释水平","FRED: T5YIE"],
  [12,"市场通胀","5Y5Y远期通胀补偿",1,0.30,2.31,"%",2.2678783,0.0987903,"2026-09-16",5,3,"长期锚；同样含风险与流动性成分","FRED: T5YIFR"],
  [15,"劳动力粘性","平均时薪同比",1,0.25,3.0857455,"%",4.3677958,0.6830206,"2026-08-01",5,3,"月频、构成效应明显；CES会月度及年度修订","BLS/FRED: CES0500000003"],
  [16,"劳动力粘性","Atlanta Fed工资增长追踪器",1,0.25,4.10,"%",3.50,0.75,"2026-08-01",5,4,"匹配同一劳动者的工资增速，3个月移动平均；中枢/尺度为模型假设","Atlanta Fed WGT"],
  [17,"劳动力粘性","失业率（反向）",-1,0.15,4.10,"%",3.98,0.3550125,"2026-08-01",5,4,"家庭调查月频；样本波动大，单月变化需谨慎","BLS/FRED: UNRATE"],
  [18,"劳动力粘性","JOLTS职位空缺数",1,0.20,7271,"千人",8847.2623,1750.1508,"2026-07-01",5,3,"并非高频；约1个月滞后、月度与年度修订较大","BLS/FRED: JTSJOL"],
  [19,"劳动力粘性","初请失业金4周均值（反向）",-1,0.15,206000,"人",223663.7931,22445.2484,"2026-09-05",5,4,"周频且及时；受季调、假期与州级申报扰动","DOL/FRED: ICSA"],
  [22,"原材料传导","PPI大宗商品3个月变动",1,0.35,-0.7829083,"%",1.1590888,3.0031765,"2026-08-01",5,4,"广谱上游价格月频代理；不等于最终消费价格","BLS/FRED: PPIACO"],
  [23,"原材料传导","WTI现货60日变动",1,0.65,43.4199946,"%",2.3565562,19.3365269,"2026-09-15",5,5,"高频且准确反映能源；不能代表核心服务通胀","EIA/FRED: DCOILWTICO"],
  [28,"期限溢价","ACM 10Y期限溢价水平",1,0.70,0.7089843,"%",-0.0354072,0.5621820,"2026-09-15",5,3,"模型估计值；日度估计、周度更新，存在模型风险","NY Fed ACMTP10"],
  [29,"期限溢价","ACM 10Y期限溢价20日变动",1,0.30,-0.0475904,"百分点",0.0132716,0.1838833,"2026-09-15",5,3,"判断长端上行是否来自期限溢价边际扩张","NY Fed ACMTP10"],
  [32,"市场传导","10Y实际利率20日变动",1,0.25,0.28,"百分点",0.0386590,0.1966126,"2026-09-15",5,4,"长久期估值的直接折现率通道","FRED: DFII10"],
  [33,"市场传导","美高收益债OAS 20日变动",1,0.20,0.13,"百分点",-0.0257860,0.2641338,"2026-09-15",5,5,"信用风险与融资条件核心确认指标","FRED: BAMLH0A0HYM2"],
  [34,"市场传导","美投资级债OAS 20日变动",1,0.10,0.01,"百分点",-0.0080372,0.0636386,"2026-09-15",5,5,"比高收益更稳健，但对早期风险反应较弱","FRED: BAMLC0A0CM"],
  [35,"市场传导","VIX水平",1,0.15,17.20,"指数",19.1296970,5.2749403,"2026-09-15",5,5,"股票隐含波动；事件冲击快、均值回归也快","CBOE/FRED: VIXCLS"],
  [36,"市场传导","美元广义指数20日变动",1,0.15,-0.1231008,"%",0.0573589,1.1875496,"2026-09-11",5,4,"全球美元流动性与风险偏好代理","Fed/FRED: DTWEXBGS"],
  [37,"市场传导","芝加哥联储NFCI水平",1,0.15,-0.56,"指数",-0.3977854,0.1335983,"2026-09-11",5,4,"周频综合金融条件；负值代表较历史均值宽松","Chicago Fed/FRED: NFCI"],
];

for (const [r,mod,metric,dir,w,current,unit,mean,std,date,avail,acc,note,source] of rows) {
  engine.getRange(`A${r}:H${r}`).values = [[mod,metric,dir,w,current,unit,mean,std]];
  engine.getRange(`I${r}`).formulas = [[`=IFERROR(C${r}*(E${r}-G${r})/H${r},"")`]];
  engine.getRange(`J${r}`).formulas = [[`=IF(I${r}="","",MAX(0,MIN(100,50+20*I${r})))`]];
  engine.getRange(`K${r}:O${r}`).values = [[date,avail,acc,note,source]];
}

const subScores = [
  [8,"政策性利率得分","=SUMPRODUCT(D5:D7,J5:J7)/SUM(D5:D7)"],
  [13,"市场通胀预期子分","=SUMPRODUCT(D10:D12,J10:J12)/SUM(D10:D12)"],
  [20,"劳动力粘性子分","=SUMPRODUCT(D15:D19,J15:J19)/SUM(D15:D19)"],
  [24,"原材料传导子分","=SUMPRODUCT(D22:D23,J22:J23)/SUM(D22:D23)"],
  [26,"通胀预期与粘性综合","=45%*J13+35%*J20+20%*J24"],
  [30,"期限溢价得分","=SUMPRODUCT(D28:D29,J28:J29)/SUM(D28:D29)"],
  [38,"市场传导得分","=SUMPRODUCT(D32:D37,J32:J37)/SUM(D32:D37)"],
];
for (const [r,label,formula] of subScores) {
  engine.mergeCells(`A${r}:I${r}`);
  engine.getRange(`A${r}:I${r}`).values = [[label]];
  engine.getRange(`J${r}`).formulas = [[formula]];
  engine.mergeCells(`K${r}:O${r}`);
  engine.getRange(`K${r}:O${r}`).formulas = [[scoreLabelFormula(`J${r}`)]];
  engine.getRange(`A${r}:O${r}`).format = {
    fill: LIGHT_TEAL,
    font: { name: FONT, bold: true, color: NAVY },
    borders: { preset: "all", style: "thin", color: "#A8C8C2" },
  };
  engine.getRange(`J${r}`).format.numberFormat = "0.0";
  engine.getRange(`K${r}:O${r}`).format.horizontalAlignment = "center";
}

section(engine, "A40:O40", "综合输出与传导门控", TEAL);
engine.getRange("A41:F52").values = [
  ["输出","值","定义","解释","辅助",""],
  ["政策路径得分",null,"0-100，越高越收紧","市场对未来政策路径的定价",null,""],
  ["通胀预期得分",null,"市场预期45%+工资劳动力35%+原材料20%","避免只看油价或只看BEI",null,""],
  ["期限溢价得分",null,"ACM水平70%+20日变化30%","识别财政供给/久期风险",null,""],
  ["市场传导得分",null,"实际利率+信用+波动率+美元+NFCI","确认政策是否真正压到风险资产",null,""],
  ["基础利率压力",null,"政策35%+通胀35%+期限溢价30%","不含传导门控",null,""],
  ["有效风险资产利率压力",null,"基础压力×(0.75+0.5×传导/100)","核心总分：0-100",null,""],
  ["市场确认分",null,"通胀40%+期限30%+传导30%","政策之外的市场性利率确认",null,""],
  ["政策冲击占比",null,"|政策-50|÷(|政策-50|+|市场-50|)","对应视频中的政策:市场权重",null,""],
  ["市场冲击占比",null,"1-政策冲击占比","与上一项合计100%",null,""],
  ["政策/市场方向",null,"政策分与市场确认分同向或背离","背离意味着传导不完整",null,""],
  ["数据置信度",null,"可得性与准确性均值","仅衡量数据质量，不衡量预测正确率",null,""],
];
header(engine, "A41:F41");
engine.getRange("B42:B52").formulas = [
  ["=J8"],["=J26"],["=J30"],["=J38"],["=35%*B42+35%*B43+30%*B44"],
  ["=MIN(100,MAX(0,B46*(0.75+0.5*B45/100)))"],["=40%*B43+30%*B44+30%*B45"],
  ["=IFERROR(ABS(B42-50)/(ABS(B42-50)+ABS(B48-50)),50%)"],["=1-B49"],
  ["=IF(SIGN(B42-50)=SIGN(B48-50),\"同向\",\"背离\")"],
  ["=AVERAGE(L5:L7,L10:L12,L15:L19,L22:L23,L28:L29,L32:L37)*10+AVERAGE(M5:M7,M10:M12,M15:M19,M22:M23,M28:M29,M32:M37)*10"],
];
engine.getRange("A53:F53").values = [["当前制度识别",null,"规则优先于主观叙事","",null,""]];
engine.getRange("B53").formulas = [["=IF(AND(B42>=60,B44>=60,B43<60),\"政策重定价 + 期限溢价冲击\",IF(AND(B46>=65,B45>=60),\"全面收紧传导\",IF(AND(B43>=60,B44>=60),\"通胀与期限溢价共振\",IF(AND(B42>=60,B43<55,B45<55),\"政策独涨/预防性加息\",IF(AND(B46<=40,B45<=45),\"宽松传导\",\"混合状态\")))))"]];
engine.getRange("A53:F53").format = { fill: LIGHT_ORANGE, font: { name: FONT, bold: true, color: NAVY }, borders: { preset: "all", style: "thin", color: "#E6B8AF" } };
engine.getRange("B42:B48").format.numberFormat = "0.0";
engine.getRange("B49:B50").format.numberFormat = "0%";
engine.getRange("B52").format.numberFormat = "0.0";
engine.getRange("E5:E37").format.fill = INPUT_BLUE;
engine.getRange("G5:H37").format.fill = INPUT_BLUE;
engine.getRange("D5:D37").format.fill = INPUT_BLUE;
engine.getRange("E5:H37").format.numberFormat = "0.000";
engine.getRange("D5:D37").format.numberFormat = "0%";
engine.getRange("I5:J37").format.numberFormat = "0.0";
bordered(engine, "A4:O38");
bordered(engine, "A41:F53");
engine.getRange("A1:O53").format.wrapText = true;
engine.getRange("A:A").format.columnWidth = 15;
engine.getRange("B:B").format.columnWidth = 31;
engine.getRange("C:C").format.columnWidth = 12;
engine.getRange("D:D").format.columnWidth = 10;
engine.getRange("E:E").format.columnWidth = 13;
engine.getRange("F:F").format.columnWidth = 11;
engine.getRange("G:H").format.columnWidth = 16;
engine.getRange("I:J").format.columnWidth = 12;
engine.getRange("K:K").format.columnWidth = 13;
engine.getRange("L:M").format.columnWidth = 11;
engine.getRange("N:N").format.columnWidth = 46;
engine.getRange("O:O").format.columnWidth = 24;
engine.getRange("4:53").format.rowHeight = 25;

// ---------------- 风险资产 ----------------
baseSheet(risk, "A:J");
title(risk, "A1:J2", "风险资产映射", "A3:J3", "环境分>50表示当前利率结构相对有利；<50表示相对不利。敏感度为可编辑的结构性假设，不是回归系数，也不是交易建议。");
risk.getRange("A5:J5").values = [["资产", "政策敏感度", "通胀敏感度", "期限溢价敏感度", "传导敏感度", "环境分", "判断", "主要受力通道", "反转条件", "说明"]];
header(risk, "A5:J5");
const riskRows = [
  ["纳斯达克/长久期成长",-0.9,-0.8,-1.0,-0.8,"真实利率与久期折现","实际利率回落，且信用条件未恶化","估值久期最长"],
  ["标普500",-0.6,-0.5,-0.7,-0.7,"折现率+盈利预期","期限溢价和实际利率同步回落","盈利缓冲更强"],
  ["罗素2000",-0.8,-0.4,-0.5,-1.0,"融资成本+信用传导","HY OAS/NFCI转松","对银行与信用更敏感"],
  ["高收益信用",-0.7,-0.4,-0.5,-1.1,"信用利差与再融资","HY OAS不再扩张且政策路径回落","传导权重最高"],
  ["新兴市场股票",-0.6,-0.5,-0.6,-1.0,"美元+全球流动性","美元转弱且真实利率回落","需叠加本地基本面"],
  ["黄金",-0.6,0.8,-0.5,-0.5,"实际利率/美元 vs 通胀","通胀补偿上行快于实际利率","两条通道方向可能相反"],
  ["比特币",-0.8,0.2,-0.7,-1.1,"全球流动性+风险偏好","美元/NFCI转松且真实利率回落","高波动，不等同黄金"],
  ["原油/大宗商品",-0.2,1.0,-0.2,-0.3,"通胀与实物供需","需求未衰退且库存继续去化","需结合曲线与库存"],
  ["美国长债",-0.7,-0.9,-1.2,-0.5,"通胀+期限溢价+实际利率","ACM期限溢价和BEI同步下行","期限溢价权重最高"],
  ["美元指数",0.8,0.4,0.5,0.8,"政策差+避险需求","美外利差收窄且风险偏好修复","正敏感度表示利率紧缩利好美元"],
];
for (let i=0;i<riskRows.length;i++) {
  const r=6+i;
  const [asset,p,inf,tp,tr,channel,flip,note] = riskRows[i];
  risk.getRange(`A${r}:E${r}`).values = [[asset,p,inf,tp,tr]];
  risk.getRange(`F${r}`).formulas = [[`=MAX(0,MIN(100,50+((B${r}*('因子引擎'!$B$42-50))+(C${r}*('因子引擎'!$B$43-50))+(D${r}*('因子引擎'!$B$44-50))+(E${r}*('因子引擎'!$B$45-50)))/(ABS(B${r})+ABS(C${r})+ABS(D${r})+ABS(E${r}))))`]];
  risk.getRange(`G${r}`).formulas = [[environmentLabelFormula(`F${r}`)]];
  risk.getRange(`H${r}:J${r}`).values = [[channel,flip,note]];
}
risk.getRange("B6:E15").format.fill = INPUT_BLUE;
risk.getRange("B6:E15").format.numberFormat = "0.0";
risk.getRange("F6:F15").format.numberFormat = "0.0";
risk.getRange("A5:J15").format.wrapText = true;
bordered(risk, "A5:J15");
risk.getRange("A:A").format.columnWidth = 24;
risk.getRange("B:E").format.columnWidth = 15;
risk.getRange("F:G").format.columnWidth = 13;
risk.getRange("H:H").format.columnWidth = 24;
risk.getRange("I:I").format.columnWidth = 31;
risk.getRange("J:J").format.columnWidth = 26;
risk.getRange("5:15").format.rowHeight = 31;
risk.freezePanes.freezeRows(5);

// ---------------- 场景与阈值 ----------------
baseSheet(scen, "A:L");
title(scen, "A1:L2", "场景仿真与证伪阈值", "A3:L3", "先定制度，再看资产；场景分数均为0-100压力分。蓝色为假设，可自行覆盖。 ");
scen.getRange("A5:L5").values = [["场景", "政策", "通胀", "期限溢价", "市场传导", "有效利率压力", "纳斯达克", "标普500", "高收益信用", "黄金", "美元", "场景解释"]];
header(scen, "A5:L5");
const scenarios = [
  ["当前快照",null,null,null,null,"政策重定价与期限溢价偏紧，但信用/波动传导仅中等"],
  ["预防性加息/政策独涨",80,50,50,45,"政策路径上修，通胀与信用条件未确认"],
  ["通胀再锚定失败",75,75,70,70,"工资、商品、BEI、实际利率与信用同时收紧"],
  ["财政供给/期限溢价冲击",55,55,85,65,"长端受供给与久期风险驱动，短端不一定同步"],
  ["软着陆式降息",35,40,45,35,"政策回落，通胀温和，信用条件保持稳定"],
  ["衰退式降息",25,25,35,80,"政策宽松但信用利差和波动率快速恶化"],
];
for (let i=0;i<scenarios.length;i++) {
  const r=6+i;
  const [name,p,inf,tp,tr,explain] = scenarios[i];
  scen.getRange(`A${r}`).values = [[name]];
  if (i===0) {
    scen.getRange(`B${r}:E${r}`).formulas = [["='因子引擎'!$B$42","='因子引擎'!$B$43","='因子引擎'!$B$44","='因子引擎'!$B$45"]];
  } else {
    scen.getRange(`B${r}:E${r}`).values = [[p,inf,tp,tr]];
    scen.getRange(`B${r}:E${r}`).format.fill = INPUT_BLUE;
  }
  scen.getRange(`F${r}`).formulas = [[`=MIN(100,MAX(0,(35%*B${r}+35%*C${r}+30%*D${r})*(0.75+0.5*E${r}/100)))`]];
  const assetRows = [6,7,9,11,15];
  for (let j=0;j<assetRows.length;j++) {
    const rr=assetRows[j];
    const col=String.fromCharCode("G".charCodeAt(0)+j);
    scen.getRange(`${col}${r}`).formulas = [[`=MAX(0,MIN(100,50+((B${r}-50)*'风险资产'!$B$${rr}+(C${r}-50)*'风险资产'!$C$${rr}+(D${r}-50)*'风险资产'!$D$${rr}+(E${r}-50)*'风险资产'!$E$${rr})/(ABS('风险资产'!$B$${rr})+ABS('风险资产'!$C$${rr})+ABS('风险资产'!$D$${rr})+ABS('风险资产'!$E$${rr}))))`]];
  }
  scen.getRange(`L${r}`).values = [[explain]];
}
scen.getRange("B6:K11").format.numberFormat = "0.0";
bordered(scen, "A5:L11");
section(scen, "A14:L14", "制度判别阈值与证伪条件", TEAL);
scen.getRange("A15:F21").values = [
  ["判别","硬条件","含义","优先跟踪","证伪条件","观察窗"],
  ["政策独涨","政策≥60；通胀<55；传导<55","预防性或单点政策重定价","2Y/OIS、实际利率、信用利差","BEI/工资/信用同时转强","1-4周"],
  ["全面收紧传导","基础压力≥65；传导≥60","风险资产进入广谱压力","真实利率、HY OAS、VIX、美元、NFCI","信用利差与NFCI不确认","数日-4周"],
  ["通胀再锚定失败","通胀≥60；期限≥60","名义+真实折现率双升","5Y BEI、WGT、油价/PPI、ACM TP","工资/BEI回落或油价冲击逆转","1-3月"],
  ["期限溢价冲击","期限≥65；政策<60","财政供给/久期风险主导长端","ACM TP、拍卖尾差、期限曲线","TP回落且长端收益率不再上行","1-8周"],
  ["软着陆宽松","政策≤40；通胀≤45；传导≤45","折现率下行且信用稳定","2Y、实际利率、HY OAS、NFCI","信用快速恶化","1-3月"],
  ["衰退式宽松","政策≤35；传导≥65","降息不能抵消盈利/信用风险","初请、失业率、HY OAS、VIX","信用与就业企稳","数周-2季"],
];
header(scen, "A15:F15");
bordered(scen, "A15:F21");
scen.getRange("A5:L21").format.wrapText = true;
scen.getRange("A:A").format.columnWidth = 25;
scen.getRange("B:K").format.columnWidth = 13;
scen.getRange("L:L").format.columnWidth = 40;
scen.getRange("A15:A21").format.columnWidth = 22;
scen.getRange("B15:B21").format.columnWidth = 30;
scen.getRange("C:F").format.columnWidth = 26;
scen.getRange("5:21").format.rowHeight = 33;

// ---------------- 数据字典 ----------------
baseSheet(dict, "A:J");
title(dict, "A1:J2", "高频指标可得性与准确性", "A3:J3", "“可得性”衡量免费、更新频率与获取难度；“准确性”衡量对目标概念的贴合度与修订/模型风险。两者必须分开。");
dict.getRange("A5:J5").values = [["维度","指标","频率","典型滞后","修订风险","可得性","准确性","是否入模","主要局限","官方来源"]];
header(dict, "A5:J5");
const dictionary = [
 ["政策","有效联邦基金利率 EFFR","日","1日","低",5,5,"是","准确描述当前政策落点，不代表未来路径","https://www.newyorkfed.org/markets/reference-rates/effr"],
 ["政策","SOFR","日","1日","低",5,5,"辅助","交易基础强，但仍是隔夜融资现状","https://www.newyorkfed.org/markets/reference-rates/sofr"],
 ["政策","Fed funds futures / OIS","日内","实时","低",3,4,"首选但需终端","含风险溢价、合约技术因素；免费历史不完整","https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"],
 ["政策","2Y美债","日内","实时","低",5,4,"是","政策路径代理，仍含期限溢价","https://fred.stlouisfed.org/series/DGS2"],
 ["通胀","5Y/10Y盈亏平衡通胀","日","1日","低",5,3,"是","含通胀风险溢价与TIPS流动性溢价","https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm"],
 ["通胀","5Y5Y远期通胀补偿","日","1日","低",5,3,"是","长期锚但对短期油价不敏感","https://fred.stlouisfed.org/series/T5YIFR"],
 ["通胀","Cleveland Fed Inflation Nowcast","工作日","当日","模型会重估",5,3,"辅助","headline受油价驱动，core在月内变化很少","https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"],
 ["期限","NY Fed ACM 10Y期限溢价","日度估计/周更","数日","模型修订",5,3,"是","模型依赖强，不能视为可观测价格","https://www.newyorkfed.org/research/data_indicators/term-premia-tabs"],
 ["期限","SF Fed期限溢价","日","1日","模型修订",5,3,"交叉核验","不同模型可能给出不同水平","https://www.frbsf.org/research-and-insights/data-and-indicators/treasury-yield-premiums/"],
 ["工资","平均时薪 AHE","月","约1周","中高",5,3,"是","构成效应、月度修订和年度基准修订","https://www.bls.gov/news.release/empsit.htm"],
 ["工资","Atlanta Fed Wage Growth Tracker","月","约2周","方法变更风险",5,4,"是","匹配样本、3个月均值；不等于中位工资增速","https://www.atlantafed.org/research-and-data/data/wage-growth-tracker"],
 ["工资","就业成本指数 ECI","季","约1月","低",5,5,"慢变量","口径最稳健，但频率太低","https://www.bls.gov/eci/"],
 ["就业","失业率","月","约1周","中",5,4,"是","家庭调查月度噪声；定义不含未主动求职者","https://www.bls.gov/news.release/empsit.htm"],
 ["就业","初请失业金","周","5日左右","中",5,4,"是","及时，但季调、假日与州申报扰动明显","https://www.dol.gov/ui/data.pdf"],
 ["就业","JOLTS职位空缺","月","约1月","高",5,3,"是","不是高频；5年数据可年度重修","https://www.bls.gov/jlt/"],
 ["就业","Indeed职位发布","日/周","较短","口径变更风险",4,3,"交叉核验","私人平台覆盖偏差、定义可能变化","https://data.indeed.com/"],
 ["原材料","WTI/Brent现货与期货","日内","实时","低",5,5,"是","准确反映能源价格，但不代表核心服务通胀","https://www.eia.gov/finance/"],
 ["原材料","EIA库存与成品油价格","周","数日","中",5,4,"跟踪","用于区分供给冲击、去库与需求变化","https://www.eia.gov/petroleum/supply/weekly/"],
 ["原材料","PPI大宗商品","月","约2周","中",5,4,"是","广谱但滞后；不能直接映射CPI权重","https://www.bls.gov/ppi/"],
 ["原材料","ISM Prices Paid","月","1-3工作日","低",4,3,"辅助","扩散指数，不是价格水平或涨幅","https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/"],
 ["传导","10Y实际利率","日","1日","低",5,4,"是","长久期资产折现率关键变量","https://fred.stlouisfed.org/series/DFII10"],
 ["传导","IG/HY OAS","日","1日","低",5,5,"是","信用传导确认；指数构成随时间变化","https://fred.stlouisfed.org/series/BAMLH0A0HYM2"],
 ["传导","VIX","日内","实时","低",5,5,"是","高频风险偏好，但均值回归很快","https://fred.stlouisfed.org/series/VIXCLS"],
 ["传导","NFCI","周","约1周","低",5,4,"是","综合性强但反应不如市场价格快","https://www.chicagofed.org/research/data/nfci/current-data"],
];
for (let i=0;i<dictionary.length;i++) dict.getRange(`A${6+i}:J${6+i}`).values = [dictionary[i]];
dict.getRange(`F6:G${5+dictionary.length}`).format.numberFormat = "0";
dict.getRange(`F6:G${5+dictionary.length}`).format.fill = LIGHT_BLUE;
dict.getRange(`A5:J${5+dictionary.length}`).format.wrapText = true;
bordered(dict, `A5:J${5+dictionary.length}`);
dict.getRange("A:A").format.columnWidth = 13;
dict.getRange("B:B").format.columnWidth = 30;
dict.getRange("C:E").format.columnWidth = 15;
dict.getRange("F:H").format.columnWidth = 13;
dict.getRange("I:I").format.columnWidth = 39;
dict.getRange("J:J").format.columnWidth = 48;
dict.getRange(`5:${5+dictionary.length}`).format.rowHeight = 32;
dict.freezePanes.freezeRows(5);

// ---------------- 方法与信源 ----------------
baseSheet(method, "A:H");
title(method, "A1:H2", "方法、视频要点与更新规则", "A3:H3", "自媒体内容只用于提出假设；模型打分只使用可复核的官方/市场数据。转写与概括可能存在语音识别误差。");
section(method, "A5:H5", "两条视频的可执行要点", TEAL);
method.getRange("A6:H11").values = [
 ["视频","核心命题","模型化处理","我做的校正","硬验证","不采用的简化","久期","结论用途"],
 ["视频1","风险资产受政策性利率与市场性利率共同影响；市场利率往往先于政策动作","政策路径分与市场确认分分开，并计算政策:市场冲击占比","政策并非只有加息/降息；资产负债表、前瞻指引也会改变预期短端","2Y/OIS、实际利率、信用利差、美元、VIX/NFCI","加息=立即利空全部风险资产","数日-3月","识别传导是否落地"],
 ["视频1","预防性、一次性加息与连续加息的资产含义不同","制度识别与场景仿真","用市场确认而非主观语气判断是否‘连续收紧’","BEI、ACM TP、信用条件是否共振","只看FOMC文字或点阵图","1-4周","区分政策独涨与全面收紧"],
 ["视频2","10Y名义利率应拆为政策路径、通胀预期/补偿、期限溢价","三大因子各自0-100打分","BEI不是纯通胀预期；期限溢价是模型估计而非可观察价格","TIPS/BEI、ACM TP、实际利率","把10Y变动全部归因于Fed","数周-数年","解释长端上行来源"],
 ["视频2","工资、失业、职位空缺、原材料价格决定通胀粘性与二次传导","市场通胀45%+劳动力35%+原材料20%","JOLTS并非高频；油价对headline强、对core弱","AHE/WGT/UNRATE/JOLTS/ICSA、PPI/WTI","用单一油价或单月就业数据定性","1-6月","判断通胀冲击能否扩散"],
 ["视频2","政策冲击只有传导到市场利率与信用条件，才构成广谱风险资产压力","有效压力=基础压力×传导门控","信用、波动率、美元、NFCI必须至少两条独立链确认","实际利率链 + 信用/风险偏好链","用股债同跌一天证明制度切换","数日-8周","风险资产总开关"],
];
header(method, "A6:H6");
bordered(method, "A6:H11");
section(method, "A14:H14", "模型恒等式、打分与信源闸门", NAVY);
method.getRange("A15:H23").values = [
 ["项目","规则","解释","事实/观点","数据要求","失效条件","更新频率","备注"],
 ["利率恒等式","名义收益率≈预期平均短端利率+通胀补偿+期限溢价","实务中三者不可完全无误差分离","理论框架","至少两套独立来源","模型残差持续扩大","周/月","用于分解，不做点预测"],
 ["标准化","压力分=50+20×Z，截断至0-100","50约等于5年中枢，1个标准差≈20分","模型规则","当前、5年均值、5年标准差","结构突变使5年样本失真","每月复核","权重与中枢可编辑"],
 ["通胀层","市场45%+劳动力35%+原材料20%","避免油价、工资或BEI单因子支配","模型观点","三条链至少两条确认","只有单一链抬升","日/周/月混合","headline与core分开理解"],
 ["传导门控","有效压力=基础压力×(0.75+0.5×传导/100)","政策信号未传导时自动降权","模型观点","实际利率+信用/波动/美元/NFCI","传导指标长期背离","日/周","门控范围0.75-1.25"],
 ["信源闸门","视频/研报只进假设，不直接进分数","已发生数据优先于远期叙事","研究纪律","官方统计、联储、交易价格","无法交叉核验","持续","价量不等于基本面"],
 ["双链验证","实际利率链与信用/风险偏好链至少两条同向","防止把局部利率波动误判为系统性风险","模型规则","DFII10 + HY OAS/VIX/NFCI/USD","只有一条链确认","事件后数日","对应君君‘传导’核心"],
 ["风险资产分","50+各因子偏离×结构敏感度","是环境映射，不是收益率预测","模型观点","敏感度透明可编辑","回归关系发生制度切换","季度复核","不输出买卖指令"],
 ["可证伪性","预先写明什么出现=模型错","不以更多叙事自证","研究纪律","阈值、观察窗、反转条件","证伪后不改口径硬解释","每次事件","场景页给出阈值"],
];
header(method, "A15:H15");
bordered(method, "A15:H23");
section(method, "A26:H26", "更新SOP", ORANGE);
method.getRange("A27:D32").values = [
 ["频率","更新项","动作","检查"],
 ["每日","2Y/10Y、TIPS/BEI、实际利率、OAS、VIX、美元、油价","覆盖因子引擎当前值；保留事件前快照","确认日期和单位"],
 ["每周","ACM期限溢价、NFCI、初请4周均值、EIA库存","更新当前值及5年统计","检查模型修订"],
 ["每月","AHE、失业率、JOLTS、WGT、PPI","先记录首次发布，再记录修订值","JOLTS和CES修订单列"],
 ["事件日","FOMC/CPI/NFP/拍卖","T-1、T+1、T+5冻结快照","区分政策冲击和市场确认"],
 ["季度","敏感度、权重、5年窗口","只在有证据时调整，不追涨杀跌","留痕并做回测"],
];
header(method, "A27:D27");
bordered(method, "A27:D32");
method.getRange("A5:H32").format.wrapText = true;
method.getRange("A:A").format.columnWidth = 18;
method.getRange("B:H").format.columnWidth = 27;
method.getRange("5:32").format.rowHeight = 47;
method.freezePanes.freezeRows(5);

// ---------------- 审计 ----------------
baseSheet(audit, "A:F");
title(audit, "A1:F2", "模型审计", "A3:F3", "审计只读取模型，不向业务计算回写。容差：权重合计±0.0001；分数必须在0-100。");
audit.getRange("A5:F5").values = [["检查项","实测值","目标/范围","差异","状态","定位"]];
header(audit, "A5:F5");
audit.getRange("A6:A14").values = [["政策权重"],["市场通胀权重"],["劳动力权重"],["原材料权重"],["期限溢价权重"],["市场传导权重"],["有效压力范围"],["风险资产分范围"],["关键输入完整性"]];
audit.getRange("B6:B14").formulas = [["=SUM('因子引擎'!D5:D7)"],["=SUM('因子引擎'!D10:D12)"],["=SUM('因子引擎'!D15:D19)"],["=SUM('因子引擎'!D22:D23)"],["=SUM('因子引擎'!D28:D29)"],["=SUM('因子引擎'!D32:D37)"],["='因子引擎'!B47"],["=MIN('风险资产'!F6:F15)"],["=COUNTBLANK('因子引擎'!E5:E7)+COUNTBLANK('因子引擎'!E10:E12)+COUNTBLANK('因子引擎'!E15:E19)+COUNTBLANK('因子引擎'!E22:E23)+COUNTBLANK('因子引擎'!E28:E29)+COUNTBLANK('因子引擎'!E32:E37)"]];
audit.getRange("C6:C14").values = [[1],[1],[1],[1],[1],[1],["0-100"],["0-100（并检查最大值）"],[0]];
audit.getRange("D6:D14").formulas = [["=B6-1"],["=B7-1"],["=B8-1"],["=B9-1"],["=B10-1"],["=B11-1"],["=IF(AND(B12>=0,B12<=100),0,1)"],["=IF(AND(B13>=0,MAX('风险资产'!F6:F15)<=100),0,1)"],["=B14"]];
audit.getRange("E6:E14").formulas = [["=IF(ABS(D6)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(ABS(D7)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(ABS(D8)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(ABS(D9)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(ABS(D10)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(ABS(D11)<=0.0001,\"PASS\",\"FAIL\")"],["=IF(D12=0,\"PASS\",\"FAIL\")"],["=IF(D13=0,\"PASS\",\"FAIL\")"],["=IF(D14=0,\"PASS\",\"FAIL\")"]];
audit.getRange("F6:F14").values = [["因子引擎 D5:D7"],["因子引擎 D10:D12"],["因子引擎 D15:D19"],["因子引擎 D22:D23"],["因子引擎 D28:D29"],["因子引擎 D32:D37"],["因子引擎 B47"],["风险资产 F6:F15"],["因子引擎 E列"]];
audit.getRange("B6:D14").format.numberFormat = "0.0000";
bordered(audit, "A5:F14");
audit.getRange("A:F").format.columnWidth = 23;
audit.getRange("C:C").format.columnWidth = 28;
audit.getRange("F:F").format.columnWidth = 30;

// ---------------- 模型总览 ----------------
baseSheet(dash, "A:O");
title(dash, "A1:O2", "君君美债利率模型｜风险资产监测总览", "A3:O3", "当前快照截至 2026-09-16；官方数据经 FRED、纽约联储、BLS、DOL、EIA、Atlanta Fed 交叉核验。高分=利率/金融条件压力更大。");

const cards = [
  ["A5:C5","A6:C7","A8:C8","政策路径","='因子引擎'!$B$42"],
  ["D5:F5","D6:F7","D8:F8","通胀预期","='因子引擎'!$B$43"],
  ["G5:I5","G6:I7","G8:I8","期限溢价","='因子引擎'!$B$44"],
  ["J5:L5","J6:L7","J8:L8","市场传导","='因子引擎'!$B$45"],
  ["M5:O5","M6:O7","M8:O8","有效利率压力","='因子引擎'!$B$47"],
];
for (const [tr,vr,lr,label,formula] of cards) {
  dash.mergeCells(tr); dash.mergeCells(vr); dash.mergeCells(lr);
  dash.getRange(tr).values = [[label]];
  dash.getRange(vr).formulas = [[formula]];
  const valueCell = vr.split(":")[0];
  dash.getRange(lr).formulas = [[scoreLabelFormula(valueCell)]];
  dash.getRange(tr).format = { fill: NAVY, font: { name: FONT, bold: true, color: WHITE, size: 11 }, horizontalAlignment: "center", verticalAlignment: "center" };
  dash.getRange(vr).format = { fill: LIGHT_BLUE, font: { name: FONT, bold: true, color: NAVY, size: 24 }, horizontalAlignment: "center", verticalAlignment: "center", numberFormat: "0.0" };
  dash.getRange(lr).format = { fill: LIGHT_TEAL, font: { name: FONT, bold: true, color: TEAL, size: 10 }, horizontalAlignment: "center", verticalAlignment: "center" };
  bordered(dash, tr); bordered(dash, vr); bordered(dash, lr);
}

section(dash, "A10:H10", "当前制度判断", TEAL);
dash.mergeCells("A11:H11");
dash.getRange("A11:H11").formulas = [["='因子引擎'!$B$53"]];
dash.getRange("A11:H11").format = { fill: LIGHT_ORANGE, font: { name: FONT, size: 16, bold: true, color: NAVY }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#E6B8AF" } };
dash.mergeCells("A12:H16");
dash.getRange("A12:H16").values = [["结论：当前不是‘所有市场性利率全面失控’，而是政策路径和期限溢价偏紧、实际利率上行，但信用利差、VIX与NFCI只给出中等确认。对长久期成长、长债和高杠杆资产不利；尚不足以单独定义为系统性风险出清。原油冲击很强，但工资、失业与JOLTS没有同步显示广谱再通胀。"]];
dash.getRange("A12:H16").format = { fill: "#FFF7E6", font: { name: FONT, size: 11, color: DARK }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: "#E6B8AF" } };
section(dash, "I10:O10", "政策性利率 → 市场性利率传导", NAVY);
dash.getRange("I11:O16").values = [
  ["指标","当前","判断","指标","当前","判断",""],
  ["政策冲击占比",null,"主导","市场冲击占比",null,"未完全确认",""],
  ["2Y 20日",0.47,"+47bp","10Y实际利率20日",0.28,"+28bp",""],
  ["ACM TP水平",0.7089843,"高于5年中枢","ACM TP 20日",-0.0475904,"边际回落",""],
  ["HY OAS 20日",0.13,"+13bp","VIX",17.2,"低于5年均值",""],
  ["NFCI",-0.56,"仍偏宽松","方向",null,"政策/市场",""]
];
dash.getRange("J12").formulas = [["='因子引擎'!$B$49"]];
dash.getRange("M12").formulas = [["='因子引擎'!$B$50"]];
dash.getRange("M16").formulas = [["='因子引擎'!$B$51"]];
dash.getRange("J12:M12").format.numberFormat = "0%";
dash.getRange("J13:J15").format.numberFormat = "0.00";
dash.getRange("M13:M15").format.numberFormat = "0.00";
header(dash, "I11:O11");
bordered(dash, "I11:O16");

section(dash, "A18:G18", "因子压力分", NAVY);
dash.getRange("A19:C24").values = [["因子","分数","信号"],["政策路径",null,null],["通胀预期",null,null],["期限溢价",null,null],["市场传导",null,null],["有效利率压力",null,null]];
dash.getRange("B20:B24").formulas = [["='因子引擎'!$B$42"],["='因子引擎'!$B$43"],["='因子引擎'!$B$44"],["='因子引擎'!$B$45"],["='因子引擎'!$B$47"]];
for (let r=20;r<=24;r++) dash.getRange(`C${r}`).formulas = [[scoreLabelFormula(`B${r}`)]];
header(dash, "A19:C19");
bordered(dash, "A19:C24");
dash.getRange("B20:B24").format.numberFormat = "0.0";

section(dash, "A27:G27", "风险资产环境分", TEAL);
dash.getRange("A28:C38").values = [["资产","环境分","判断"],...riskRows.map(r=>[r[0],null,null])];
for (let i=0;i<riskRows.length;i++) {
  const r=29+i;
  dash.getRange(`B${r}`).formulas = [[`='风险资产'!$F$${6+i}`]];
  dash.getRange(`C${r}`).formulas = [[`='风险资产'!$G$${6+i}`]];
}
header(dash, "A28:C28");
bordered(dash, "A28:C38");
dash.getRange("B29:B38").format.numberFormat = "0.0";

section(dash, "A41:O41", "使用纪律", ORANGE);
dash.mergeCells("A42:O44");
dash.getRange("A42:O44").values = [["1）先看制度：政策、通胀、期限溢价谁在驱动；2）再看传导：实际利率、信用、波动率、美元、NFCI是否至少两条独立链确认；3）最后才做资产映射。任何单一数据、单日K线或自媒体观点都不能独立触发结论。该模型是研究与监测工具，不是收益预测或买卖指令。"]];
dash.getRange("A42:O44").format = { fill: "#FFF7E6", font: { name: FONT, size: 11, color: DARK }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#E6B8AF" } };

// Charts on dashboard
const factorChart = dash.charts.add("bar", dash.getRange("A19:B24"));
factorChart.title = "利率压力因子（0-100）";
factorChart.titleTextStyle.typeface = FONT;
factorChart.titleTextStyle.fontSize = 12;
factorChart.hasLegend = false;
factorChart.xAxis = { numberFormatCode: "0", numberFormatSourceLinked: false, textStyle: { typeface: FONT, fontSize: 9 }, minimumScale: 0, maximumScale: 100 };
factorChart.yAxis = { textStyle: { typeface: FONT, fontSize: 9 } };
factorChart.setPosition("E19", "O25");
if (factorChart.series.items.length) factorChart.series.items[0].fill = BLUE;

const riskChart = dash.charts.add("bar", dash.getRange("A28:B38"));
riskChart.title = "风险资产环境分（>50有利）";
riskChart.titleTextStyle.typeface = FONT;
riskChart.titleTextStyle.fontSize = 12;
riskChart.hasLegend = false;
riskChart.xAxis = { numberFormatCode: "0", numberFormatSourceLinked: false, textStyle: { typeface: FONT, fontSize: 9 }, minimumScale: 0, maximumScale: 100 };
riskChart.yAxis = { textStyle: { typeface: FONT, fontSize: 9 } };
riskChart.setPosition("E28", "O40");
if (riskChart.series.items.length) riskChart.series.items[0].fill = TEAL;

dash.getRange("A:O").format.columnWidth = 12;
dash.getRange("A:A").format.columnWidth = 25;
dash.getRange("B:C").format.columnWidth = 14;
dash.getRange("I:I").format.columnWidth = 19;
dash.getRange("J:J").format.columnWidth = 12;
dash.getRange("K:K").format.columnWidth = 17;
dash.getRange("L:L").format.columnWidth = 20;
dash.getRange("M:M").format.columnWidth = 12;
dash.getRange("N:O").format.columnWidth = 16;
dash.getRange("1:44").format.rowHeight = 24;
dash.getRange("12:16").format.rowHeight = 28;
dash.getRange("42:44").format.rowHeight = 30;
dash.freezePanes.freezeRows(3);

// Tab colors and final formats
dash.tabColor = NAVY;
engine.tabColor = BLUE;
risk.tabColor = TEAL;
scen.tabColor = ORANGE;
dict.tabColor = "#8064A2";
method.tabColor = "#5B9BD5";
audit.tabColor = "#A5A5A5";

wb.recalculate();

// Render key sheets for visual QA.
for (const sheetName of ["模型总览", "因子引擎", "风险资产"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(path.join(outputDir, "君君美债利率模型_风险资产评估_20260917.xlsx"));

const summary = await wb.inspect({ kind: "workbook,sheet,formula", maxChars: 9000, tableMaxRows: 8, tableMaxCols: 8, options: { maxResults: 120 } });
await fs.writeFile(path.join(outputDir, "inspect_summary.txt"), summary.ndjson ?? String(summary));

console.log(JSON.stringify({
  output: path.join(outputDir, "君君美债利率模型_风险资产评估_20260917.xlsx"),
  previews: ["模型总览.png","因子引擎.png","风险资产.png"].map(x=>path.join(outputDir,x)),
}, null, 2));
