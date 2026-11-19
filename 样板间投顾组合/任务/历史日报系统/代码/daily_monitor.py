#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样板间投顾组合 · 每日净值监控计算与报表引擎
口径（与 Excel 模板20260630 / 同组日报系统一致 · 买入持有权重漂移）：
  组合净值ₜ = [ Σ 初始权重ᵢ × (基金当日复权净值ᵢ / 基金起始日复权净值ᵢ) ] × (1-年化费率)^((当日-起始日)自然日数/365)
  当日预估涨跌幅 = 组合净值ₜ / 组合净值ₜ₋₁ - 1
  累计涨幅       = 组合净值 - 1
持仓明细：今日涨跌=基金复权净值日涨跌；累计涨跌=当日净值/起始日净值-1；贡献=初始配比×涨跌。
报表版式复刻同组"样板间组合日报"：总览页 + 3 张分策略页，红涨蓝跌。

用法：
  python3 daily_monitor.py --config config.json --nav nav_history.csv [--asof YYYYMMDD] [--html out.html]
"""
import argparse, csv, json, datetime as dt
from collections import defaultdict

PORTFOLIOS_ORDER = ['产业趋势','产业趋势基石','产业趋势2号','10-90','10-90基石','30-70']
MONEY_CODES = {'000917'}  # 货币基金：排最末

# 策略分组与主题色（顺序即总览页展示顺序）
STRATEGIES = [
    {'key':'10/90',  'members':['10-90基石','10-90'],            'color':'#7c5cd9','tint':'#ece7f8'},
    {'key':'30/70',  'members':['30-70'],                        'color':'#e8730c','tint':'#fceee1'},
    {'key':'产业趋势','members':['产业趋势基石','产业趋势','产业趋势2号'],'color':'#2f6fd0','tint':'#e7effb'},
]
SLATE='#38414f'; POS='#c0392b'; NEG='#2f6fd0'; GREY='#8a94a3'; HEADBG='#eef1f5'

def _d(s): return dt.datetime.strptime(s,'%Y%m%d').date()

# ---------- 配置 ----------
def load_config(path):
    with open(path, encoding='utf-8') as f:
        cfg = json.load(f)
    funds = {k.split('.')[0]: v for k, v in cfg['funds'].items()}
    ports = {}
    for pname, p in cfg['portfolios'].items():
        start = p.get('start')
        if isinstance(start, str):
            start = dt.datetime.strptime(start, '%Y-%m-%d').date()
        rebs = []
        for rb in p.get('rebalances', []):
            R = rb['date'].replace('-', '')
            shifts = [{'from': s['from'].split('.')[0], 'to': s['to'].split('.')[0],
                       'amount': float(s['amount'])} for s in rb['shifts']]
            rebs.append({'date': R, 'shifts': shifts})
        rebs.sort(key=lambda r: r['date'])
        ports[pname] = {'weights': {k.split('.')[0]: float(v) for k, v in p['weights'].items()},
                        'fee': float(p.get('fee', 0)), 'start': start, 'rebalances': rebs}
    return ports, funds

def load_nav(path):
    nav = defaultdict(dict)
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            nav[row['code']][row['date']] = float(row['nav'])
    return nav

def trading_dates(nav):
    ds = set()
    for d in nav.values(): ds.update(d.keys())
    return sorted(ds)

# ---------- 计算 ----------
def _navv(nav, code, d):
    return nav.get(code, {}).get(d)

def build_segments(cfg, nav):
    """按调仓拆分为多段：[(seg_start, weights, factor)]。
       factor=该段起点处组合累计毛净值（自建仓起、未扣费）；weights=该段起点的市值权重(±调拨)。"""
    sd = cfg['start'].strftime('%Y%m%d')
    segs = [(sd, dict(cfg['weights']), 1.0)]
    for rb in cfg.get('rebalances', []):
        R = rb['date']
        pstart, pw, pfac = segs[-1]
        G = 0.0
        for c, wv in pw.items():
            if not wv: continue
            p0 = _navv(nav, c, pstart); pr = _navv(nav, c, R)
            if p0 and pr: G += pfac * wv * (pr / p0)
        if G <= 0:  # 调仓日净值缺失，保持上一段
            continue
        mv = {}
        for c, wv in pw.items():
            if not wv: continue
            p0 = _navv(nav, c, pstart); pr = _navv(nav, c, R)
            if p0 and pr: mv[c] = pfac * wv * (pr / p0) / G
        for s in rb['shifts']:
            mv[s['from']] = mv.get(s['from'], 0.0) - s['amount']
            mv[s['to']]  = mv.get(s['to'], 0.0) + s['amount']
        segs.append((R, mv, G))
    return segs

def _active_seg(segs, d):
    act = segs[0]
    for s in segs:
        if s[0] < d: act = s   # 调仓生效日当天仍用上一段，次日启用新段
    return act

def _hold_start(segs, code):
    for s in segs:
        if s[1].get(code, 0): return s[0]
    return segs[0][0]

def compute(ports, nav, funds, asof=None):
    dates = trading_dates(nav)
    if asof: dates = [d for d in dates if d <= asof]
    asof = dates[-1]
    out = {}
    for pname, cfg in ports.items():
        start = cfg['start']
        if start is None: continue
        sd = start.strftime('%Y%m%d')
        pdates = [d for d in dates if d >= sd]
        if len(pdates) < 1: continue
        fee = cfg['fee']
        segs = build_segments(cfg, nav)

        def gross_on(d):
            st, w, fac = _active_seg(segs, d)
            g = 0.0
            for code, wi in w.items():
                if not wi: continue
                p0 = _navv(nav, code, st); pt = _navv(nav, code, d)
                if p0 and pt: g += wi * (pt / p0)
            return fac * g
        def net_on(d):
            return gross_on(d) * ((1 - fee) ** ((_d(d) - start).days / 365.0))

        nav_now = net_on(pdates[-1])
        day_ret = (nav_now / net_on(pdates[-2]) - 1.0) if len(pdates) >= 2 else 0.0

        # 持仓明细：用当前生效段的权重；累计以各基金"首次持有段起点"为基准
        d1 = pdates[-1]; d0 = pdates[-2] if len(pdates) >= 2 else pdates[-1]
        cur_w = _active_seg(segs, d1)[1]
        hold = []
        for code, wi in cur_w.items():
            if abs(wi) < 1e-9: continue
            base = _navv(nav, code, _hold_start(segs, code))
            pt = _navv(nav, code, d1); pp = _navv(nav, code, d0)
            day = (pt / pp - 1.0) if (pt and pp) else 0.0
            cum = (pt / base - 1.0) if (pt and base) else 0.0
            hold.append({'code':code,'name':funds.get(code, code),'w':wi,
                         'day':day,'cum':cum,'cd':wi*day,'cc':wi*cum,
                         'money':code in MONEY_CODES})
        hold.sort(key=lambda h:(h['money'], -h['day']))

        out[pname] = {'asof':asof,'start':sd,'nav':nav_now,'day_ret':day_ret,
                      'cum':nav_now-1.0,'fee':fee,'holdings':hold,
                      'rebalanced':len(segs) > 1}
    return out, asof

# ---------- 格式 ----------
def pct(x):
    return ('+' if x >= 0 else '-') + f'{abs(x)*100:.2f}%'
def clr(x):
    return POS if x >= 0 else NEG
def wfmt(w):
    return f'{w*100:g}%'
def disp(name):
    return name.replace('-', '/')

# ---------- 渲染 ----------
def _overview_rows():
    return ('<tr style="background:%s;color:#5a6472;font-size:12px">'
            '<th style="text-align:left;padding:10px 14px;font-weight:600">组合名称</th>'
            '<th style="padding:10px 8px;font-weight:600">上线日期</th>'
            '<th style="padding:10px 8px;font-weight:600">年费率</th>'
            '<th style="padding:10px 8px;font-weight:600">模拟净值</th>'
            '<th style="padding:10px 8px;font-weight:600">今日涨跌幅</th>'
            '<th style="padding:10px 14px;font-weight:600">累计涨跌幅</th></tr>') % HEADBG

def _port_row(pname, r):
    return (f'<tr style="border-bottom:1px solid #eef0f3">'
            f'<td style="text-align:left;padding:12px 14px;font-weight:700;color:#2b3240">{disp(pname)}</td>'
            f'<td style="padding:12px 8px;text-align:center;color:{GREY}">{r["start"][:4]}-{r["start"][4:6]}-{r["start"][6:]}</td>'
            f'<td style="padding:12px 8px;text-align:center;color:{GREY}">{wfmt(r["fee"])}</td>'
            f'<td style="padding:12px 8px;text-align:center;font-weight:600;color:#2b3240">{r["nav"]:.4f}</td>'
            f'<td style="padding:12px 8px;text-align:center;font-weight:700;color:{clr(r["day_ret"])}">{pct(r["day_ret"])}</td>'
            f'<td style="padding:12px 14px;text-align:center;font-weight:700;color:{clr(r["cum"])}">{pct(r["cum"])}</td></tr>')

def _disclaimer():
    return ('<div style="padding:10px 16px;color:#9aa3b0;font-size:12px;background:#fafbfc">'
            '数据基于底层基金涨跌幅加权+费率估算，AI推送，仅供预览使用，最终务必以系统数据为准</div>')

def _headerbar(title, asof, bg, subcolor):
    return (f'<table role="presentation" style="width:100%;background:{bg};border-collapse:collapse">'
            f'<tr><td style="padding:16px 18px;color:#fff;font-size:20px;font-weight:800;letter-spacing:1px">{title}</td>'
            f'<td style="padding:16px 18px;text-align:right;color:{subcolor};font-size:13px;white-space:nowrap">'
            f'更新日期：{asof[:4]}-{asof[4:6]}-{asof[6:]}</td></tr></table>')

def card_overview(res, asof):
    body = _overview_rows()
    for st in STRATEGIES:
        members = [m for m in st['members'] if m in res]
        if not members: continue
        body += (f'<tr><td colspan="6" style="padding:0">'
                 f'<div style="border-left:4px solid {st["color"]};background:{st["tint"]};'
                 f'padding:8px 12px;font-weight:700;color:{st["color"]};font-size:13px">{st["key"]} 策略</div>'
                 f'</td></tr>')
        for m in members:
            body += _port_row(m, res[m])
    return (f'<div style="border:1px solid #e6e9ee;border-radius:10px;overflow:hidden;margin-bottom:22px">'
            f'{_headerbar("样板间组合业绩概览", asof, SLATE, "#c3ccd8")}'
            f'{_disclaimer()}'
            f'<table style="border-collapse:collapse;width:100%;font-size:14px;'
            f'font-family:\'PingFang SC\',\'Microsoft YaHei\',sans-serif">{body}</table></div>')

def _sec_title(text, st):
    return (f'<div style="margin:16px 16px 8px;border-left:4px solid {st["color"]};'
            f'background:{st["tint"]};padding:8px 12px;font-weight:800;color:{st["color"]};font-size:15px">{text}</div>')

def _holdings_table(pname, r, st):
    head = (f'<tr style="background:{HEADBG};color:#5a6472;font-size:12px">'
            f'<th style="text-align:left;padding:8px 14px;font-weight:600">基金名称</th>'
            f'<th style="padding:8px;font-weight:600">初始配比</th>'
            f'<th style="padding:8px;font-weight:600">今日涨跌</th>'
            f'<th style="padding:8px;font-weight:600">今日贡献</th>'
            f'<th style="padding:8px;font-weight:600">累计涨跌</th>'
            f'<th style="padding:8px 14px;font-weight:600">累计贡献</th></tr>')
    arrow = '▲' if r['day_ret'] >= 0 else '▼'
    sub = (f'<tr><td colspan="6" style="padding:0">'
           f'<div style="border-left:4px solid {st["color"]};background:{st["tint"]};padding:7px 12px;font-size:13px">'
           f'<b style="color:{st["color"]}">{disp(pname)}</b> '
           f'<span style="color:{clr(r["day_ret"])};font-weight:700">{arrow} {pct(r["day_ret"])}</span>'
           f'<span style="color:#9aa3b0"> ／ 累计 </span><span style="color:{clr(r["cum"])};font-weight:700">{pct(r["cum"])}</span>'
           f'</div></td></tr>')
    rows = ''
    for h in r['holdings']:
        rows += (f'<tr style="border-bottom:1px solid #f0f2f5">'
                 f'<td style="text-align:left;padding:9px 14px;color:#2b3240">{h["name"]}</td>'
                 f'<td style="padding:9px 8px;text-align:center;color:{GREY}">{wfmt(h["w"])}</td>'
                 f'<td style="padding:9px 8px;text-align:center;font-weight:600;color:{clr(h["day"])}">{pct(h["day"])}</td>'
                 f'<td style="padding:9px 8px;text-align:center;color:{clr(h["cd"])}">{pct(h["cd"])}</td>'
                 f'<td style="padding:9px 8px;text-align:center;font-weight:600;color:{clr(h["cum"])}">{pct(h["cum"])}</td>'
                 f'<td style="padding:9px 14px;text-align:center;color:{clr(h["cc"])}">{pct(h["cc"])}</td></tr>')
    return (f'<table style="border-collapse:collapse;width:100%;font-size:13.5px;margin:0 0 6px;'
            f'font-family:\'PingFang SC\',\'Microsoft YaHei\',sans-serif">{sub}{head}{rows}</table>')

def card_strategy(st, res, asof):
    members = [m for m in st['members'] if m in res]
    if not members: return ''
    ov = _overview_rows()
    for m in members: ov += _port_row(m, res[m])
    holds = ''.join(_holdings_table(m, res[m], st) for m in members)
    return (f'<div style="border:1px solid #e6e9ee;border-radius:10px;overflow:hidden;margin-bottom:22px">'
            f'{_headerbar(st["key"] + " 策略", asof, st["color"], "#eef2f7")}'
            f'{_disclaimer()}'
            f'{_sec_title("一、组合总览", st)}'
            f'<table style="border-collapse:collapse;width:100%;font-size:14px;'
            f'font-family:\'PingFang SC\',\'Microsoft YaHei\',sans-serif;margin-bottom:6px">{ov}</table>'
            f'{_sec_title("二、持仓基金表现", st)}'
            f'<div style="padding:0 4px 10px">{holds}</div></div>')

def render_report(res, asof):
    cards = card_overview(res, asof)
    for st in STRATEGIES:
        cards += card_strategy(st, res, asof)
    return (f'<div style="background:#f0f2f5;padding:16px;'
            f'font-family:\'PingFang SC\',\'Microsoft YaHei\',sans-serif;max-width:760px">{cards}</div>')

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--nav', required=True)
    ap.add_argument('--asof', default=None)
    ap.add_argument('--html', default=None)
    a = ap.parse_args()
    ports, funds = load_config(a.config)
    nav = load_nav(a.nav)
    res, asof = compute(ports, nav, funds, a.asof)
    print(f'=== 数据日期 {asof} ===')
    print(f'{"组合":<12}{"模拟净值":>10}{"今日预估":>10}{"累计涨幅":>10}')
    for p in PORTFOLIOS_ORDER:
        if p not in res: continue
        r = res[p]
        print(f'{p:<12}{r["nav"]:>10.4f}{pct(r["day_ret"]):>11}{pct(r["cum"]):>11}')
    if a.html:
        with open(a.html, 'w', encoding='utf-8') as f:
            f.write(render_report(res, asof))
        print('HTML ->', a.html)
    return res

if __name__ == '__main__':
    main()
