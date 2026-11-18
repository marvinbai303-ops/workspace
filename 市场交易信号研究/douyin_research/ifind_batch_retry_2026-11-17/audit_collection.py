"""核对 iFinD 原始回执与完整下载文件，输出可追溯的日终／午盘样例。"""
import csv
import importlib.util
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'normalized'
OUT.mkdir(exist_ok=True)
D = Decimal
DAY = '20261116'
PREFIXES = '000 001 002 003 300 301 302 600 601 603 605 688 689'.split()
spec = importlib.util.spec_from_file_location('indicators', ROOT.parent/'core_indicators_2026-11-16/indicators.py')
ind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ind)


def data(name):
    raw = json.loads((ROOT/'raw'/f'{name}.json').read_text())
    return json.loads(raw['result']['content'][0]['text'])['data']


def read_csv(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig')))


def source_rows(name):
    path = ROOT/'downloads'/f'{name}_0.csv'
    if path.exists():
        return read_csv(path)
    answer = data(name)['answer'].replace('\\n', '\n')
    lines = [x.strip() for x in answer.splitlines() if x.strip().startswith('|')]
    table = [[x.strip() for x in line.strip('|').split('|')] for line in lines]
    assert table and len(table) >= 2, name
    return [dict(zip(table[0], r)) for r in table[2:] if len(r) == len(table[0])]


def write_csv(name, rows):
    assert rows, name
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def iso(s):
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}'


def normalized_stock(r, source):
    return dict(date=iso(DAY), code=r['股票代码'], name=r['股票简称'],
                close_unadjusted=D(r[f'收盘价:不复权[{DAY}]']),
                return_pct=D(r[f'涨跌幅:不复权[{DAY}]']),
                amount_yuan=D(r[f'成交额[{DAY}]']), volume_shares=D(r[f'成交量[{DAY}]']),
                turnover_pct=D(r[f'换手率[{DAY}]']), source=source)


stocks, partitions = [], []
for prefix in PREFIXES:
    name = f'prefix_{prefix}'
    rows = source_rows(name)
    selected = data(name)['selectedSecuritiesCount']
    assert len(rows) == selected and selected < 1000, (name, len(rows), selected)
    assert all(r['股票代码'].startswith(prefix) for r in rows)
    stocks.extend(normalized_stock(r, name) for r in rows)
    partitions.append(dict(prefix=prefix, selected=selected, received=len(rows)))
stocks.sort(key=lambda r: r['code'])
codes = {r['code'] for r in stocks}
expected = data('universe_eod')['selectedSecuritiesCount']
assert len(stocks) == len(codes) == expected == data('universe_recount')['selectedSecuritiesCount']
assert all(r['code'].endswith(('.SH', '.SZ')) and 'ST' not in r['name'].upper()
           and r['volume_shares'] > 0 and r['amount_yuan'] > 0 for r in stocks)
write_csv('全市场日终_2026-11-16.csv', stocks)
by_code = {r['code']: r for r in stocks}
checks = {}
for name in ['universe_eod', 'universe_recount', 'universe_price_crosscheck', 'universe_volume_crosscheck']:
    rows = source_rows(name)
    for r in rows:
        n = normalized_stock(r, name)
        assert n['code'] in by_code
        assert all(v == by_code[n['code']][k] for k,v in n.items() if k != 'source'), (name, n['code'])
    checks[name] = len(rows)

groups = {s: [r for r in stocks if (r['return_pct'] > 0)-(r['return_pct'] < 0) == s] for s in [1,-1,0]}
sums = {s: {field: sum(r[field] for r in rows) for field in ['amount_yuan','volume_shares']} for s,rows in groups.items()}
metrics = ind.breadth(len(groups[1]), len(groups[-1]), len(groups[0]),
                      float(sums[1]['amount_yuan']), float(sums[-1]['amount_yuan']),
                      float(sums[1]['volume_shares']), float(sums[-1]['volume_shares']))
h5 = {r['code'] for r in stocks if r['turnover_pct'] > 5}
prior = ROOT.parent/'data_source_audit_2026-11-17/raw'
prior_h5 = {r['股票代码'] for r in read_csv(prior/'ifind_turnover_filter.csv')}
prior_star = {r['股票代码'] for r in read_csv(prior/'ifind_partition_fixed.csv')}
assert h5 == prior_h5
assert {c for c in codes if c.startswith(('688','689'))} == prior_star
metrics.update(date=iso(DAY), turnover_gt5_count=len(h5), turnover_gt5_pct=100*len(h5)/len(stocks),
               net_advances=len(groups[1])-len(groups[-1]), flat_amount_yuan=float(sums[0]['amount_yuan']),
               total_amount_yuan=float(sum(v['amount_yuan'] for v in sums.values())))

