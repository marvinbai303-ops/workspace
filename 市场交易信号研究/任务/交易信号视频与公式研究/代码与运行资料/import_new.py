"""把发现的新作品并入 videos.json / video_urls.json，并输出待下载 ID。"""
import json, os, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET_SEC = 'MS4wLjABAAAAHwe0CgM38CCjWMNxHSvkydtX5zlrG38YoPTtrvkX7bRzlN2xJje0cqecaY-1jSay'

SRC = sys.argv[1] if len(sys.argv) > 1 else 'discovered.json'
discovered = json.load(open(os.path.join(BASE, SRC)))
videos = json.load(open(os.path.join(BASE, 'videos.json')))
urls = json.load(open(os.path.join(BASE, 'video_urls.json')))
known = {str(x['id']) for x in videos}


def urls_of(addr):
    if not isinstance(addr, dict):
        return []
    out = []
    for u in addr.get('url_list') or []:
        if isinstance(u, str) and u.startswith('http') and u not in out:
            out.append(u)
    return out


def cands_of(d):
    res, seen = [], set()

    def add(addr, tag):
        for u in urls_of(addr):
            if u not in seen:
                seen.add(u)
                res.append({'url': u, 'tag': tag, 'size': (addr.get('data_size') or 0)})

    add(d.get('play_addr'), 'play_addr')
    add(d.get('download_addr'), 'download_addr')
    add(d.get('play_addr_h264'), 'play_addr_h264')
    brs = [b for b in (d.get('bit_rate') or []) if isinstance(b, dict)]
    brs.sort(key=lambda b: b.get('bit_rate') or 0, reverse=True)
    for b in brs:
        add(b.get('play_addr'), 'bit_rate_%s' % (b.get('gear_name') or b.get('bit_rate')))
    return res


new_items = []
for d in discovered:
    if d.get('sec_uid') != TARGET_SEC or str(d['id']) in known:
        continue
    new_items.append(d)
new_items.sort(key=lambda x: x['create_time'])

added = []
for d in new_items:
    vid = str(d['id'])
    ct = d['create_time']
    date = datetime.datetime.fromtimestamp(ct + 8 * 3600, datetime.timezone.utc).strftime('%Y-%m-%d')
    dur = round((d.get('duration_ms') or 0) / 60000.0, 1)
    videos.append({'id': vid, 'date': date, 'dur': dur, 'desc': d.get('desc') or '',
                   'abstract': '', 'chapters': [], 'audio': '', 'mix': ''})
    urls[vid] = {'id': vid, 'desc': d.get('desc') or '', 'create_time': ct,
                 'duration': (d.get('duration_ms') or 0) / 1000.0,
                 'width': d.get('width'), 'height': d.get('height'),
                 'has_audio_tag': True, 'candidates': cands_of(d)}
    added.append(vid)

json.dump(videos, open(os.path.join(BASE, 'videos.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(urls, open(os.path.join(BASE, 'video_urls.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(added, open(os.path.join(BASE, 'new_ids.json'), 'w'), ensure_ascii=False, indent=1)

print('新增作品', len(added), '| 清单总数', len(videos))
for d in new_items:
    print(f"  {d['id']} {datetime.datetime.fromtimestamp(d['create_time']+8*3600,datetime.timezone.utc).strftime('%Y-%m-%d')} "
          f"{round((d.get('duration_ms') or 0)/60000,1)}min 候选{len(cands_of(d))} | {(d.get('desc') or '')[:40]}")
