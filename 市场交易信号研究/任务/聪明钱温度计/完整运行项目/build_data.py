"""Recalculate the dashboard from audited source files; never fetch or fabricate values."""
import csv, json, hashlib, importlib.util
from decimal import Decimal as D
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
RESEARCH = WORK / 'douyin_research'
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)

def read_csv(p):
    return list(csv.DictReader(p.open(encoding='utf-8-sig')))

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def source(p, label):
    return dict(file=str(p.relative_to(WORK)), label=label, sha256=digest(p), provider='iFinD MCP')

def vw_series(rows):
    """Video 36: rolling SUM(C*V)/SUM(V), with an independent Decimal calculation."""
    result=[]; dea=None
    for i,r in enumerate(rows):
        dif=hist=None
        if i>=25:
            def weighted(n):
                window=rows[i+1-n:i+1]
                vol=sum(D(str(x['volume'])) for x in window)
                assert vol>0
                return sum(D(str(x['close']))*D(str(x['volume'])) for x in window)/vol
            dif=weighted(12)-weighted(26)
            dea=dif if dea is None else D('.2')*dif+D('.8')*dea
            hist=2*(dif-dea)
        result.append({**r,'dif':float(dif) if dif is not None else None,'dea':float(dea) if dea is not None else None,'histogram':float(hist) if hist is not None else None})
    return result

def build_vw(old,sources):
    daily_path=old/'normalized/上证指数_日线及VW_MACD.csv'
    week_path=old/'normalized/上证指数_已完成周线及VW_MACD.csv'
    raw=read_csv(daily_path); raw_week=read_csv(week_path)
    daily=[dict(date=r['date'],close=float(r['close_points']),volume=float(r['volume_shares'])) for r in raw]
    assert len({r['date'] for r in daily})==len(daily) and daily==sorted(daily,key=lambda r:r['date'])
    bydate={r['date']:r for r in daily}
    updates=DATA/'vw_daily_updates.json'
    if updates.exists():
        for r in json.loads(updates.read_text()):
            assert r['validated'] and r['session']=='eod' and r['code']=='000001.SH'
            p=WORK/r['source'];assert digest(p)==r['sha256']
            v=dict(date=r['date'],close=float(r['close']),volume=float(r['volume']))
            assert v['close']>0 and v['volume']>0
            if v['date'] in bydate: assert bydate[v['date']]==v,'VW index history revision requires audit'
            bydate[v['date']]=v;sources.append(source(p,'VW-MACD 新增指数日终输入'))
    daily=sorted(bydate.values(),key=lambda r:r['date'])
    completed={r['week'] for r in raw_week}; groups={}
    def week(d):
        x=date.fromisoformat(d).isocalendar();return f'{x.year}-W{x.week:02}'
    for r in daily:groups.setdefault(week(r['date']),[]).append(r)
    lastweek=week(daily[-1]['date'])
    # A current Friday is complete. Holiday-shortened current weeks wait for calendar proof / next week.
    completed.update(k for k,rs in groups.items() if k<lastweek or date.fromisoformat(rs[-1]['date']).weekday()==4)
    weekly=[dict(date=rr[-1]['date'],week=k,close=rr[-1]['close'],volume=sum(r['volume'] for r in rr)) for k,rr in sorted(groups.items()) if k in completed]
    for r in raw_week:
        got=next(v for v in weekly if v['week']==r['week'])
        assert got['date']==r['date'] and abs(got['close']-float(r['close_points']))<1e-8 and abs(got['volume']-float(r['volume_shares']))<.1
    ds,ws=vw_series(daily),vw_series(weekly)
    for refs,series in [(raw,ds),(raw_week,ws)]:
        index={r['date']:r for r in series}
        for ref in refs:
            for k in ('dif','dea','histogram'):
                v=ref['vw_'+k]
                assert (not v and index[ref['date']][k] is None) or (v and abs(float(v)-index[ref['date']][k])<1e-8),('VW independent check',ref['date'],k)
    sources.extend([source(daily_path,'VW-MACD 上证指数已验收日线'),source(week_path,'VW-MACD 已完成周线与原结果对照')])
    f=RESEARCH/'formula_audit/已公开公式_通达信.txt'
    sources.append({**source(f,'视频36 01:40 已公开 VW-MACD 源码'),'provider':'博主视频画面核查'})
    return dict(code='000001.SH',name='上证指数',parameters=[12,26,9],daily=ds,weekly=ws,
                formula='DIF=SUM(C*V,12)/SUM(V,12)-SUM(C*V,26)/SUM(V,26); DEA=EMA(DIF,9); MACD=2*(DIF-DEA)',
                seed='前25根留空；DEA从首个有效DIF初始化',noonPolicy='午盘引用最近有效日终，不将半日K插入日终历史',
                weeklyPolicy='周末收盘价×全周成交量参与加权；只纳入已完成周，不把每日C×V之和当周线C×V')