# 指数非空量额所对应的有效交易日；不把周末前值填充计入 MA。
index_raw = read_csv(ROOT/'downloads/shanghai_daily_long_0.csv')
index_rows = sorted([dict(date=iso(r['日期']), code=r['证券代码'], close_points=D(r['收盘价（不前推）']),
                         volume_shares=D(r['成交量']), amount_yuan=D(r['成交金额']))
                     for r in index_raw if r['成交量'] and D(r['成交量']) > 0], key=lambda r:r['date'])
calendar = {r['date'] for r in index_rows}
assert len(calendar) == len(index_rows)
wind_raw = json.loads((prior/'wind_cli_qfq_history.json').read_text())
wind = json.loads(wind_raw['content'][0]['text'])['data']['rows']
wind_prices = {r[0][:10]: D(r[2]) for r in wind}
assert calendar == set(wind_prices)
vw = ind.vw_macd([float(r['close_points']) for r in index_rows], [float(r['volume_shares']) for r in index_rows])
for r,v in zip(index_rows, vw):
    r.update(vw_dif=v['dif'] if v else None, vw_dea=v['dea'] if v else None,
             vw_histogram=v['histogram'] if v else None)
write_csv('上证指数_日线及VW_MACD.csv', index_rows)
weeks = defaultdict(list)
current_week = date.fromisoformat(iso(DAY)).isocalendar()[:2]
for r in index_rows:
    weeks[date.fromisoformat(r['date']).isocalendar()[:2]].append(r)
weekly = [dict(week=f'{k[0]}-W{k[1]:02}', date=rr[-1]['date'], close_points=rr[-1]['close_points'],
               volume_shares=sum(r['volume_shares'] for r in rr)) for k,rr in sorted(weeks.items()) if k < current_week]
weekly_vw = ind.vw_macd([float(r['close_points']) for r in weekly], [float(r['volume_shares']) for r in weekly])
for r,v in zip(weekly, weekly_vw):
    r.update(vw_dif=v['dif'] if v else None, vw_dea=v['dea'] if v else None,
             vw_histogram=v['histogram'] if v else None)
write_csv('上证指数_已完成周线及VW_MACD.csv', weekly)

qfq_raw = read_csv(ROOT/'downloads/qfq_history_multi_0.csv')
qfq = sorted([dict(date=iso(r['日期']), code=r['证券代码'], name=r['证券简称'], close_qfq=D(r['收盘价']))
              for r in qfq_raw if iso(r['日期']) in calendar], key=lambda r:(r['code'],r['date']))
assert len({(r['code'],r['date']) for r in qfq}) == len(qfq)
sample_ma = []
for c in sorted({r['code'] for r in qfq}):
    rr = [r for r in qfq if r['code'] == c]
    assert {r['date'] for r in rr} == calendar
    assert rr[-1]['close_qfq'] == by_code[c]['close_unadjusted']
    sample_ma.append(dict(code=c, count=len(rr), last_close=rr[-1]['close_qfq'],
                          **{f'MA{n}':sum(r['close_qfq'] for r in rr[-n:])/n for n in [20,60,250]}))
single = {iso(r['日期']):D(r['收盘价']) for r in read_csv(ROOT/'downloads/qfq_history_single_0.csv')}
assert all(r['close_qfq'] == single[r['date']] for r in qfq if r['code']=='600519.SH')
max_wind_diff = max(abs(r['close_qfq']-wind_prices[r['date']]) for r in qfq if r['code']=='600519.SH')
assert max_wind_diff <= D('.0051')
write_csv('三只股票_前复权有效日线.csv', qfq)

etf_raw = read_csv(ROOT/'downloads/etf_daily_long_0.csv')
etf_rows = sorted([dict(date=iso(r['日期']), code=r['证券代码'], name=r['证券简称'],
                       close_unadjusted=D(r['收盘价']), volume_shares=D(r['成交量']), amount_yuan=D(r['成交额']))
                   for r in etf_raw if r['成交量'] and D(r['成交量'])>0], key=lambda r:(r['date'],r['code']))
etf_days = sorted({r['date'] for r in etf_rows})
assert set(etf_days) == {d for d in calendar if d >= '2026-01-01'}
totals = []
for d in etf_days:
    rr = [r for r in etf_rows if r['date']==d]
    assert len(rr)==3 and {r['code'] for r in rr}=={'510300.SH','510050.SH','588000.SH'}
    totals.append(dict(date=d, amount_yuan=sum(r['amount_yuan'] for r in rr)))
for i,r in enumerate(totals):
    r['MA20_amount_yuan'] = sum(x['amount_yuan'] for x in totals[i-19:i+1])/20 if i>=19 else None
write_csv('三只ETF_有效日线.csv', etf_rows)
write_csv('三只ETF_合计成交额及MA20.csv', totals)

