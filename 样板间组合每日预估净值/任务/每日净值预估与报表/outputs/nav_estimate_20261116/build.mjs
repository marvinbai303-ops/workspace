import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const dir=fileURLToPath(new URL('.',import.meta.url));
const m=JSON.parse(await fs.readFile(dir+'model.json','utf8'));
const wb=Workbook.create();
const names=['评估汇总',...m.funds.map(f=>f.code),'持仓与计算','成分股行情','实际净值','半年报完整持仓','方法与来源'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const C={navy:'#17365D',blue:'#376CB0',green:'#24836F',grey:'#66758A',pale:'#EEF3FA',orange:'#FFF0D9'};
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const date=s=>new Date(s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8)+'T00:00:00Z');
function put(s,r,c,a){if(a.length)s.getRangeByIndexes(r-1,c-1,a.length,a[0].length).values=a;}
function form(s,r,c,a){if(a.length)s.getRangeByIndexes(r-1,c-1,a.length,a[0].length).formulas=a;}
function base(s,end='V70'){s.showGridLines=false;s.getRange('A1:'+end).format.font={name:'Arial',size:10,color:'#172C45'};s.getRange('A1:'+end).format.rowHeight=21;s.getRange('A1:'+end).format.verticalAlignment='center';s.getRange('A1:'+end).format.columnWidth=13;}
function title(s,t,end='K'){s.getRange('A2').values=[[t]];s.getRange('A2').format.font={size:15,bold:true,color:C.navy};s.getRange('A3:'+end+'3').format.borders={bottom:{style:'thin',color:C.navy}};s.getRange('A2').format.rowHeight=26;}
function head(s,row,labels){put(s,row,1,[labels]);const r=s.getRangeByIndexes(row-1,0,1,labels.length);r.format={fill:C.navy,font:{color:'#FFFFFF',bold:true},horizontalAlignment:'center',wrapText:true,rowHeight:34};}
function stripe(s,start,end,width){for(let r=start;r<=end;r++)if((r-start)%2===0)s.getRange(`A${r}:${col(width-1)}${r}`).format.fill='#F4F7FB';}
const pct='0.00%;[Red](0.00%);"—"';const bp='0.0;[Red](0.0);"—"';
const pars=sheets['方法与来源'];base(pars,'H36');title(pars,'计算口径与数据来源','H');pars.getRange('A:A').format.columnWidth=25;pars.getRange('B:H').format.columnWidth=19;
const notes=[
['模拟基准日','2026-09-30。首个收益日为2026-10-08，最后实际净值日为2026-11-13。'],
['交易日口径','剔除周末及国庆休市；港股按相邻基金净值日的价格比计算，跨假期收益不会漏记。'],
['简单预估','股票总仓位 × 三季报披露重仓股票的归一化加权收益；非股票资产收益按0处理。'],
['复合预估','三季报披露权重保留，剩余股票仓位由半年报未重叠持股补全，再加滞后误差校正。'],
['持仓补全','半年报占净资产比例≥0.10%的股票进入候选池；剔除三季报已披露证券后，按半年报相对权重分配剩余仓位。'],
['补全的局限','旧持股仅是推测尾部的代理，不能视为9月30日真实全持仓。被剔除的微小持仓包含在同一尾部代理中。'],
['每日误差校正','取前5个交易日（实际收益－补全原始预估）的均值×0.5，限制在±30bp；前5日不校正。'],
['参数选择','窗口、缩减比例和上限均为预先固定的启发式设置，未按本轮样本优化。只使用t−1及更早净值。'],
['净值校正','当日锚定预估净值＝前一日实际复权净值×(1＋当日复合预估)。与未重置的累计曲线分别展示。'],
['累计曲线','三条曲线均从9月30日归一为1。两种预估均逐日连乘，不用实际净值重置，以保留累计漂移。'],
['公平评估','主表只评价披露日下一交易日起的日收益误差；全期事后模拟单列。发布前结果含持仓前视信息。'],
['历史训练','披露后可以用已知季报权重重建过去收益并训练校正；预测当日的实际净值不得进入当日预测。'],
['股票权重','两法均固定股票总仓位，不模拟基金经理每日交易。三季报权重为披露占净资产比，不混用A/C份额规模。'],
['A/H证券','同一发行人A/H股分别保留，因此个别基金披露清单超过10个证券代码。'],
['价格与汇率','股票采用iFinD前复权收盘价。港股收益折算人民币，使用中国外汇交易中心港元人民币中间价的日变化代理。'],
['估值差异','中间价不等于基金最终会计估值汇率。分红复权、限售股估值、交易费用及非股票资产也可能产生偏差。'],
['实际涨跌幅','iFinD复权单位净值的相邻基金交易日之比减1，含分红再投资口径；不使用行情接口重复填充的周末增长率。'],
['净值发布时间','假定前一交易日净值在下一日预估前已知；若个别日延迟披露，应延后使用。缺少逐日实际发布时间，未做该项校验。'],
['评价指标','MAE为平均绝对误差，RMSE为均方根误差，误差＝预估－实际。1bp＝0.01个百分点；改善为负表示复合更差。'],
['iFinD','股票总仓位、复权基金净值、前复权股价、汇率；原始工具返回已留档，查询日期2026-11-16。'],
['妙想（东方财富）','三季报基金重仓持股明细及披露日期。iFinD未完整返回单只权重后，按用户指定顺序补取。'],
['Wind','半年报全部股票持仓。iFinD和妙想只返回重仓股后补取；数据来源于万得Wind金融数据服务。'],
['公告交叉核对','嘉实前沿创新三季报送出日期2026-10-27，股票仓位与披露权重通过公开报告及数据源交叉核验。'],
['公告链接','https://www.hongdianfund.com/FundAnnouncement/Detail/009993/0000000000001skgcs'],
['交易日来源','https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml'],
['组合口径','按用户要求仅逐只基金比较，不使用等权或猜测组合权重。'],
];
notes.forEach((r,i)=>{put(pars,5+i,1,[[r[0]]]);put(pars,5+i,2,[[r[1]]]);});pars.getRange('B5:B30').format.columnWidth=112;pars.getRange('B5:B30').format.wrapText=true;pars.getRange('A5:B30').format.rowHeight=34;
// Authoritative controls and fund inputs on the holdings sheet.
const h=sheets['持仓与计算'];base(h,'AK300');title(h,'披露持仓与每日计算输入','AK');
put(h,4,1,[['校正窗口',5,'缩减比例',.5,'校正上限',.003,'半年报筛选门槛',.001]]);h.getRange('B4').format.fill=C.orange;h.getRange('D4').format.fill=C.orange;h.getRange('F4').format.fill=C.orange;h.getRange('D4').setNumberFormat('0%');h.getRange('F4:H4').setNumberFormat('0.00%');
head(h,6,['基金代码','基金名称','股票总仓位','三季报披露权重','尾部仓位','半年报候选合计','报告披露日','候选股数']);
m.funds.forEach((f,i)=>{const r=7+i;put(h,r,1,[[f.code+".OF",f.name,f.stockpos,null,null,f.half_tail_sum,new Date(f.disclosure+'T00:00:00Z'),f.tail_count]]);});h.getRange('B:B').format.columnWidth=23;h.getRange('C7:F13').setNumberFormat('0.00%');h.getRange('G7:G13').setNumberFormat('yyyy-mm-dd');h.getRange('C7:C13').format.font.color='#245CC0';
put(h,15,1,[['来源：三季报权重为妙想/东方财富，股票总仓位为iFinD；半年报候选为Wind。权重均为净资产口径。']]);
const holdStart=18;head(h,17,['基金代码','证券代码','证券名称','持仓来源','披露原权重','简单法权重','复合法权重','报告期',...m.dates.slice(1).map(d=>date(d))]);h.getRange('I17:'+col(7+m.dates.length-1)+'17').setNumberFormat('mm-dd');
const ranges={};m.holdings.forEach((x,i)=>{const r=holdStart+i;const fi=m.funds.findIndex(f=>f.code===x.fund);const fr=7+fi;put(h,r,1,[[x.fund+".OF",x.code,x.name,x.role,x.weight,null,null,new Date(x.period+'T00:00:00Z')]]);if(!ranges[x.fund])ranges[x.fund]=[r,r];else ranges[x.fund][1]=r;form(h,r,6,[[x.role==='三季报披露'?`=E${r}*$C$${fr}/$D$${fr}`:'=0',x.role==='三季报披露'?`=E${r}`:`=E${r}*$E$${fr}/$F$${fr}`]]);});
m.funds.forEach((f,i)=>{let [a,b]=ranges[f.code],r=7+i;form(h,r,4,[[`=SUMIF(D${a}:D${b},"三季报披露",E${a}:E${b})`,`=C${r}-D${r}`]]);});
h.getRange(`E${holdStart}:G${holdStart+m.holdings.length-1}`).setNumberFormat('0.000%');h.getRange(`H${holdStart}:H${holdStart+m.holdings.length-1}`).setNumberFormat('yyyy-mm-dd');h.getRange('A:A').format.columnWidth=13;h.getRange('C:D').format.columnWidth=20;h.freezePanes.freezeRows(17);h.freezePanes.freezeColumns(3);
m.funds.forEach((f,i)=>{const [a,b]=ranges[f.code];form(h,7+i,6,[[`=SUMIF(D${a}:D${b},"半年报尾部候选",E${a}:E${b})`]]);form(h,7+i,8,[[`=COUNTIF(D${a}:D${b},"半年报尾部候选")`]]);});
m.holdings.forEach((x,i)=>{if(x.role==='半年报尾部候选'){let ri=m.h1raw.findIndex(t=>t.fund===x.fund&&t.code===x.code);form(h,holdStart+i,5,[[`='半年报完整持仓'!D${ri+7}`]]);}});
// Prices and FX above, return calculations below.
const p=sheets['成分股行情'];let priceStart=8,returnHead=priceStart+m.stocks.length+3,returnStart=returnHead+1;base(p,`AF${returnStart+m.stocks.length+1}`);title(p,'成分股复权价格与人民币收益','AF');put(p,4,1,[['来源：iFinD每日前复权收盘价；港元人民币中间价来自中国外汇交易中心，经iFinD取得。']]);put(p,5,1,[['港元人民币中间价',null,null,...m.fx]]);head(p,7,['证券代码','证券名称','市场',...m.dates.map(date)]);p.getRange('D7:AE7').setNumberFormat('mm-dd');
m.stocks.forEach((x,i)=>put(p,priceStart+i,1,[[x.code,x.name,x.hk?'HK':'境内',...x.prices]]));p.getRange(`D${priceStart}:AE${priceStart+m.stocks.length-1}`).setNumberFormat('0.0000');p.getRange('D5:AE5').setNumberFormat('0.0000');head(p,returnHead,['证券代码','证券名称','人民币收益',...m.dates.slice(1).map(date)]);p.getRange(`D${returnHead}:AD${returnHead}`).setNumberFormat('mm-dd');
m.stocks.forEach((x,i)=>{let r=returnStart+i,pr=priceStart+i;put(p,r,1,[[x.code,x.name,x.hk?'含汇率变动':'前复权收益']]);form(p,r,4,[m.dates.slice(1).map((d,j)=>`=${col(j+4)}${pr}/${col(j+3)}${pr}${x.hk?`*${col(j+4)}$5/${col(j+3)}$5`:''}-1`)]);});p.getRange(`D${returnStart}:AD${returnStart+m.stocks.length-1}`).setNumberFormat(pct);p.getRange('B:B').format.columnWidth=20;p.getRange('A:A').format.columnWidth=15;p.freezePanes.freezeRows(7);p.freezePanes.freezeColumns(3);
m.holdings.forEach((x,i)=>{let sr=returnStart+m.stocks.findIndex(s=>s.code===x.code);form(h,holdStart+i,9,[m.dates.slice(1).map((d,j)=>`='成分股行情'!${col(j+3)}${sr}`)]);});h.getRange(`I18:AI${holdStart+m.holdings.length-1}`).setNumberFormat(pct);
const a=sheets['实际净值'];base(a,'H38');title(a,'实际复权单位净值','H');put(a,4,1,[['来源：iFinD get_fund_market_performance，取数日期2026-11-16。剔除非交易日重复填值。']]);head(a,6,['净值日期',...m.funds.map(f=>f.name)]);put(a,7,1,m.dates.map((d,i)=>[date(d),...m.funds.map(f=>m.nav[f.code][i])]));a.getRange('A7:A34').setNumberFormat('yyyy-mm-dd');a.getRange('B7:H34').setNumberFormat('0.0000');a.getRange('A:H').format.columnWidth=20;a.freezePanes.freezeRows(6);
const raw=sheets['半年报完整持仓'];base(raw,'G335');title(raw,'半年报完整股票持仓','G');put(raw,4,1,[['来源：Wind fund_get_equity_holdings，报告期2026-06-30。保留全部返回行；显示为0的披露权重可能为四舍五入。']]);head(raw,6,['基金代码','证券代码','证券名称','披露占净资产比','补全候选','报告期']);put(raw,7,1,m.h1raw.map(x=>[x.fund+".OF",x.code,x.name,x.weight,x.included?'纳入':'未纳入',new Date(x.period+'T00:00:00Z')]));raw.getRange(`D7:D${6+m.h1raw.length}`).setNumberFormat('0.00%');raw.getRange(`F7:F${6+m.h1raw.length}`).setNumberFormat('yyyy-mm-dd');raw.getRange('A:F').format.columnWidth=20;raw.freezePanes.freezeRows(6);
// Each fund has the same calculation flow; no result is hardcoded.
const fundMetricRows={};
m.funds.forEach((f,fi)=>{const s=sheets[f.code];base(s,'V76');s.tabColor=C.blue;title(s,f.name+' 预估与实际对照','V');put(s,4,1,[['股票总仓位',null,'三季报覆盖',null,'披露日',null,'样本截止','2026-11-13']]);form(s,4,2,[[`='持仓与计算'!C${7+fi}`]]);form(s,4,4,[[`='持仓与计算'!D${7+fi}`]]);form(s,4,6,[[`='持仓与计算'!G${7+fi}`]]);s.getRange('B4:D4').setNumberFormat('0.00%');s.getRange('F4').setNumberFormat('yyyy-mm-dd');put(s,6,1,[['披露日之前为事后持仓模拟；校正只使用前一日及更早数据。主评估仅纳入披露后交易日。']]);
head(s,8,['日期','实际涨跌幅','简单预估','复合预估','简单误差bp','复合误差bp','实际复权净值','复合锚定净值','实际累计净值','简单累计净值','复合累计净值','补全原始预估','滞后校正','补全残差','简单绝对误差bp','复合绝对误差bp','简单平方误差','复合平方误差','简单方向正确','复合方向正确','披露后可用','图表日期']);
let n=m.dates.length,end=8+n;put(s,9,1,[[date(m.dates[0])]]);form(s,9,7,[[`='实际净值'!${col(fi+1)}7`]]);put(s,9,9,[[1,1,1]]);form(s,9,22,[['=TEXT(A9,"mm-dd")']]);let [ha,hb]=ranges[f.code];
for(let i=1;i<n;i++){let r=9+i;put(s,r,1,[[date(m.dates[i])]]);let srccol=col(i+7);form(s,r,2,[[`=G${r}/G${r-1}-1`,`=SUMPRODUCT('持仓与计算'!$F$${ha}:$F$${hb},'持仓与计算'!${srccol}${ha}:${srccol}${hb})`,`=L${r}+M${r}`,`=(C${r}-B${r})*10000`,`=(D${r}-B${r})*10000`,`='实际净值'!${col(fi+1)}${7+i}`,`=G${r-1}*(1+D${r})`,`=G${r}/$G$9`,`=J${r-1}*(1+C${r})`,`=K${r-1}*(1+D${r})`,`=SUMPRODUCT('持仓与计算'!$G$${ha}:$G$${hb},'持仓与计算'!${srccol}${ha}:${srccol}${hb})`,`=IF(ROW()-10<'持仓与计算'!$B$4,0,MAX(-'持仓与计算'!$F$4,MIN('持仓与计算'!$F$4,'持仓与计算'!$D$4*AVERAGE(INDEX(N:N,MAX(10,ROW()-'持仓与计算'!$B$4)):N${r-1}))))`,`=B${r}-L${r}`,`=ABS(E${r})`,`=ABS(F${r})`,`=E${r}^2`,`=F${r}^2`,`=IF(SIGN(C${r})=SIGN(B${r}),1,0)`,`=IF(SIGN(D${r})=SIGN(B${r}),1,0)`,`=IF(A${r}>$F$4,1,0)`,`=TEXT(A${r},"mm-dd")`]]);}
s.getRange(`A9:A${end}`).setNumberFormat('yyyy-mm-dd');s.getRange(`B10:D${end}`).setNumberFormat(pct);s.getRange(`E10:F${end}`).setNumberFormat(bp);s.getRange(`G9:K${end}`).setNumberFormat('0.0000');s.getRange(`L10:N${end}`).setNumberFormat(pct);s.getRange(`O10:R${end}`).setNumberFormat('0.0');s.getRange('A:A').format.columnWidth=15;s.getRange('B:V').format.columnWidth=15;s.getRange('G:K').format.columnWidth=16;stripe(s,9,end,22);s.freezePanes.freezeRows(8);s.freezePanes.freezeColumns(1);
let chart=s.charts.add('line',[s.getRange(`V8:V${end}`),s.getRange(`I8:I${end}`),s.getRange(`J8:J${end}`),s.getRange(`K8:K${end}`)]);chart.title='累计模拟净值（9月30日＝1）';chart.setPosition('A40','K58');chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=14;chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};chart.yAxis={numberFormatCode:'0.00',numberFormatSourceLinked:false};[C.navy,C.blue,C.green].forEach((c,i)=>chart.series.items[i].line={fill:c,width:2});
const first=9+m.dates.findIndex(d=>d>f.disclosure.replaceAll('-',''));fundMetricRows[f.code]={start:first,end};
});
const sum=sheets['评估汇总'];base(sum,'L47');sum.tabColor=C.navy;title(sum,'基金净值预估：简单法与复合法','L');put(sum,4,1,[['主评估：三季报披露后的可用交易日。统计日收益误差，不以重置净值后的曲线贴合度评价。']]);
head(sum,6,['基金','评估天数','简单MAE bp','复合MAE bp','MAE改善','简单RMSE bp','复合RMSE bp','简单最大误差bp','复合最大误差bp','复合方向命中率','更准的方法']);
m.funds.forEach((f,i)=>{let r=7+i,{start,end}=fundMetricRows[f.code],ref=`'${f.code}'!`;put(sum,r,1,[[f.name]]);form(sum,r,2,[[`=COUNT(${ref}B${start}:B${end})`,`=AVERAGE(${ref}O${start}:O${end})`,`=AVERAGE(${ref}P${start}:P${end})`,`=1-D${r}/C${r}`,`=SQRT(AVERAGE(${ref}Q${start}:Q${end}))`,`=SQRT(AVERAGE(${ref}R${start}:R${end}))`,`=MAX(${ref}O${start}:O${end})`,`=MAX(${ref}P${start}:P${end})`,`=AVERAGE(${ref}T${start}:T${end})`,`=IF(D${r}<C${r},"复合预估","简单预估")`]]);});sum.getRange('C7:I13').setNumberFormat('0.0');sum.getRange('E7:E13').setNumberFormat('0.0%');sum.getRange('J7:J13').setNumberFormat('0.0%');stripe(sum,7,13,11);
put(sum,16,1,[['全期事后模拟：2026-10-08至2026-11-13。含季报披露前数据，仅用于观察，不等同可执行回测。']]);head(sum,18,['基金','样本天数','简单MAE bp','复合MAE bp','MAE改善','实际累计收益','简单累计收益','复合累计收益','简单期末偏差pp','复合期末偏差pp']);
m.funds.forEach((f,i)=>{let r=19+i,{end}=fundMetricRows[f.code],ref=`'${f.code}'!`;put(sum,r,1,[[f.name]]);form(sum,r,2,[[`=COUNT(${ref}B10:B${end})`,`=AVERAGE(${ref}O10:O${end})`,`=AVERAGE(${ref}P10:P${end})`,`=1-D${r}/C${r}`,`=${ref}I${end}-1`,`=${ref}J${end}-1`,`=${ref}K${end}-1`,`=(G${r}-F${r})*100`,`=(H${r}-F${r})*100`]]);});sum.getRange('C19:D25').setNumberFormat('0.0');sum.getRange('E19:H25').setNumberFormat('0.00%');sum.getRange('I19:J25').setNumberFormat('0.00');stripe(sum,19,25,10);
put(sum,28,1,[['解读：MAE、RMSE和最大误差越小越好；MAE改善为负，说明复合方法更差。1bp＝0.01个百分点。']]);put(sum,30,1,[['重点限制：样本较短、尾部持仓来自半年报代理、港股汇率采用中间价。参数未针对本样本优化。']]);sum.getRange('A:A').format.columnWidth=24;sum.getRange('B:K').format.columnWidth=16;
form(sum,29,1,[['="结果：复合方法在"&COUNTIF(E7:E13,">0")&"只基金改善、"&COUNTIF(E7:E13,"<0")&"只变差。宏利复兴与嘉实前沿创新的日均误差仍偏大。"']]);
const chart=sum.charts.add('bar',[sum.getRange('A6:A13'),sum.getRange('C6:C13'),sum.getRange('D6:D13')]);chart.title='披露后每日平均绝对误差（bp）';chart.setPosition('A33','K48');chart.yAxis={numberFormatCode:'0',numberFormatSourceLinked:false};chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=14;chart.series.items.forEach((s,i)=>s.fill=[C.blue,C.green][i]);
wb.recalculate();
const checks=[];
for(const f of m.funds){const s=sheets[f.code];const expected=m.daily.filter(r=>r.fund===f.code);const values=s.getRange(`B10:F${9+m.dates.length-1}`).values;expected.forEach((r,i)=>{let exp=[r.actual,r.simple,r.composite,r.simple_error*10000,r.composite_error*10000];exp.forEach((v,j)=>{if(typeof values[i][j]!=='number'||Math.abs(values[i][j]-v)>1e-7)checks.push({fund:f.code,row:i+10,col:j+2,actual:values[i][j],expected:v});});});}
await fs.writeFile(dir+'verification.json',JSON.stringify({differences:checks,summary:sheets['评估汇总'].getRange('A6:K13').values},null,2));
if(checks.length)throw Error('Calculation verification failed: '+JSON.stringify(checks.slice(0,4)));
await fs.mkdir(dir+'previews',{recursive:true});
for(const name of names){let range=name==='评估汇总'?'A1:K30':m.funds.some(f=>f.code===name)?'A1:K19':name==='方法与来源'?'A1:B17':name==='持仓与计算'?'A1:H26':name==='成分股行情'?'A1:J17':name==='实际净值'?'A1:H18':'A1:F18';let blob=await wb.render({sheetName:name,range,scale:1.5});await fs.writeFile(dir+'previews/'+name+'.png',new Uint8Array(await blob.arrayBuffer()));}
let ch=await wb.render({sheetName:'009993',range:'A39:K59',scale:1.5});await fs.writeFile(dir+'previews/曲线.png',new Uint8Array(await ch.arrayBuffer()));
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(dir+'产业趋势2号_逐基金净值预估对照.xlsx');
console.log(JSON.stringify({output:dir+'产业趋势2号_逐基金净值预估对照.xlsx',checks:checks.length,sheets:names.length}));
