import csv,importlib.util,json
from pathlib import Path
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'normalized';OUT.mkdir(exist_ok=True)
def payload(name):
 r=json.loads((ROOT/'raw'/f'{name}.json').read_text())['result']
 assert not r.get('isError') and r.get('ok') is not False,name
 return json.loads(r['content'][0]['text'])['data']
jobs=json.loads((ROOT/'noon_jobs.json').read_text())
universe=json.loads((ROOT/'today_universe.json').read_text())
codes={r['股票代码'] for r in universe}
eod={r['code']:r for r in csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/全市场日终_2026-11-16.csv').open(encoding='utf-8-sig'))}
status=payload('noon_missing4_status')
assert status['indicators_params']['交易状态']['截止日期']=='20261117'
st=status['answer'].replace('\\n','\n')
tab=[[v.strip() for v in x.strip().strip('|').split('|')] for x in st.splitlines() if x.strip().startswith('|')]
status_rows=[dict(zip(tab[0],r)) for r in tab[2:] if len(r)==len(tab[0])]
suspended={r['证券代码']:r['交易状态'] for r in status_rows if '连续停牌' in r['交易状态']}
assert len(suspended)==4
records=[];seen=set();excluded=[];changed_refs=[];float_changes=[];retries=[]
for j in jobs:
 name=j['name']
 if (ROOT/'raw'/f'{name}_retry.json').exists():name+='_retry';retries.append(name)
 tab=payload(name)['tables'];bars=[dict(zip(tab[0],r)) for r in tab[1:]]
 expected=j['args']['symbols'].split(',')
 assert {r['证券代码'] for r in bars}<=set(expected)
 for c in expected:
  assert c not in seen;seen.add(c)
  am=sorted([r for r in bars if r['证券代码']==c and r['time']<='2026-11-17 11:30'],key=lambda r:r['time'])
  if not am:
   assert c in suspended,('missing without suspension proof',c)
   excluded.append(dict(code=c,reason=suspended[c]));continue
  assert [r['time'] for r in am]==['2026-11-17 10:30','2026-11-17 11:30'],c
  close=D(am[-1]['收盘价']);ref=D(am[0]['收盘价'])-D(am[0]['涨跌'])
  amt=sum(D(r['成交额']) for r in am);vol=sum(D(r['成交量']) for r in am);turn=sum(D(r['换手率']) for r in am)
  assert ref>0 and close>0 and amt>0 and vol>0 and turn>=0,c
  assert close-ref==sum(D(r['涨跌']) for r in am),('change chain',c)
  if c in eod and ref!=D(eod[c]['close_unadjusted']):changed_refs.append(dict(code=c,reference=ref,previous_raw_close=eod[c]['close_unadjusted']))
  if c in eod and turn>0 and D(eod[c]['turnover_pct'])>0:
   f_today=100*vol/turn;f_prior=100*D(eod[c]['volume_shares'])/D(eod[c]['turnover_pct'])
   if abs(f_today/f_prior-1)>D('.01'):float_changes.append(dict(code=c,today_inferred_float=f_today,prior_inferred_float=f_prior))
  records.append(dict(date='2026-11-17',time='11:30',code=c,name=am[-1]['证券简称'],
                      close=close,reference_previous_close=ref,return_pct=100*(close/ref-1),
                      volume_shares=vol,amount_yuan=amt,vendor_hourly_turnover_pct=turn,
                      turnover_denominator_status='needs_current_float_confirmation' if c in ['301055.SZ','688653.SH'] else 'vendor_field_not_individually_recomputed',source=name))
assert seen==codes
assert len(records)+len(excluded)==len(codes)
records.sort(key=lambda r:r['code'])
spec=importlib.util.spec_from_file_location('indicators',ROOT.parent/'core_indicators_2026-11-16/indicators.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
rr=[{k:(float(v) if isinstance(v,D) else v) for k,v in r.items()} for r in records]
metrics=mod.aggregate_stocks(rr,[r['code'] for r in records])[0]
h5=sum(r['vendor_hourly_turnover_pct']>5 for r in records)
up=[r for r in records if r['return_pct']>0];down=[r for r in records if r['return_pct']<0]
metrics.update(mod.breadth(len(up),len(down),len(records)-len(up)-len(down),
                          float(sum(r['amount_yuan'] for r in up)),float(sum(r['amount_yuan'] for r in down)),
                          float(sum(r['volume_shares'] for r in up)),float(sum(r['volume_shares'] for r in down))))
metrics['total_amount_including_flat']=float(sum(r['amount_yuan'] for r in records))
metrics.update(turnover_gt5_count=h5,turnover_gt5_pct=100*h5/len(records),time='11:30',eligible_count=len(records),universe_before_no_trade_exclusion=len(codes))
bycode={r['code']:r for r in records}
old=list(csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/午盘样本_2026-11-17_1130.csv').open(encoding='utf-8-sig')))
for r in old:
 if r['code'] not in eod:continue
 n=bycode[r['code']]
 for a,b in [('close','close'),('volume_shares','morning_volume_shares'),('amount_yuan','morning_amount_yuan'),('reference_previous_close','reference_previous_close')]:assert n[a]==D(r[b]),(r['code'],a)
for name,rs in [('全市场午盘_2026-11-17_1130.csv',records),('午盘剔除股票_2026-11-17.csv',excluded)]:
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
result=dict(metrics=metrics,requested_batches=len(jobs),retry_batches=retries,missing_unresolved=[],excluded=excluded,
            reference_close_differs_from_prior_raw_close=changed_refs,implied_float_change_gt1pct=float_changes,
            check_original_three_stock_samples=True,reference_method='first completed 60-minute bar close minus its period price change; both morning price changes sum to the noon price change',
            turnover_method='sum of the two completed morning vendor hourly-turnover percentages; not a full-universe independent volume/float recomputation',
            turnover_denominator_pending=['301055.SZ','688653.SH'],
            cutoff='2026-11-17 11:30 Asia/Shanghai')
(ROOT/'noon_audit_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=lambda x:float(x))+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2,default=lambda x:float(x)))