references = {}
for name in ['midday_reference_stocks','midday_reference_etfs','midday_reference_index']:
    table = data(name)['tables']
    for r in [dict(zip(table[0],r)) for r in table[1:]]:
        assert r['time'].startswith('2026-11-17')
        tick = D('.001') if name.endswith('etfs') else D('.01')
        references[r['证券代码']] = (D(r['最新价'])-D(r['涨跌'])).quantize(tick)
midday = []
for name in ['midday_stocks','midday_etfs','midday_index_close30']:
    table = data(name)['tables']
    bars = [dict(zip(table[0],r)) for r in table[1:]]
    for c in sorted({r['证券代码'] for r in bars}):
        rr = sorted([r for r in bars if r['证券代码']==c and '2026-11-17 09:30'<=r['time']<='2026-11-17 11:30'],key=lambda r:r['time'])
        assert rr and rr[-1]['time']=='2026-11-17 11:30'
        prev = by_code[c]['close_unadjusted'] if c in by_code else (index_rows[-1]['close_points'] if c=='000001.SH' else next(r['close_unadjusted'] for r in etf_rows if r['code']==c and r['date']==iso(DAY)))
        ref = references[c]
        assert abs(ref-prev) <= D('.00021'), (c, ref, prev)
        midday.append(dict(date='2026-11-17', time='11:30', code=c, name=rr[-1]['证券简称'],
                           close=D(rr[-1]['收盘价']), previous_day_raw_close=prev,
                           reference_previous_close=ref, return_pct=(D(rr[-1]['收盘价'])/ref-1)*100,
                           morning_volume_shares=sum(D(r['成交量']) for r in rr),
                           morning_amount_yuan=sum(D(r['成交额']) for r in rr),
                           completed_bars=len(rr), source=name))
# 参考昨收由供应商同日实时快照的“最新价－涨跌”复原；不使用小时线涨跌幅作日内方向。
minute = data('midday_stock_1min')['tables']
minute = [dict(zip(minute[0],r)) for r in minute[1:] if r[2]<='2026-11-17 11:30']
maotai = next(r for r in midday if r['code']=='600519.SH')
assert sum(D(r['成交量']) for r in minute)==maotai['morning_volume_shares']
assert sum(D(r['成交额']) for r in minute)==maotai['morning_amount_yuan']
assert D(minute[-1]['收盘价'])==maotai['close']
write_csv('午盘样本_2026-11-17_1130.csv', midday)

result = dict(source='iFinD MCP', as_of='2026-11-17', eod_date=iso(DAY), max_query_concurrency=5,
              universe=dict(vendor_selected=expected, unique_downloaded=len(codes), partitions=partitions,
                            direct_overlap_checks=checks, h5_codes_match_previous_complete_file=True,
                            star_codes_match_previous_complete_file=True),
              eod_metrics=metrics,
              daily_index=dict(calendar_rows=len(index_raw), trading_rows=len(index_rows), start=index_rows[0]['date'],
                               end=index_rows[-1]['date'], last_vw_macd=vw[-1], completed_weeks=len(weekly),
                               last_completed_week=weekly[-1]),
              qfq=dict(calendar_rows=len(qfq_raw), trading_rows=len(qfq), per_stock_ma=sample_ma,
                       maotai_max_abs_diff_vs_prior_wind_2decimal=max_wind_diff,
                       adjustment='前复权', requested_adjustment_anchor=iso(DAY),
                       vendor_explicit_anchor_metadata=False),
              etfs=dict(calendar_rows=len(etf_raw), trading_rows=len(etf_rows), unique_trading_days=len(etf_days), last=totals[-1]),
              midday_samples=midday, maotai_minute_and_hourly_match=True,
              not_completed=['全市场 MA20/60/250 比例', '按新股票池重建完整历史 MCL', '全市场午盘快照',
                             '历史逐日 ST / 上市状态的独立明细验证', '自动定时采集部署'],
              rejected_sources={'market_report':'返回阶段表现，未落实所需日终行情日期字段',
                                'universe_remainder':'未执行排除前缀条件，返回原池样例，不用于补齐',
                                'midday_index':'返回空表', 'midday_index_unified':'返回空表'},
              midday_previous_close_method='供应商同日最新价减涨跌，剔除浮点尾差。股票精确到分、ETF精确到厘；指数实时参考昨收仅到小数点后2位，与日线4位存在0.0002点舍入差。')
(ROOT/'audit_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=lambda x:float(x))+'\n')
print(json.dumps({k:result[k] for k in ['eod_metrics','daily_index','qfq','etfs']},ensure_ascii=False,indent=2,default=lambda x:float(x)))
print('PASS: 全池完整性、无重复、字段日期、交叉样本、交易日历、换手筛选、分钟/小时汇总检查。')
