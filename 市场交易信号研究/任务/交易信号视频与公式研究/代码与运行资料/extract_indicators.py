import json, re, os, glob, collections

BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research'
vids = {v['id']: v for v in json.load(open(f'{BASE}/videos.json'))}
names = {'7698297594887604287': '照妖镜', '7686278450684004352': '金融宝藏',
         '7686145209003935770': '研判', '7685362419392071726': '数据证伪'}
order = {v['id']: i + 1 for i, v in enumerate(json.load(open(f'{BASE}/videos.json')))}

CATS = {
    'A_宽广度与量价': ['宽广度', '涨跌家数', '红盘', '腾落', 'ADL', 'ADR', '涨跌比', '阿姆', 'TRIN',
                 '额价差', '量能', '放量', '缩量', '换手', 'MCL', '麦克', '量价', '冰点', '上涨家数',
                 '下跌家数', '成交金额', '成交额'],
    'B_期权与衍生品': ['PCR', 'pcr', '认沽', '认购', 'put', 'call', '期权', '隐含波动', 'IV', '升贴水',
                 '期货', '主力合约', '持仓报告', '中信期货', '净多', '净空', '宽基', 'ETF', '50ETF',
                 '做空', '对冲', '波动率'],
    'C_债券利率与宏观资金': ['国债', '收益率曲线', '倒挂', '股债', '息差', '利差', '欧洲美元', '在岸美元',
                    'SHIBOR', '拆放', '主权债', '中美利差', '债券', '美联储', '加息', '降息', '十年期',
                    '资金流向', '聪明钱', '大资金'],
    'D_估值与筹码': ['总市值', 'GDP', '市净率', '等权', '估值', '高管', '增减持', '抛售', '公募', '汇金',
                '中证金融', '社保', '仓位', '筹码', '市盈率', '低估', '高估'],
    'E_传统技术分析': ['MACD', 'CCI', '布林', '一目均衡', '均线', '周K', '日K', '趋势线', '支撑位',
                 'VWMACD', '标准差', '上轨', '下轨', '技术分析', '背离'],
    'F_外围市场': ['恒生', '国企指数', '外围', '港股', '外资', '美股', 'A50'],
}
CALC = ['计算', '公式', '除以', '比值', '比例', '算法', '编程', '量化系统', '数据源', '数据处理',
        '自己写', '加权', '移动平均', '平滑', '标准差', '轨道', '怎么算', '等于', '乘以', '分之',
        '口径', '拆分', '反推', '搭建', '架设']
NUM = re.compile(r'\d+(?:\.\d+)?\s*(?:%|倍|个基点|bp|万亿|亿|万|点)|\b0\.\d+\b|\b\d\.\d+\b')

files = sorted(glob.glob(f'{BASE}/transcripts/*.md'))
print('transcript files', len(files))
rows = []
for fp in files:
    vid = os.path.basename(fp)[:-3]
    txt = open(fp, encoding='utf-8').read()
    lines = [l.strip() for l in txt.split('\n') if l.strip().startswith('[')]
    v = vids.get(vid, {})
    for ln in lines:
        body = re.sub(r'^\[[^\]]+\]\s*', '', ln)
        hits = {c: [k for k in kws if k in body] for c, kws in CATS.items()}
        hits = {c: ks for c, ks in hits.items() if ks}
        if not hits: continue
        calc = [k for k in CALC if k in body]
        nums = NUM.findall(body)
        rows.append(dict(vid=vid, no=order.get(vid, 0), date=v.get('date', ''),
                         title=v.get('desc', '')[:60], line=ln, body=body,
                         cats=list(hits), kws=sum(hits.values(), []), calc=calc, nums=nums))

print('matched segments', len(rows))
cnt = collections.Counter(k for r in rows for k in r['kws'])
print('\n=== TOP KEYWORDS ===')
for k, n in cnt.most_common(70):
    print(f'{k:12s} {n:4d}  视频数 {len(set(r["vid"] for r in rows if k in r["kws"]))}')

# 计算方法相关段落（含计算线索或数字）
key = [r for r in rows if r['calc'] or len(r['nums']) >= 2]
key.sort(key=lambda r: (r['no'], r['line']))
print('\ncalculation-relevant segments', len(key))

out = ['# 指标与计算方法 · 逐字稿原文摘录\n',
       f'> 从 {len(files)} 篇逐字稿中抽取 {len(rows)} 个指标相关段落，其中 {len(key)} 个含计算线索/数值。\n']
for cat in CATS:
    cr = [r for r in rows if cat in r['cats']]
    cr.sort(key=lambda r: r['no'])
    out.append(f'\n\n## {cat}（{len(cr)} 段）\n')
    last = None
    for r in cr:
        if r['no'] != last:
            out.append(f'\n### [{r["no"]:02d}] {r["date"]} {names.get(vids.get(r["vid"], {}).get("mix", ""), "")}｜{r["title"][:45]}\n')
            last = r['no']
        flag = ' ★' if (r['calc'] or len(r['nums']) >= 2) else ''
        out.append(f'-{flag} {r["body"]}\n')

open(f'{BASE}/指标原文摘录.md', 'w', encoding='utf-8').write(''.join(out))

# 计算线索专档
out2 = ['# 计算方法 / 阈值 / 实证数值 · 原文专档\n']
last = None
for r in key:
    if r['no'] != last:
        out2.append(f'\n### [{r["no"]:02d}] {r["date"]} {r["title"][:50]}\n')
        last = r['no']
    out2.append(f'- {r["body"]}\n')
open(f'{BASE}/计算方法原文专档.md', 'w', encoding='utf-8').write(''.join(out2))
print('\n摘录字数', len(''.join(out)), '专档字数', len(''.join(out2)))
