"""核心指标计算。只计算已明确定义的量；原博主归属与输入口径见中文手册。"""
from __future__ import annotations
import math
from collections import defaultdict
from statistics import mean, stdev


def finite(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{field} 必须是有限数值')
    return value


def breadth(a, d, u=0, up_amount=None, down_amount=None,
            up_volume=None, down_volume=None):
    for name, val in [('A', a), ('D', d), ('U', u)]:
        finite(val, name)
        if val < 0 or int(val) != val:
            raise ValueError('家数必须是非负整数')
    p = a / (a + d) if a + d else None
    out = dict(A=a, D=d, U=u, count=a+d+u, two_sided=(a > 0 and d > 0),
               advance_share_pct=None if p is None else 100*p)
    for suffix, up, down in [('amount', up_amount, down_amount), ('volume', up_volume, down_volume)]:
        if up is None and down is None:
            continue
        for val in [up, down]:
            finite(val, suffix)
            if val < 0:
                raise ValueError('成交量额不能小于零')
        q = up / (up + down) if up + down else None
        # 退化样本统一不给 TRIN，不把无穷大/0 当作交易信号。
        t = a * down / (d * up) if min(a, d, up, down) > 0 else None
        out.update({f'up_{suffix}': up, f'down_{suffix}': down,
                    f'up_{suffix}_share_pct': None if q is None else 100*q,
                    f'{suffix}_gap_pp': None if p is None or q is None else 100*(q-p),
                    f'trin_{suffix}': t})
    return out


def aggregate_stocks(rows, expected_codes):
    """每条记录为同一时点/同一日；涨跌幅是相对交易所昨收。金额单位元，量单位股。
    expected_codes 是该批全部日期的固定演示股票池。生产版本需逐日传入时点股票池。
    零成交股票排除，平盘仅计 U，不计涨/跌组。这里的排除规则是本实现的约定。
    """
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['date']].append(r)
    answer = []
    for date, items in sorted(grouped.items()):
        codes = [r['code'] for r in items]
        if len(codes) != len(set(codes)):
            raise ValueError(f'{date}: 重复股票记录')
        if set(codes) != set(expected_codes):
            raise ValueError(f'{date}: 股票池不完整或包含非预期股票')
        a = d = u = excluded = 0
        ep = em = vp = vm = 0.0
        has_volume = all('volume_shares' in r and r['volume_shares'] is not None for r in items)
        for r in items:
            ret = finite(r['return_pct'], 'return_pct')
            amt = finite(r['amount_yuan'], 'amount_yuan')
            if amt < 0:
                raise ValueError('成交额为负')
            vol = finite(r['volume_shares'], 'volume_shares') if has_volume else None
            if vol is not None and vol < 0:
                raise ValueError('成交量为负')
            if amt == 0:
                excluded += 1
                continue
            if ret > 0:
                a += 1
                ep += amt
                if has_volume: vp += vol
            elif ret < 0:
                d += 1
                em += amt
                if has_volume: vm += vol
            else:
                u += 1
        out = breadth(a, d, u, ep, em, vp if has_volume else None, vm if has_volume else None)
        out.update(date=date, supplied_count=len(items), excluded_zero_amount=excluded,
                   total_amount_including_flat=sum(r['amount_yuan'] for r in items))
        answer.append(out)
    return answer


def ema(values, n, seed='first'):
    if n < 1 or int(n) != n or seed not in ('first', 'zero'):
        raise ValueError('EMA 参数错误')
    result = []
    prev = None if seed == 'first' else 0.0
    alpha = 2 / (n + 1)
    for x in values:
        finite(x, 'EMA 输入')
        prev = x if prev is None else alpha*x + (1-alpha)*prev
        result.append(prev)
    return result


def mcclellan(rows, normalized=False, warmup_transitions=200, seed='first'):
    """博主版 normalized=False；True 是主流 RANA 替代版，不能与原版混名。
    以交易日记录为一步；不擅自把缺失交易日补为零。日历完整性须在上游核验。
    """
    dates = [r['date'] for r in rows]
    if dates != sorted(set(dates)):
        raise ValueError('日期必须严格升序且不重复')
    values = []
    for r in rows:
        breadth(r['A'], r['D'], r.get('U', 0))
        if normalized and r['A']+r['D'] == 0:
            raise ValueError('归一化分母为零')
        values.append((r['A']-r['D']) * (1000/(r['A']+r['D']) if normalized else 1))
    fast, slow = ema(values, 19, seed), ema(values, 39, seed)
    return [dict(date=date, input_net_advances=x, ema19=f, ema39=s, mcl=f-s,
                 warmed=i >= warmup_transitions, normalized=normalized)
            for i, (date, x, f, s) in enumerate(zip(dates, values, fast, slow))]


def equity_bond_spread(pe_ttm, yield_pct):
    """PE 为倍数；国债收益率以百分数输入（例如 1.6），输出百分点。主流代理公式。"""
    finite(pe_ttm, 'PE_TTM')
    finite(yield_pct, '国债收益率')
    if pe_ttm <= 0:
        return dict(earnings_yield_pct=None, spread_pp=None, ratio=None, valid=False)
    ey = 100 / pe_ttm
    return dict(earnings_yield_pct=ey, spread_pp=ey-yield_pct,
                ratio=ey/yield_pct if yield_pct != 0 else None, valid=True)


def prior_window_stats(values, window, k):
    """研究版：仅用 t-window...t-1，样本标准差(ddof=1)，并列取中点。
    此窗口和排名规则非博主公开算法。历史不足/有缺失时不输出统计量。
    """
    if window < 2 or int(window) != window or k <= 0:
        raise ValueError('统计参数错误')
    result = []
    for i, x in enumerate(values):
        hist = values[max(0, i-window):i]
        if len(hist) != window or x is None or any(v is None for v in hist):
            result.append(None)
            continue
        for v in hist+[x]: finite(v, '统计输入')
        mu, sd = mean(hist), stdev(hist)
        rank = 100 * (sum(v < x for v in hist) + 0.5*sum(v == x for v in hist)) / window
        result.append(dict(mean=mu, std=sd, lower=mu-k*sd, upper=mu+k*sd,
                           z=(x-mu)/sd if sd else None, percentile=rank))
    return result


def vw_macd(closes, volumes, short=12, long=26, mid=9):
    """按视频36：滚动 SUM(C*V)/SUM(V)，非 EMA(C*V)/EMA(V)。"""
    if len(closes) != len(volumes) or not 1 <= short < long or mid < 1:
        raise ValueError('VW-MACD 参数错误')
    for c, v in zip(closes, volumes):
        if finite(c, 'close') <= 0 or finite(v, 'volume') < 0:
            raise ValueError('价格或量无效')
    out, dea = [], None
    for i in range(len(closes)):
        if i+1 < long:
            out.append(None)
            continue
        means = []
        for n in [short, long]:
            c, v = closes[i+1-n:i+1], volumes[i+1-n:i+1]
            means.append(sum(x*y for x, y in zip(c, v))/sum(v) if sum(v) else None)
        if None in means:
            out.append(None)
            dea = None
            continue
        dif = means[0]-means[1]
        dea = dif if dea is None else 2/(mid+1)*dif+(1-2/(mid+1))*dea
        out.append(dict(dif=dif, dea=dea, histogram=2*(dif-dea)))
    return out
