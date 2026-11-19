import re, os, glob, json

BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research'
os.makedirs(f'{BASE}/times', exist_ok=True)

# 视频编号 <- 文件名前缀；id <- 文件名中的 19 位数字
id2no = {}
for f in glob.glob(f'{BASE}/videos/*.mp4'):
    b = os.path.basename(f)
    m = re.match(r'(\d+)_.*?_(\d{16,20})_', b)
    if m:
        id2no[m.group(2)] = int(m.group(1))
print('mapped videos', len(id2no))

HIGH = ['公式', '代码', '屏幕', '看一下', '看一下屏幕', '展示', '展示一下', '这张图', '这个图',
        '表格', '算法', '除以', '计算', '上轨', '下轨', '标准差', '红线', '蓝线', '绿线',
        '曲线', '编程', '源码', '公布', '公开给', '画一', '坐标轴', '这条线', '那条线',
        'K线', '周线', '日线', '副图', '主图', '指标是', '数值是', '截图', '图形',
        '市盈率', '市净率', 'GDP', '国债', '息差', 'PCR', '阿姆', 'TRIN', 'MCL',
        '宽广度', '额价差', '成交量', '成交额', '比值', '比例', '百分点', '基点',
        '系统', '数据处理', '量化', '回测', '评分', '记录表', '仓位报告']
MID = ['数据', '指标', '观察点', '数值', '多少', '倍', '%', '点', '线', '图', '表']

def parse_t(s):
    parts = s.strip().split(':')
    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except Exception:
        return None
    return None

summary = []
for fp in sorted(glob.glob(f'{BASE}/transcripts/*.md')):
    vid = os.path.basename(fp)[:-3]
    no = id2no.get(vid)
    if no is None:
        continue
    txt = open(fp, encoding='utf-8').read()
    segs = []
    for line in txt.split('\n'):
        m = re.match(r'^\[([^\],]+),([^\],]+)[^\]]*\]\s*(.*)$', line.strip())
        if not m:
            continue
        st, en = parse_t(m.group(1)), parse_t(m.group(2))
        if st is None or en is None:
            continue
        body = m.group(3)
        score = sum(3 for k in HIGH if k in body) + sum(1 for k in MID if k in body)
        segs.append((st, en, score, body[:60]))
    if not segs:
        continue
    duration = max(e for _, e, _, _ in segs)
    # 高分段：段首与段中，最多每段 3 个点
    ranked = sorted(segs, key=lambda x: -x[2])[:10]
    pts = set()
    for st, en, sc, _ in ranked:
        if sc < 3:
            continue
        pts.add(round(st + 0.4, 2))
        pts.add(round(min(st + 2.0, en - 0.1), 2))
        if en - st > 5:
            pts.add(round((st + en) / 2, 2))
    # 全片均匀兜底：每 12 秒一帧
    t = 0.4
    while t < duration:
        pts.add(round(t, 2))
        t += 12.0
    times = sorted(p for p in pts if 0 <= p <= duration)
    out = f'{BASE}/times/{no:02d}.txt'
    open(out, 'w').write('\n'.join(f'{p:.2f}' for p in times) + '\n')
    summary.append(dict(no=no, id=vid, dur=round(duration, 1), frames=len(times),
                        hot=len([s for s in segs if s[2] >= 6])))

json.dump(summary, open(f'{BASE}/times/_summary.json', 'w'), ensure_ascii=False, indent=1)
print('videos', len(summary), 'total frames', sum(s['frames'] for s in summary))
print('hot segs', sum(s['hot'] for s in summary))
