import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def payload(name):
 r=json.loads((ROOT/'raw'/f'{name}.json').read_text())['result']
 return json.loads(r['content'][0]['text'])['data']
def rows(name):
 f=ROOT/'downloads'/f'{name}_0.csv'
 if f.exists():return list(csv.DictReader(f.open(encoding='utf-8-sig')))
 s=payload(name)['answer'].replace('\\n','\n')
 table=[[v.strip() for v in x.strip().strip('|').split('|')] for x in s.splitlines() if x.strip().startswith('|')]
 return [dict(zip(table[0],r)) for r in table[2:] if len(r)==len(table[0])]
allrows=[]
for pre in '000 001 002 003 300 301 302 600 601 603 605 688 689'.split():
 name='today_pool_'+pre;rs=rows(name)
 assert len(rs)==payload(name)['selectedSecuritiesCount']<1000,(name,len(rs))
 assert all(r['股票代码'].startswith(pre) for r in rs)
 allrows+=rs
codes=sorted(r['股票代码'] for r in allrows)
assert len(codes)==len(set(codes))==payload('today_pool_all')['selectedSecuritiesCount']
assert all(c.endswith(('.SH','.SZ')) for c in codes)
assert all('ST' not in r['股票简称'].upper() for r in allrows)
(ROOT/'today_universe.json').write_text(json.dumps(sorted(allrows,key=lambda r:r['股票代码']),ensure_ascii=False,indent=2))
jobs=[]
for i in range(0,len(codes),10):
 jobs.append({'name':f'noon_{i//10:04d}','tool':'stock_highfreq_quotes','args':{'symbols':','.join(codes[i:i+10]),'indicators':'收盘价,成交量,成交额,涨跌,换手率','data_mode':'highfreq','interval':60}})
(ROOT/'noon_jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2))
eod=list(csv.DictReader((ROOT.parent/'ifind_batch_retry_2026-11-17/normalized/全市场日终_2026-11-16.csv').open(encoding='utf-8-sig')))
eodcodes=sorted(r['code'] for r in eod)
assert set(eodcodes)<=set(codes)
jobs=[]
for i in range(0,len(eodcodes),6):
 cc=eodcodes[i:i+6]
 query='A股股票'+','.join(cc)+'，2025-09-01至2026-11-16逐日前复权收盘价，复权基准日2026-11-16。只取收盘价，提供全部下载文件。'
 jobs.append({'name':f'ma_prices_{i//6:04d}','tool':'get_stock_performance','args':{'query':query},'expected_codes':cc})
(ROOT/'ma_price_jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2))
print(json.dumps({'today_count':len(codes),'extra_vs_eod':sorted(set(codes)-set(eodcodes)),'noon_batches':(len(codes)+9)//10,'ma_batches':len(jobs)},ensure_ascii=False))
