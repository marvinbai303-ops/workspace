import csv,json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'normalized';OUT.mkdir(exist_ok=True)
cal=sorted(r['date'].replace('-','') for r in csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/上证指数_日线及VW_MACD.csv').open(encoding='utf-8-sig')))
eod={r['code']:r for r in csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/全市场日终_2026-11-16.csv').open(encoding='utf-8-sig'))}
jobs=json.loads((ROOT/'ma_price_jobs.json').read_text());series=defaultdict(dict);complete_batches=[]
for j in jobs:
 f=ROOT/'downloads'/f"{j['name']}_0.csv"
 if not f.exists():continue
 rows=list(csv.DictReader(f.open(encoding='utf-8-sig')))
 assert len(rows)==442*len(j['expected_codes']),(f,len(rows))
 assert {r['证券代码'] for r in rows}==set(j['expected_codes'])
 for r in rows:
  if r['日期'] in cal and r['收盘价'].strip():series[r['证券代码']][r['日期']]=D(r['收盘价'])
 complete_batches.append(j['name'])
# 加入前轮已独立验收的三只股票，用作均线参数及分红调整交叉样本。
for r in csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/三只股票_前复权有效日线.csv').open(encoding='utf-8-sig')):
 series[r['code']][r['date'].replace('-','')]=D(r['close_qfq'])
records=[];anchor_differences=[]
for c,prices in sorted(series.items()):
 if prices['20261116']!=D(eod[c]['close_unadjusted']):anchor_differences.append(dict(code=c,qfq_last=str(prices['20261116']),unadjusted_last=eod[c]['close_unadjusted']))
 rec=dict(code=c,name=eod[c]['name'],date='2026-11-16',close=prices['20261116'],available_trading_dates=len(prices))
 for n in [20,60,250]:
  dates=cal[-n:];available=all(d in prices for d in dates)
  rec[f'MA{n}']=sum(prices[d] for d in dates)/n if available else None
  rec[f'above_MA{n}']=int(prices['20261116']>rec[f'MA{n}']) if available else None
 records.append(rec)
with (OUT/'旧口径_市场交易日补前收均线对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
result=dict(complete_price_batches=len(complete_batches),benchmark_codes=len(records),
             adjustment_anchor_differences=anchor_differences,
             complete_by_period={n:sum(r[f'MA{n}'] is not None for r in records) for n in [20,60,250]},
             note='Historical comparison only: this script uses market-calendar filled prices, not the newly confirmed individual actual-bar MA policy. Do not use for accepted MA proportions. Truncated responses are excluded.')
(ROOT/'ma_benchmark_status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(result)
