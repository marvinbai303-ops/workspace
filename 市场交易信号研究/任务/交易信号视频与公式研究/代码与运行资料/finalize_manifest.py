"""扫描 videos/ 生成最终清单（供校验脚本消费）。"""
import json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.join(BASE, 'videos')
order = json.load(open(os.path.join(BASE, 'videos.json')))

files = {}
for p in glob.glob(os.path.join(VID, '*.mp4')):
    parts = os.path.basename(p).split('_')
    if len(parts) >= 3 and parts[2].isdigit():
        files.setdefault(parts[2], os.path.basename(p))

manifest = {}
for idx, item in enumerate(order, 1):
    vid = str(item['id'])
    f = files.get(vid)
    if not f:
        continue
    p = os.path.join(VID, f)
    manifest[vid] = {'id': vid, 'file': f, 'size': os.path.getsize(p),
                     'status': 'ok', 'duration': item.get('dur', 0) * 60,
                     'desc': item.get('desc'), 'date': item.get('date'), 'idx': idx}

json.dump(manifest, open(os.path.join(BASE, 'video_manifest.json'), 'w'), ensure_ascii=False, indent=1)
print('manifest entries', len(manifest), '/', len(order))
missing = [str(x['id']) for x in order if str(x['id']) not in manifest]
print('missing', missing)
extra = [f for v, f in files.items() if v not in manifest]
print('extra files', extra)
