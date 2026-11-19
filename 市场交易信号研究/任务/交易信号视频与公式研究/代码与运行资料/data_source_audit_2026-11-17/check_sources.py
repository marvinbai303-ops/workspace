"""重放本轮取数核查，不联网。只验收观测到的接口数据，不推断缺失数据。"""
import csv
import json
import math
import sys
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'core_indicators_2026-11-16'))
from indicators import breadth, vw_macd

def payload(name):
    r=json.loads((ROOT/'raw'/f'{name}.json').read_text())
    r=r.get('result',r)
    return json.loads(r['content'][0]['text'])

def tab(name):
    s=payload(name)['data']['answer']
    return [[v.strip() for v in l.strip('|').split('|')] for l in s.splitlines() if l.startswith('|')][2:]

def num(s):
    s=s.strip()
    if s in ['', '\\t', '--']: return None
    for suf,mul in [('万亿',1e12),('亿',1e8),('万',1e4)]:
        if s.endswith(suf): return float(s[:-len(suf)])*mul
    return float(s)

def csv_rows(name):
    with (ROOT/'raw'/name).open(encoding='utf-8-sig') as f: return list(csv.DictReader(f))

def run():
    out={}
    universe=csv_rows('ifind_universe_download.csv')
    out['universe_download']={'requested_count':5027,'downloaded_count':len(universe),'complete':len(universe)==5027}
    part=csv_rows('ifind_partition_fixed.csv')
    assert len(part)==606 and len({r['股票代码'] for r in part})==606
    assert not any('ST' in r['股票简称'] for r in part)
    assert all(float(r['成交额[20261116]'])>0 for r in part)
    assert all(r['股票代码'].endswith('.SH') for r in part)
    out['star_partition']={'count':len(part),'unique':606,'st_names':0,'date':'2026-11-16','complete_partition':True,'historical_status_independently_audited':False}
    tables=payload('wind_filtered_eod')['data']['data']
    vals={t['columns'][0]['name']:t['rows'][0][0] for t in tables if len(t['columns'])==1 and len(t['rows'])==1}
    keys=lambda term:next(v for k,v in vals.items() if term in k)
    a,d,u=keys('大于0的沪深A股家数'),keys('小于0的沪深A股家数'),keys('等于0的沪深A股家数')
    assert a+d+u==5027
    amounts=[]; volumes=[]
    for group in ['大于0','小于0']:
        for t in tables:
            if len(t['columns'])!=1:continue
            c=t['columns'][0]
            if group in c['name'] and '成交额合计' in c['name']:
                amounts.append(t['rows'][0][0]*{'亿元':1e8,'万亿元':1e12}[c['unit']])
            if group in c['name'] and '成交量合计' in c['name']: volumes.append(t['rows'][0][0])
    out['filtered_market_20261116']=breadth(a,d,u,*amounts,*volumes)
    # 193家 ST 与7家零成交有3家交集，不能重复减去。
    zero_table=next(t for t in tables if len(t['rows'])==7)
    overlap=sum('ST' in row[1] for row in zero_table['rows'])
    assert 5224-193-7+overlap==5027
    out['filter_reconciliation']={'before':5224,'st':193,'zero_amount':7,'intersection':overlap,'after':5027}
    history_tables=payload('wind_filtered_history_retry')['data']['data']
    out['filtered_counts_20261113']={t['columns'][0]['name']:t['rows'][0][0] for t in history_tables if len(t['columns'])==1 and len(t['rows'])==1}
    h5=csv_rows('ifind_turnover_filter.csv')
    assert len(h5)==677 and len({r['股票代码'] for r in h5})==677
    assert all(float(r['换手率[20261116]'])>5 for r in h5)
    assert not any('ST' in r['股票简称'] or r['股票代码'].endswith('.BJ') for r in h5)
    out['turnover_above_5']={'count':677,'denominator':5027,'percentage':100*677/5027,'denominator_basis':'same iFinD筛选条件的总数，与Wind汇总家数一致；尚未全量逐股连接审计'}
    out['ordinary_turnover_checks']={'300750.SZ':100*36113461/4260620000,'600519.SH':100*3996700/1250080000}
    etfs=defaultdict(dict)
    for row in tab('ifind_etf_20days'):
        val=num(row[3])
        if val is not None: etfs[row[2]][row[0]]=val
    assert len(etfs)==20 and all(len(v)==3 for v in etfs.values())
    totals=[sum(v.values()) for _,v in sorted(etfs.items())]
    out['etf_amount']={'days':20,'records':60,'last_yuan':totals[-1],'ma20_yuan':sum(totals)/20}
    index=[]
    for row in tab('ifind_vw_shanghai'):
        vol,close=num(row[3]),num(row[4])
        if vol is not None and close is not None:index.append((row[2],close,vol))
    index.sort()
    vwm=vw_macd([r[1] for r in index],[r[2] for r in index])
    out['vw_macd_source_check']={'symbol':'000001.SH','daily_bars':len(index),'first':index[0][0],'last':index[-1][0],'formula_sample':vwm[-1],'warmup_sufficient':False}
    hist=payload('wind_cli_qfq_history')['data']['rows']
    assert len(hist)==291 and len({r[0] for r in hist})==291
    closes=[float(r[2]) for r in hist]
    out['ma_history_check']={'symbol':'600519.SH','daily_bars':291,'last_close':closes[-1],
                             'ma':{str(n):sum(closes[-n:])/n for n in [20,60,250]},'adjustment':'request aftype=0 afdate=2026-11-16; first value matches iFinD qfq within precision'}
    minutes=payload('wind_cli_minutes_retry')['data']['rows']
    morning=[r for r in minutes if r[0][11:16]<'13:00']
    full_vol=sum(float(r[6]) for r in minutes);full_amt=sum(float(r[5]) for r in minutes)
    assert full_vol==3996700 and full_amt==5767305714
    am_vol=sum(float(r[6]) for r in morning); am_amt=sum(float(r[5]) for r in morning)
    out['midday_example']={'symbol':'600519.SH','date':'2026-11-16','morning_bars':len(morning),'last_bar_label':morning[-1][0],
                          'close':float(morning[-1][2]),'volume_shares':am_vol,'amount_yuan':am_amt,
                          'change_vs_prev_close_pct':100*(float(morning[-1][2])/1435.26-1),
                          'daily_volume_check':full_vol,'daily_amount_check':full_amt,'all_bars':len(minutes)}
    hour=payload('ifind_today_intraday')['data']['tables'][1:]
    out['hour_bar_trap']={'last_period_label':hour[-1][2],'queried_before_1130':True,
                         'reported_change_pct':float(hour[-1][4]),'change_from_previous_hour':100*(float(hour[-1][3])/float(hour[-2][3])-1),
                         'not_daily_change':True}
    (ROOT/'audit_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
