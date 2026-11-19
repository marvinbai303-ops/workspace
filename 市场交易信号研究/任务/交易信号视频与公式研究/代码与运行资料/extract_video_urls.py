"""从既有抓包响应中提取每个视频的完整播放地址（含音轨优先）。"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ['harvest.json', 'collection_cap.json']

awemes = {}

def collect(obj):
    """递归寻找 aweme 对象（含 video.play_addr）。"""
    if isinstance(obj, dict):
        if 'aweme_id' in obj and isinstance(obj.get('video'), dict):
            vid = str(obj['aweme_id'])
            if vid not in awemes or len(json.dumps(obj)) > len(json.dumps(awemes[vid])):
                awemes[vid] = obj
        for v in obj.values():
            collect(v)
    elif isinstance(obj, list):
        for v in obj:
            collect(v)

for fn in SOURCES:
    p = os.path.join(BASE, fn)
    if not os.path.exists(p):
        continue
    data = json.load(open(p))
    for rec in data:
        body = rec.get('body', '')
        if not body:
            continue
        try:
            collect(json.loads(body))
        except Exception as e:
            print('SKIP body in', fn, str(e)[:60])

def urls_of(addr):
    if not isinstance(addr, dict):
        return []
    out = []
    for u in addr.get('url_list') or []:
        if isinstance(u, str) and u.startswith('http') and u not in out:
            out.append(u)
    return out

result = {}
for vid, a in awemes.items():
    v = a.get('video') or {}
    cands = []

    def add(addr, tag, size=0):
        for u in urls_of(addr):
            cands.append({'url': u, 'tag': tag, 'size': size or (addr.get('data_size') or 0)})

    # 优先：主播放地址（通常 1080p 且音视频合一）
    add(v.get('play_addr'), 'play_addr')
    add(v.get('download_addr'), 'download_addr')
    add(v.get('play_addr_h264'), 'play_addr_h264')
    # 备用：各码率档位，按码率降序，只保留带音轨标记的
    brs = [b for b in (v.get('bit_rate') or []) if isinstance(b, dict)]
    brs.sort(key=lambda b: b.get('bit_rate') or 0, reverse=True)
    for b in brs:
        add(b.get('play_addr'), 'bit_rate_%s' % (b.get('gear_name') or b.get('bit_rate')))

    # 去重（按 URL）
    seen, uniq = set(), []
    for c in cands:
        if c['url'] not in seen:
            seen.add(c['url'])
            uniq.append(c)

    result[vid] = {
        'id': vid,
        'desc': a.get('desc') or '',
        'create_time': a.get('create_time'),
        'duration': (v.get('duration') or a.get('duration') or 0) / 1000.0,
        'width': v.get('width'),
        'height': v.get('height'),
        'has_audio_tag': bool((v.get('play_addr') or {}).get('file_cs', '').find('|a:') >= 0),
        'candidates': uniq,
    }

out = os.path.join(BASE, 'video_urls.json')
json.dump(result, open(out, 'w'), ensure_ascii=False, indent=1)

vids = json.load(open(os.path.join(BASE, 'videos.json')))
ids = [str(x['id']) for x in vids]
covered = [i for i in ids if result.get(i, {}).get('candidates')]
print('抓包中 aweme 总数:', len(awemes))
print('清单视频数:', len(ids), '有可用地址:', len(covered))
print('缺失地址:', [i for i in ids if i not in covered])
print('额外 aweme（不在清单中）:', [k for k in result if k not in ids][:20])
print('候选数分布:', {n: sum(1 for r in result.values() if len(r['candidates']) == n) for n in range(0, 6)})
print('带音轨标记:', sum(1 for r in result.values() if r['has_audio_tag']))
print('主地址示例:', result[ids[0]]['candidates'][0]['url'][:180] if result.get(ids[0], {}).get('candidates') else 'N/A')
print('saved', out)
