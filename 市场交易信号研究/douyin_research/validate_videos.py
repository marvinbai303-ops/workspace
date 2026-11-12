"""校验已下载视频：容器、音视频轨、时长、大小一致性。"""
import json, os, struct, glob

BASE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.join(BASE, 'videos')
manifest = json.load(open(os.path.join(BASE, 'video_manifest.json')))
urls = json.load(open(os.path.join(BASE, 'video_urls.json')))
order = json.load(open(os.path.join(BASE, 'videos.json')))


def probe(path):
    with open(path, 'rb') as f:
        head = f.read(1024 * 1024)
    if head[4:8] != b'ftyp':
        return None
    handlers, i = [], 0
    while True:
        i = head.find(b'hdlr', i + 1)
        if i < 0 or len(handlers) > 10:
            break
        handlers.append(head[i + 12:i + 16].decode('latin1', 'ignore'))
    # mvhd: timescale + duration
    dur = None
    p = head.find(b'mvhd')
    if p > 0:
        ver = head[p + 4]
        if ver == 0:
            ts, du = struct.unpack('>II', head[p + 16:p + 24])
        else:
            ts = struct.unpack('>I', head[p + 24:p + 28])[0]
            du = struct.unpack('>Q', head[p + 28:p + 36])[0]
        if ts:
            dur = round(du / ts, 1)
    return {'video': 'vide' in handlers, 'audio': 'soun' in handlers,
            'duration': dur, 'size': os.path.getsize(path)}


rows = []
for idx, item in enumerate(order, 1):
    vid = str(item['id'])
    m = manifest.get(vid)
    if not m:
        rows.append((idx, vid, 'MISSING', 0, None, None))
        continue
    p = os.path.join(VID, m['file'])
    r = probe(p) if os.path.exists(p) else None
    if not r:
        rows.append((idx, vid, 'BAD_FILE', 0, None, None))
        continue
    status = 'OK' if (r['video'] and r['audio']) else ('NO_AUDIO' if not r['audio'] else 'NO_VIDEO')
    rows.append((idx, vid, status, round(r['size'] / 1e6, 1), r['duration'], m['file']))

ok = [r for r in rows if r[2] == 'OK']
bad = [r for r in rows if r[2] != 'OK']
print('清单数', len(order), '完整(含音视频)', len(ok), '异常', len(bad))
print('总大小 GB', round(sum(r[3] for r in ok) / 1000, 2))
print('时长合计 分钟', round(sum(r[4] or 0 for r in ok) / 60, 1))
print('单文件时长范围', min((r[4] or 0) for r in ok), '-', max((r[4] or 0) for r in ok), '秒')
for r in bad:
    print('  ISSUE', r)

# 额外文件（不在 manifest 中）
known = {m['file'] for m in manifest.values()}
extra = [os.path.basename(p) for p in glob.glob(os.path.join(VID, '*.mp4')) if os.path.basename(p) not in known]
if extra:
    print('额外文件', len(extra), extra[:5])

json.dump([{'idx': r[0], 'id': r[1], 'status': r[2], 'mb': r[3], 'duration_s': r[4], 'file': r[5]} for r in rows],
          open(os.path.join(BASE, 'video_validation.json'), 'w'), ensure_ascii=False, indent=1)
print('saved video_validation.json')
