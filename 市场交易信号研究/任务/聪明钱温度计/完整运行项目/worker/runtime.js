// The published page and audited seed are prepended by assemble.py.
const response=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const toolNames=[
 {name:'get_thermometer',description:'读取聪明钱温度计的数据状态与最近快照；full=true 时返回完整已保存数据。',inputSchema:{type:'object',properties:{full:{type:'boolean'}},additionalProperties:false}},
 {name:'initialize_thermometer',description:'将发布版本中已验收的初始数据写入持久存储。已有数据时只读回，不覆盖。',inputSchema:{type:'object',properties:{},additionalProperties:false}},
 {name:'update_thermometer',description:'保存由工作区 build_data.py 复算和验收的完整看板 JSON，并读回校验。保留所有原有快照；禁止修改既有历史值。',inputSchema:{type:'object',properties:{data_json:{type:'string',description:'data/dashboard.json 的完整 UTF-8 JSON 内容'}},required:['data_json'],additionalProperties:false}}
];
function summary(d){return {generatedAt:d.generatedAt,latestDate:d.latestDate,snapshotCount:d.snapshots.length,latestSnapshot:d.snapshots.at(-1),mclLast:d.mcl.at(-1),etfLast:d.etfs.at(-1),vwDailyLast:d.vwMacd?.daily.at(-1),vwWeeklyLast:d.vwMacd?.weekly.at(-1),schedule:d.schedule}}
async function stored(env){const item=env.BUCKET?await env.BUCKET.get('dashboard/latest.json'):null;return item?await item.json():null}
function check(d){
 if(d.schemaVersion!==1||!Array.isArray(d.snapshots)||!d.snapshots.length||!Array.isArray(d.mcl)||!d.mcl.length||!Array.isArray(d.etfs)||!Array.isArray(d.sources)||!d.schedule)throw Error('缺必要数据结构');
 if(!Number.isFinite(Date.parse(d.generatedAt)))throw Error('生成时间无效');
 const keys=new Set();let prior='';
 for(const s of d.snapshots){const key=s.date+' '+s.time;if(!/^\d{4}-\d{2}-\d{2}$/.test(s.date)||!['noon','eod'].includes(s.session)||s.time!==(s.session==='noon'?'11:30':'15:00')||keys.has(key)||key<prior)throw Error('日期、时点或排序无效');keys.add(key);prior=key;
  if(![s.A,s.D,s.U,s.count].every(x=>Number.isInteger(x)&&x>=0)||s.A+s.D+s.U!==s.count||!s.count)throw Error('家数验收失败');
  if(![s.upAmount,s.downAmount,s.flatAmount,s.totalAmount,s.upVolume,s.downVolume].every(x=>Number.isFinite(x)&&x>=0))throw Error('成交字段无效');
  const close=(a,b)=>a===null&&b===null||Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<1e-7;
  const p=s.A+s.D?100*s.A/(s.A+s.D):null,q=s.upAmount+s.downAmount?100*s.upAmount/(s.upAmount+s.downAmount):null;
  const two=!!(s.A&&s.D);if(two&&(!s.upAmount||!s.downAmount||!s.upVolume||!s.downVolume))throw Error('非零家数组缺成交');
  if(!close(s.p,p)||!close(s.q,q)||!close(s.gap,two?q-p:null)||!close(s.trin,two?s.A*s.downAmount/(s.D*s.upAmount):null)||!close(s.trinVolume,two?s.A*s.downVolume/(s.D*s.upVolume):null))throw Error('公式复算不一致');
  if(Math.abs(s.totalAmount-s.upAmount-s.downAmount-s.flatAmount)>.1||!s.sources?.length)throw Error('合计或来源缺失');
 }
 if(d.latestDate!==d.snapshots.at(-1).date)throw Error('最新日期不一致');
 let fast=null,slow=null,last='';for(const [i,r] of d.mcl.entries()){if(r.date<=last||![r.A,r.D,r.U].every(x=>Number.isInteger(x)&&x>=0))throw Error('MCL 序列无效');last=r.date;const n=r.A-r.D;fast=fast===null?n:.1*n+.9*fast;slow=slow===null?n:.05*n+.95*slow;if(Math.abs(r.mcl-(fast-slow))>1e-7||r.warmed!==(i>=200))throw Error('MCL 原式复算失败');}
 for(const r of d.etfs){if(!Array.isArray(r.parts)||r.parts.length!==3||new Set(r.parts.map(p=>p.code)).size!==3||r.parts.some(p=>!['510050.SH','510300.SH','588000.SH'].includes(p.code)||!Number.isFinite(p.amount)||p.amount<0)||Math.abs(r.parts.reduce((a,p)=>a+p.amount,0)-r.amount)>.1)throw Error('ETF 合计验收失败');}
 for(const s of d.sources)if(!/^[a-f0-9]{64}$/.test(s.sha256))throw Error('来源指纹缺失');
 if(d.vwMacd){
  if(d.vwMacd.code!=='000001.SH'||JSON.stringify(d.vwMacd.parameters)!=='[12,26,9]')throw Error('VW-MACD 对象或参数不一致');
  for(const period of ['daily','weekly']){const rows=d.vwMacd[period];if(!Array.isArray(rows)||rows.length<26)throw Error('VW历史不足');let dea=null,last='';
   for(let i=0;i<rows.length;i++){const r=rows[i];if(r.date<=last||!Number.isFinite(r.close)||r.close<=0||!Number.isFinite(r.volume)||r.volume<=0)throw Error('VW原始输入无效');last=r.date;
    if(i<25){if(r.dif!==null||r.dea!==null||r.histogram!==null)throw Error('VW预热错误');continue;}
    const vw=n=>{const win=rows.slice(i+1-n,i+1);return win.reduce((s,x)=>s+x.close*x.volume,0)/win.reduce((s,x)=>s+x.volume,0)};
    const dif=vw(12)-vw(26);dea=dea===null?dif:.2*dif+.8*dea;
    if(!['dif','dea','histogram'].every(k=>Number.isFinite(r[k]))||Math.abs(r.dif-dif)>1e-7||Math.abs(r.dea-dea)>1e-7||Math.abs(r.histogram-2*(dif-dea))>1e-7)throw Error('VW-MACD原式复算失败');
   }
  }
 }
}
function preserve(old,next){if(old.vwMacd){if(!next.vwMacd)throw Error('禁止丢失VW历史');for(const period of ['daily','weekly'])for(const r of old.vwMacd[period]){const n=next.vwMacd[period].find(x=>x.date===r.date);if(!n||n.close!==r.close||n.volume!==r.volume)throw Error('禁止改写既有VW输入');}}for(const r of old.snapshots){const n=next.snapshots.find(s=>s.date===r.date&&s.session===r.session);if(!n||['A','D','U','upAmount','downAmount','upVolume','downVolume'].some(k=>n[k]!==r[k]))throw Error('禁止丢失或未经核验地改写历史快照');}for(const r of old.mcl){const n=next.mcl.find(s=>s.date===r.date);if(!n||['A','D','U','mcl'].some(k=>n[k]!==r[k]))throw Error('禁止改写既有 MCL 历史');}}
async function write(env,d){if(!env.BUCKET)throw Error('持久存储尚未连接');check(d);const raw=JSON.stringify(d);await env.BUCKET.put('dashboard/latest.json',raw,{httpMetadata:{contentType:'application/json'}});const read=await stored(env);if(JSON.stringify(read)!==raw)throw Error('写入后读回不一致');const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw)))).map(x=>x.toString(16).padStart(2,'0')).join('');return {persisted:true,readbackVerified:true,sha256:digest,...summary(read)}}
export default {async fetch(request,env){const path=new URL(request.url).pathname;
 if(path==='/'&&request.method==='GET')return new Response(PAGE,{headers:{'content-type':'text/html; charset=utf-8','cache-control':'no-cache','x-content-type-options':'nosniff'}});
 if(path==='/api/data'&&request.method==='GET')return response((await stored(env))||SEED);
 if(path==='/mcp'&&request.method==='POST'){let body;try{body=await request.json()}catch{return response({error:'Invalid JSON'},400)}const reply=result=>response({jsonrpc:'2.0',id:body.id??null,result});
  if(body.method==='server/discover')return reply({supportedVersions:['2026-07-28','2025-03-26'],capabilities:{tools:{}}});
  if(body.method==='initialize')return reply({protocolVersion:body.params?.protocolVersion||'2025-03-26',serverInfo:{name:'smart-money-thermometer',version:'1.0.0'},capabilities:{tools:{}}});
  if(body.method==='notifications/initialized')return new Response(null,{status:204});
  if(body.method==='tools/list')return reply({tools:toolNames});
  if(body.method==='tools/call'){if(!request.headers.get('oai-authenticated-user-id'))return response({error:'Authenticated Site owner required'},403);
   try{const name=body.params?.name,args=body.params?.arguments||{},current=(await stored(env));let result;
    if(name==='get_thermometer')result=args.full?current||SEED:{persisted:!!current,...summary(current||SEED)};
    else if(name==='initialize_thermometer')result=current?{persisted:true,alreadyInitialized:true,...summary(current)}:await write(env,SEED);
    else if(name==='update_thermometer'){if(typeof args.data_json!=='string'||args.data_json.length>4000000)throw Error('输入格式或大小不合规');const next=JSON.parse(args.data_json);check(next);preserve(current||SEED,next);result=await write(env,next);}
    else throw Error('Unknown tool');return reply({content:[{type:'text',text:JSON.stringify(result)}]});
   }catch(e){return reply({isError:true,content:[{type:'text',text:e.message}]})}
  }return response({jsonrpc:'2.0',id:body.id??null,error:{code:-32601,message:'Method not found'}});
 }return new Response('Not found',{status:404});}};
