import re, os, glob, json, collections

BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research'
os.chdir(BASE)
os.makedirs('visual_transcripts', exist_ok=True)

rows = []
for fp in sorted(glob.glob('visual_scan/scan_*.md')):
    for line in open(fp, encoding='utf-8'):
        m = re.match(r'^\|\s*(\d{2})\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$', line)
        if not m:
            continue
        no, r, c, label, kind, desc = m.groups()
        label = label.strip()
        path = f'frames/{no}/t_{label}.jpg'
        if not os.path.exists(path):
            # 尝试按行列映射
            idx = json.load(open('sheets/_index.json')).get(no, {})
            fr = idx.get('frames', [])
            k = (int(r) - 1) * 6 + (int(c) - 1)
            if 0 <= k < len(fr):
                path = f'frames/{no}/{fr[k]}'
                label = fr[k][2:-4]
        if not os.path.exists(path):
            continue
        rows.append(dict(no=no, t=label, kind=kind.strip(), desc=desc.strip(), path=path))

print('parsed rows', len(rows), 'with file', sum(1 for r in rows if os.path.exists(r['path'])))

# 高价值类型与关键词优先
FORMULA = ('公式', '代码', '表格')
KEY = ['TRIN', '阿姆', 'MCL', 'PCR', '市值', 'GDP', '市净', 'PB', '市盈率', '股债', '息差',
       '标准差', '宽广度', '额价差', 'VWMACD', 'COT', 'ADL', 'ADR', '分位', '净持仓',
       'realtime', 'backtest', '评分', '高走', 'ARMS', 'A/D', '成交额', '持仓', '定价权']

def weight(r):
    d = r['desc'] + r['kind']
    w = 0
    if any(k in r['kind'] for k in FORMULA): w += 4
    w += sum(1 for k in KEY if k in d)
    return w

for r in rows:
    r['w'] = weight(r)

# 按 (视频, 描述前 30 字) 去重，每组最多保留 2 张（首 + 末），高权重组保留 3 张
groups = collections.defaultdict(list)
for r in rows:
    key = (r['no'], r['desc'][:28])
    groups[key].append(r)

chosen = []
for key, g in groups.items():
    g.sort(key=lambda x: float(x['t']) if x['t'].replace('.', '').isdigit() else 0)
    w = max(x['w'] for x in g)
    n = 3 if w >= 6 else (2 if w >= 3 else 1)
    if len(g) <= n:
        pick = g
    else:
        idxs = sorted(set([0, len(g) // 2, len(g) - 1]))[:n]
        pick = [g[i] for i in idxs]
    chosen.extend(pick)

chosen.sort(key=lambda r: (r['no'], float(r['t']) if r['t'].replace('.', '').isdigit() else 0))
byvid = collections.defaultdict(list)
for r in chosen:
    byvid[r['no']].append(r)

tasks = []
for no in sorted(byvid):
    items = byvid[no]
    lines = []
    for r in items:
        lines.append(f"- [ ] `{r['t']}s` | {r['kind']} | {os.path.abspath(r['path'])} | 扫描备注：{r['desc'][:110]}")
    p = f'refine/{no}.md'
    os.makedirs('refine', exist_ok=True)
    open(p, 'w', encoding='utf-8').write(f'# 视频 {no} 精读帧（{len(items)} 张）\n\n' + '\n'.join(lines) + '\n')
    tasks.append(dict(no=no, count=len(items), file=os.path.abspath(p),
                      paths=[os.path.abspath(r['path']) for r in items],
                      notes=[r['desc'][:110] for r in items]))

json.dump(tasks, open('refine/_tasks.json', 'w'), ensure_ascii=False, indent=1)
print('chosen', len(chosen), 'videos', len(tasks))
print('per video:', ' '.join(f'{t["no"]}:{t["count"]}' for t in tasks))
