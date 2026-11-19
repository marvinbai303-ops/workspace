#!/usr/bin/env python3
# coding: utf-8
"""
玄驹组合·卫星轮动引擎 V1.1 —— 日常监控脚本
用途: 读取用户提供的 iFind 指数数据 + 系统导出的最新持仓权重, 输出当日监控面板:
     组合快照 / 因子打分 / streak状态 / 调仓信号(醒目标注) / 换手预算。
原则: 只依据用户提供的数据文件, 不联网取数, 不用任何外部先验修正数据;
     数据异常只报告、不推断。本脚本只产生"信号建议", 不执行任何交易。
运行: python daily_check.py --data "indexdata(场外-ifind).xlsx" --weights "最新持仓比例.xlsx" [--config config.json] [--out reports]
退出码: 0=正常无信号  2=触发调仓信号  1=数据校验失败
"""
import argparse, json, re, sys, os
from datetime import datetime
import numpy as np
import pandas as pd

# ---------------- 数据读取 ----------------
def load_matrix_sheet(xlsx, sheet):
    """首行=指数代码, 次行=指数名称, 首列=日期; 0视为缺失"""
    raw = pd.read_excel(xlsx, sheet_name=sheet, header=None)
    codes = raw.iloc[0, 1:].tolist(); names = raw.iloc[1, 1:].tolist()
    keep = [i for i, (c, nm) in enumerate(zip(codes, names))
            if isinstance(nm, str) and nm.strip() and not str(nm).startswith('ps')]
    cols = [str(names[i]).strip() for i in keep]
    d = raw.iloc[2:, [0] + [i + 1 for i in keep]].copy()
    d.columns = ['Date'] + cols
    d['Date'] = pd.to_datetime(d['Date'], errors='coerce')
    d = d.dropna(subset=['Date']).set_index('Date').sort_index()
    d = d[~d.index.duplicated(keep='first')]
    for c in d.columns:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d.replace(0.0, np.nan)

def load_fund_map(xlsx):
    """指数&基金匹配 sheet -> {基金6位代码: 指数名称}"""
    raw = pd.read_excel(xlsx, sheet_name='指数&基金匹配', header=None)
    hdr = None
    for r in range(min(10, len(raw))):
        if (raw.iloc[r] == '指数代码').any():
            hdr = r; break
    if hdr is None:
        return {}
    df = raw.iloc[hdr + 1:].copy()
    cols = {v: c for c, v in raw.iloc[hdr].items() if isinstance(v, str)}
    out = {}
    for _, row in df.iterrows():
        fc = str(row[cols.get('基金代码', -1)]) if '基金代码' in cols else ''
        ix = str(row[cols.get('指数名称', -1)]) if '指数名称' in cols else ''
        m = re.search(r'(\d{6})', fc)
        if m and ix and ix != 'nan':
            out[m.group(1)] = ix.strip()
    return out

def load_weights(xlsx):
    """系统导出持仓: 首行=基金全名(可含代码), 首列=日期; 返回(权重历史df, 最新日期)"""
    raw = pd.read_excel(xlsx, sheet_name=0, header=None)
    names = [str(x).strip() for x in raw.iloc[0, 1:].tolist()]
    d = raw.iloc[1:, :len(names) + 1].copy()
    d.columns = ['Date'] + names
    d['Date'] = pd.to_datetime(d['Date'], errors='coerce')
    d = d.dropna(subset=['Date']).set_index('Date').sort_index()
    for c in d.columns:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d, d.index.max()

# ---------------- 因子 ----------------
def build_factors(px):
    ret = px.pct_change()
    ma60 = px.rolling(60).mean()
    hist_ok = px.notna().cumsum() >= 120
    avail = px.notna() & ma60.notna() & hist_ok
    qual = avail & (px > ma60)
    def zrow(df):
        m = df.where(avail)
        mu = m.mean(axis=1); sd = m.std(axis=1).replace(0, np.nan)
        return m.sub(mu, axis=0).div(sd, axis=0)
    comp = {}
    for w in (20, 60, 120):
        r = px / px.shift(w) - 1.0
        s = ret.rolling(w, min_periods=w).std()
        comp[w] = zrow(r.divide(s.replace(0, np.nan)))
    score = (comp[20] + comp[60] + comp[120]) / 3.0
    masked = score.where(qual)
    ranks = masked.rank(axis=1, ascending=False, method='first')
    return score, comp, qual, ranks, ma60