def aggregate(rows, date, session, expected_count):
    codes=[r['code'] for r in rows]
    assert len(codes)==len(set(codes))==expected_count, 'Missing or duplicate securities'
    assert all(r['date']==date and r['code'].endswith(('.SH','.SZ')) and 'ST' not in r['name'].upper() for r in rows)
    assert all(D(r['amount_yuan'])>0 and D(r['volume_shares'])>0 for r in rows)
    if session=='noon':
        assert all(r['time']=='11:30' for r in rows)
    groups={s:[r for r in rows if (D(r['return_pct'])>0)-(D(r['return_pct'])<0)==s] for s in (-1,0,1)}
    a,d,u=[len(groups[s]) for s in (1,-1,0)]
    totals={s:{f:sum(D(r[f]) for r in groups[s]) for f in ('amount_yuan','volume_shares')} for s in (-1,0,1)}
    p=D(a)/(a+d) if a+d else None
    q=totals[1]['amount_yuan']/(totals[1]['amount_yuan']+totals[-1]['amount_yuan']) if a+d else None
    two_sided=bool(a and d)
    out=dict(date=date, session=session, time='11:30' if session=='noon' else '15:00', A=a,D=d,U=u,count=len(rows),
             p=float(100*p) if p is not None else None,q=float(100*q) if q is not None else None,
             gap=float(100*(q-p)) if two_sided else None,
             trin=float(D(a)*totals[-1]['amount_yuan']/(D(d)*totals[1]['amount_yuan'])) if two_sided else None,
             trinVolume=float(D(a)*totals[-1]['volume_shares']/(D(d)*totals[1]['volume_shares'])) if two_sided else None,
             totalAmount=float(sum(t['amount_yuan'] for t in totals.values())),upAmount=float(totals[1]['amount_yuan']),downAmount=float(totals[-1]['amount_yuan']),flatAmount=float(totals[0]['amount_yuan']),
             upVolume=float(totals[1]['volume_shares']),downVolume=float(totals[-1]['volume_shares']),
             scope='沪深 A 股 · 剔 ST/*ST、北交所、无成交股票', twoSided=two_sided)
    if two_sided:
        assert abs(float(p/(1-p)/(q/(1-q)))-out['trin'])<1e-10
    return out

