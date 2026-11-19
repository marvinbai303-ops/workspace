"""对比新抓取的合集响应与既有清单，识别新增作品并合并索引。"""
import json, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'harvest_new.json')

awemes = {}


def collect(obj):
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


for rec in json.load(open(SRC)):
    body = rec.get('body', '')
    if not body:
        continue
    try:
        collect(json.loads(body))
    except Exception:
        pass

def urls_of(addr):
    if not isinstance(addr, dict):
        return []
    out = []
    for u in addr.get('url_list') or []:
        if isinstance(u, str) and u.startswith('http') and u not in out:
            out.append(u)
    return out


def build_entry(a):
    v = a.get('video') or {}
    cands, seen = [], set()

    def add(addr, tag):
        for u in urls_of(addr):
            if u not in seen:
                seen.add(u)
                cands.append({'url': u, 'tag': tag, 'size': (addr.get('data_size') or 0)})

    add(v.get('play_addr'), 'play_addr')
    add(v.get('download_addr'), 'download_addr')
    add(v.get('play_addr_h264'), 'play_addr_h264')
    brs = [b for b in (v.get('bit_rate') or []) if isinstance(b, dict)]
    brs.sort(key=lambda b: b.get('bit_rate') or 0, reverse=True)
    for b in brs:
        add(b.get('play_addr'), 'bit_rate_%s' % (b.get('gear_name') or b.get('bit_rate')))
    return cands


videos_list = json.load(open(os.path.join(BASE, 'videos.json')))
urls_map = json.load(open(os.path.join(BASE, 'video_urls.json')))
known = {str(x['id']) for x in videos_list}

new_ids, refreshed = [], 0
for vid, a in awemes.items():
    cands = build_entry(a)
    if not cands:
        continue
    if vid in known:
        # 仅刷新签名地址，不改变下载状态
        urls_map[vid]['candidates'] = cands
        refreshed += 1
        continue
    v = a.get('video') or {}
    ct = a.get('create_time') or 0
    date = datetime.datetime.fromtimestamp(ct + 8 * 3600, datetime.timezone.utc).strftime('%Y-%m-%d') if ct else ''
    dur = round((v.get('duration') or a.get('duration') or 0) / 60000.0, 1)
    entry = {
        'id': vid, 'date': date, 'dur': dur, 'desc': a.get('desc') or '',
        'abstract': '', 'chapters': [], 'audio': '', 'mix': '',
    }
    videos_list.append(entry)
    urls_map[vid] = {
        'id': vid, 'desc': entry['desc'], 'create_time': ct, 'duration': dur * 60,
        'width': v.get('width'), 'height': v.get('height'),
        'has_audio_tag': bool((v.get('play_addr') or {}).get('file_cs', '').find('|a:') >= 0),
        'candidates': cands,
    }
    new_ids.append(vid)

json.dump(videos_list, open(os.path.join(BASE, 'videos.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(urls_map, open(os.path.join(BASE, 'video_urls.json'), 'w'), ensure_ascii=False, indent=1)

print('抓取到 aweme:', len(awemes), '| 命中已有:', refreshed, '| 新增:', len(new_ids))
for vid in new_ids:
    e = urls_map[vid]
    print(f"  NEW {vid} {e['create_time'] and datetime.datetime.fromtimestamp(e['create_time']+8*3600, datetime.timezone.utc).strftime('%Y-%m-%d')} "
          f"{round(e['duration']/60,1)}min {e['width']}x{e['height']} 候选{len(e['candidates'])} | {e['desc'][:50]}")
json.dump(new_ids, open(os.path.join(BASE, 'new_ids.json'), 'w'), ensure_ascii=False, indent=1)
print('saved new_ids.json')