def calc_streaks(ranks, qual, holdings, K, since):
    """按V1.1规则倒推streak; since=上次调仓生效日(之前的历史不计入)"""
    idx = ranks.index[ranks.index >= since]
    out_s, in_s = {}, {}
    for a in ranks.columns:
        held = a in holdings
        st = 0
        for d in reversed(idx):
            r = ranks.loc[d, a]
            if held:
                bad = pd.isna(r) or r > K + 1
                if bad: st += 1
                else: break
            else:
                good = pd.notna(r) and r <= K
                if good: st += 1
                else: break
        (out_s if held else in_s)[a] = st
    return out_s, in_s

# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='indexdata(场外-ifind).xlsx')
    ap.add_argument('--weights', required=True)
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--out', default='reports')
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding='utf-8'))
    P = cfg['params']
    K, PERSIST, MINHOLD = P['K'], P['persist'], P['min_hold_days']
    warn, err = [], []

    # 1) 数据
    px = load_matrix_sheet(args.data, '卫星指数行情')
    try:
        amt = load_matrix_sheet(args.data, '卫星指数成交额')
    except Exception:
        amt = None; warn.append('未读到成交额sheet, 量能参考列缺省')
    fund_map = load_fund_map(args.data)
    fund_map.update(cfg.get('fund_index_overrides', {}))
    wdf, wdate = load_weights(args.weights)
    pdate = px.index.max()
    eval_date = min(pdate, wdate)   # 因子按两者中较早者的可得数据评估

    # 2) 持仓映射
    latest = wdf.loc[wdate]
    core_w, cash_w = 0.0, 0.0
    sat_w = {}          # 指数名 -> 当前权重
    buy_date = {}       # 指数名 -> 首次出现权重的日期(保守的最短持有起点)
    unmapped = []
    for fund, w in latest.items():
        if pd.isna(w) or w < 1e-6: continue
        name = str(fund)
        if any(k in name for k in cfg.get('cash_keywords', ['货币'])):
            cash_w += float(w); continue
        if any(k in name for k in cfg.get('core_keywords', ['科技100'])):
            core_w += float(w); continue
        m = re.search(r'(\d{6})', name)
        ix = fund_map.get(m.group(1)) if m else None
        if ix is None:
            ix = next((i for i in px.columns if i in name), None)
        if ix is None or ix not in px.columns:
            unmapped.append(name); continue
        sat_w[ix] = sat_w.get(ix, 0.0) + float(w)
        ser = wdf[fund]
        nz = ser[ser > 0.005]
        buy_date[ix] = nz.index.min() if len(nz) else wdate
    holdings = list(sat_w)

    # 3) 校验
    tot = float(latest.fillna(0).sum())
    if abs(tot - 1.0) > 0.01: err.append(f'权重合计={tot:.4f}, 偏离1超过1%')
    if unmapped: err.append('无法映射到指数池的持仓: ' + '; '.join(unmapped))
    if (wdate - pdate).days > 5: warn.append(f'指数数据({pdate.date()})明显滞后于权重数据({wdate.date()}), 因子可能过期')
    if (pdate - wdate).days > 5: warn.append(f'权重数据({wdate.date()})明显滞后于指数数据({pdate.date()}), 请重新导出持仓')
    if err:
        print('❌ 数据校验失败:\n' + '\n'.join(' - ' + e for e in err)); sys.exit(1)

    # 4) 因子与streak
    score, comp, qual, ranks, ma60 = build_factors(px)
    d = eval_date if eval_date in px.index else px.index[px.index <= eval_date].max()
    since = pd.Timestamp(cfg['state']['last_trade_date'])
    out_s, in_s = calc_streaks(ranks.loc[:d], qual.loc[:d], holdings, K, since)

    # 5) 信号判定
    def mh_ok(a):
        return a in buy_date and (wdate - buy_date[a]).days >= MINHOLD
    used = float(cfg['ledger']['used_turnover'])
    elapsed = d.dayofyear / 365.0
    p_eff = PERSIST
    slow = (elapsed > 0.1) and (used / P['cap'] / max(elapsed, 1e-9) > 1.5)
    if slow: p_eff = max(PERSIST, 15)

    exits = [a for a in holdings if out_s.get(a, 0) >= p_eff and mh_ok(a)]
    blocked = [a for a in holdings if out_s.get(a, 0) >= p_eff and not mh_ok(a)]
    slots = K - (len(holdings) - len(exits))
    cands = [a for a in px.columns if a not in holdings and in_s.get(a, 0) >= p_eff
             and pd.notna(ranks.loc[d, a]) and ranks.loc[d, a] <= K]
    cands = sorted(cands, key=lambda a: ranks.loc[d, a])[:max(0, slots)]
    inv = 1.0 - min(cash_w, 0.015)
    core_ratio = core_w / inv if inv > 0 else 0
    core_breach = core_ratio < P['core_band'][0] or core_ratio > P['core_band'][1]
    sat_bucket = 1.0 - core_w - cash_w
    triggered = bool(exits or cands or core_breach)

    # 6) 报告
    L = []
    L.append(f"# 玄驹组合·卫星轮动V1.1 监控报告  {d.date()}")
    L.append(f"\n指数数据截止 **{pdate.date()}** | 持仓权重截止 **{wdate.date()}** | 评估日 **{d.date()}** | 上次调仓生效 {since.date()}")
    if warn: L.append('\n**⚠️ 警告:** ' + ' / '.join(warn))

    L.append('\n## 一、组合快照')
    L.append(f'\n| 资产 | 权重 | 备注 |\n|---|---|---|')
    L.append(f'| 现金(货基) | {cash_w:.2%} | 目标1% |')
    L.append(f'| 核心:科技100 | {core_w:.2%} | 占可投 {core_ratio:.1%}, band {P["core_band"][0]:.0%}-{P["core_band"][1]:.0%} {"❌出带" if core_breach else "✓带内"} |')
    for a in sorted(sat_w, key=sat_w.get, reverse=True):
        dd_ = (wdate - buy_date[a]).days if a in buy_date else -1
        L.append(f'| 卫星:{a} | {sat_w[a]:.2%} | 入场约16.5%, 已持有{dd_}天, 卫星内占比{sat_w[a]/max(sat_bucket,1e-9):.0%} |')
    satcash = sat_bucket - sum(sat_w.values())
    if satcash > 0.005: L.append(f'| 卫星内现金 | {satcash:.2%} | 空位资金, 留货基 |')

    L.append('\n## 二、因子打分(评估日全池)')
    hdr = '| 标的 | 综合分 | z(r20/σ) | z(r60/σ) | z(r120/σ) | 合格排名 | 过资格线 | 持有 |'
    if amt is not None: hdr = hdr + ' 量能(20/120日均额) |'
    L.append('\n' + hdr)
    L.append('|' + '---|' * (hdr.count('|') - 1))
    order = sorted(px.columns, key=lambda a: (score.loc[d, a] if pd.notna(score.loc[d, a]) else -99), reverse=True)
    for a in order:
        s_ = f"{score.loc[d,a]:.2f}" if pd.notna(score.loc[d, a]) else '-'
        zz = [f"{comp[w].loc[d,a]:.2f}" if pd.notna(comp[w].loc[d, a]) else '-' for w in (20, 60, 120)]
        r_ = f"{int(ranks.loc[d,a])}" if pd.notna(ranks.loc[d, a]) else '-'
        q_ = '是' if bool(qual.loc[d, a]) else '**否**'
        h_ = '★' if a in holdings else ''
        row = f'| {a} | {s_} | {zz[0]} | {zz[1]} | {zz[2]} | {r_} | {q_} | {h_} |'
        if amt is not None:
            a20 = amt[a].rolling(20, min_periods=10).mean()
            a120 = amt[a].rolling(120, min_periods=60).mean()
            v = a20.loc[:d].iloc[-1] / a120.loc[:d].iloc[-1] if pd.notna(a120.loc[:d].iloc[-1]) else np.nan
            row = row + (f' {v:.2f} |' if pd.notna(v) else ' - |')
        L.append(row)
    L.append('\n*资格线=收盘价>MA60且历史≥120日; 排名只在过线者中排; 量能列仅观察不入分*')

    L.append('\n## 三、streak状态(换入/换出确认进度)')
    L.append(f'\n| 标的 | 状态 | 进度(需{p_eff}日) |\n|---|---|---|')
    for a in holdings:
        L.append(f'| {a} | 持有, 连续跌出前{K+1}名 | {out_s.get(a,0)} 日 {"🔶接近触发" if out_s.get(a,0)>=p_eff*0.7 else ""} |')
    for a, v in sorted(in_s.items(), key=lambda kv: -kv[1]):
        if v > 0: L.append(f'| {a} | 候补, 连续进入前{K}名 | {v} 日 {"✅已过线(等空位)" if v>=p_eff else ""} |')

    L.append('\n## 四、信号判定')
    if triggered:
        L.append('\n> ## 🚨🚨 触发调仓信号 —— 需人工确认执行 🚨🚨')
        if exits:
            for a in exits:
                L.append(f'\n**换出 {a}**: 全额赎回(当前约占组合 {sat_w[a]:.1%})。原因: 连续{out_s[a]}日跌出前{K+1}名(≥{p_eff}日确认)。')
        if cands:
            freed = sum(sat_w[a] for a in exits) + max(satcash, 0)
            per = min(freed / len(cands) if cands else 0, sat_bucket / K)
            for a in cands:
                L.append(f'\n**换入 {a}**: 目标买入约占组合 {per:.1%}(=可用资金等分, 上限卫星桶/{K})。原因: 连续{in_s[a]}日进入前{K}名(≥{p_eff}日确认)且过资格线。')
        if core_breach:
            L.append(f'\n**核心再平衡**: 核心占可投 {core_ratio:.1%} 已出 {P["core_band"][0]:.0%}-{P["core_band"][1]:.0%} 带, 调回50%。')
        L.append('\n**执行链**: T+1提交赎回 → 资金到账日(约T+2/T+3)重跑本脚本**复核**: 信号仍成立→申购新标的; 信号消失→放弃本次调仓。')
        L.append(f'**换手预算检查**: 本次预计消耗约 {sum(sat_w[a] for a in exits) + (abs(core_w-inv*0.5) if core_breach else 0):.1%}(监管口径), 年内已用 {used:.0%}, 硬顶 {P["hard_cap"]:.0%}。')
        L.append('**执行后**: 更新 config.json 的 ledger.used_turnover 与 state.last_trade_date。')
    else:
        L.append('\n✅ 今日无调仓信号。')
        watch = [f'{a}(out {out_s[a]}/{p_eff})' for a in holdings if out_s.get(a, 0) > 0]
        watch += [f'{a}(in {v}/{p_eff})' for a, v in in_s.items() if v > 0]
        if watch: L.append('观察名单: ' + ', '.join(watch))
        if blocked: L.append('⏸️ 已过换出线但受7天最短持有保护: ' + ', '.join(blocked))

    L.append('\n## 五、换手预算')
    L.append(f'\n年内已用 **{used:.0%}** / 硬顶 {P["hard_cap"]:.0%}(监管上限200%×0.97) | 年度进度 {elapsed:.0%} | 分级降速: {"⚠️已触发, 持续期升至15日" if slow else "未触发(持续期12日)"}')
    L.append(f'\n---\n*V1.1规则见《卫星轮动引擎V1.1规则.md》; 打分/信号仅依据用户提供的数据文件; 本报告不构成自动交易指令。*')

    rpt = '\n'.join(L)
    os.makedirs(args.out, exist_ok=True)
    fp = os.path.join(args.out, f'监控报告_{d.strftime("%Y%m%d")}.md')
    open(fp, 'w', encoding='utf-8').write(rpt)
    print(rpt)
    print(f'\n💾 报告已保存: {fp}')
    sys.exit(2 if triggered else 0)

if __name__ == '__main__':
    main()