def build():
    old=RESEARCH/'ifind_batch_retry_2026-11-17'
    noon=RESEARCH/'full_validation_2026-11-17'
    mcldir=RESEARCH/'mcl_ifind_include_st_2026-11-17'
    defs=[('2026-11-16','eod',old/'normalized/全市场日终_2026-11-16.csv',old/'audit_results.json','eod_metrics'),
          ('2026-11-17','noon',noon/'normalized/全市场午盘_2026-11-17_1130.csv',noon/'noon_audit_results.json','metrics')]
    snapshots=[]; sources=[]
    for date,session,path,auditpath,key in defs:
        audit=json.loads(auditpath.read_text()); metrics=audit[key]
        if session=='noon': assert audit['missing_unresolved']==[]
        snap=aggregate(read_csv(path),date,session,metrics['count'])
        for field,ref in [('p','advance_share_pct'),('q','up_amount_share_pct'),('gap','amount_gap_pp'),('trin','trin_amount'),('trinVolume','trin_volume')]:
            assert abs(snap[field]-metrics[ref])<1e-9,field
        snap['sources']=[source(path,'已验收逐股明细'),source(auditpath,'独立校验记录')]
        snapshots.append(snap);sources.extend(snap['sources'])
    # Future runs add validated manifests, keeping source CSV and raw receipts in this workspace.
    for manifest in sorted((DATA/'imports').glob('*.json')) if (DATA/'imports').exists() else []:
        m=json.loads(manifest.read_text())
        assert m['validation']['accepted'] is True and m['validation']['missing_codes']==[]
        assert m['provider']=='iFinD MCP' and m['scope_id']=='SHSZ_NONST_ACTIVE_V1', 'Provider/scope changes require a separate series'
        path=WORK/m['csv']; assert digest(path)==m['sha256']
        rows=read_csv(path)
        assert set(r['code'] for r in rows)==set(m['expected_codes']), 'Universe does not match'
        snap=aggregate(rows,m['date'],m['session'],len(m['expected_codes']))
        snap['sources']=[source(path,'新增已验收逐股明细'),source(manifest,'新增校验清单')]
        duplicate=[s for s in snapshots if (s['date'],s['session'])==(snap['date'],snap['session'])]
        if duplicate:
            assert all(snap[k]==duplicate[0][k] for k in ('A','D','U','upAmount','downAmount','totalAmount')), 'Conflicting historical revision'
        else: snapshots.append(snap)
        sources.extend(snap['sources'])
    snapshots.sort(key=lambda s:(s['date'],s['time']))
    spec=importlib.util.spec_from_file_location('mcl_update',mcldir/'update_mcl.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mcl=mod.calculate(mod.read_rows(mcldir/'ifind_breadth_history.csv'))
    cached=read_csv(mcldir/'mcl_daily.csv')
    assert len(cached)==len(mcl)
    assert all(abs(float(c['mcl'])-r['mcl'])<1e-8 and c['date']==r['date'] for c,r in zip(cached,mcl))
    validation=json.loads((mcldir/'validation.json').read_text())
    assert validation['checks']['sh_plus_sz_equals_total_every_day']
    mclSeries=[{k:r[k] for k in ('date','A','D','U','net_advances','mcl','warmed')} for r in mcl]
    sources.extend([source(mcldir/'ifind_breadth_history.csv','含 ST 沪深宽度历史'),source(mcldir/'validation.json','MCL 验收与局限')])
    etfpath=old/'normalized/三只ETF_有效日线.csv';etfrows=read_csv(etfpath)
    etfs=[]
    for date in sorted(set(r['date'] for r in etfrows)):
        rr=[r for r in etfrows if r['date']==date]
        assert {r['code'] for r in rr}=={'510050.SH','510300.SH','588000.SH'} and len(rr)==3
        etfs.append(dict(date=date,session='eod',time='15:00',amount=float(sum(D(r['amount_yuan']) for r in rr)),parts=[dict(code=r['code'],amount=float(r['amount_yuan'])) for r in rr]))
    raw=json.loads((old/'audit_results.json').read_text())
    rr=[r for r in raw['midday_samples'] if r['code'] in {'510050.SH','510300.SH','588000.SH'}]
    assert len(rr)==3
    etfs.append(dict(date='2026-11-17',session='noon',time='11:30',amount=sum(r['morning_amount_yuan'] for r in rr),parts=[dict(code=r['code'],amount=r['morning_amount_yuan']) for r in rr]))
    # Independently audited ETF updates are optional and never guessed from stock turnover.
    if (DATA/'etf_updates.json').exists():
        for r in json.loads((DATA/'etf_updates.json').read_text()):
            assert r['validated'] and len(r['parts'])==3 and {p['code'] for p in r['parts']}=={'510050.SH','510300.SH','588000.SH'}
            assert abs(sum(p['amount'] for p in r['parts'])-r['amount'])<.01
            assert r.get('source') and r.get('sha256')
            assert digest(WORK/r['source'])==r['sha256'], 'ETF source fingerprint mismatch'
            if not any((e['date'],e['session'])==(r['date'],r['session']) for e in etfs):etfs.append(r)
    etfs.sort(key=lambda r:(r['date'],r['time']))
    sources.append(source(etfpath,'三只 ETF 209 日成交额底库'))
    vw=build_vw(old,sources)
    out=dict(schemaVersion=1,generatedAt=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
             latestDate=snapshots[-1]['date'],provider='iFinD MCP',snapshots=snapshots,mcl=mclSeries,etfs=etfs,vwMacd=vw,
             sources=list({s['file']:s for s in sources}.values()),mclNoonAvailable=False,
             formulaEvidence={'p':90,'trin':95,'gap':90,'mcl':100,'trinVolume':100,'etf':100,'vwMacd':100},
             schedule={'timezone':'Asia/Shanghai','times':['12:00','17:00'],'status':'待创建'},
             limitations=['MCL 为含 ST 独立序列，其他市场截面剔 ST，不拼接。','MCL 午盘缺少同口径含 ST 数据，沿用并明确标记最近日终。','成交分布仅有已验收快照；午盘和收盘分轨积累，不伪造长历史。','公式证据分不是交易胜率；尚未完成预测有效性回测。'])
    status=DATA/'schedule.json'
    if status.exists():out['schedule'].update(json.loads(status.read_text()))
    (DATA/'dashboard.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out

if __name__=='__main__':
    d=build();print(json.dumps({'snapshots':len(d['snapshots']),'mcl_days':len(d['mcl']),'etf_observations':len(d['etfs']),'latest':d['snapshots'][-1]},ensure_ascii=False,indent=2))
