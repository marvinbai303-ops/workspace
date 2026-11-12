"""对超大视频采用含音轨的 download_addr，分段并发下载并校验。"""
import json, os, sys, time, urllib.request, concurrent.futures

BASE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.join(BASE, 'videos')
VIDEO_ID = sys.argv[1] if len(sys.argv) > 1 else '7700469388663999720'
SEGMENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 6

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
    'Accept': '*/*',
}

urls = json.load(open(os.path.join(BASE, 'video_urls.json')))[VIDEO_ID]
order = json.load(open(os.path.join(BASE, 'videos.json')))
idx = next(i for i, x in enumerate(order, 1) if str(x['id']) == VIDEO_ID)
item = order[idx - 1]

# 文件名与 download_videos.py 保持一致
import re
def safe_title(desc, limit=26):
    s = re.sub(r'#\S+', ' ', desc or '')
    s = re.sub(r'[\s\r\n]+', ' ', s).strip()
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', s)
    return (s[:limit].strip(' .·-') or 'video')

target = os.path.join(VID, f"{idx:02d}_{item['date']}_{VIDEO_ID}_{safe_title(item['desc'])}.mp4")

# 只选带音轨的候选：download_addr 优先（体积适中），play_addr 兜底
cands = [c for c in urls['candidates'] if c['tag'] == 'download_addr']
cands += [c for c in urls['candidates'] if c['tag'] == 'play_addr']


def head(url):
    req = urllib.request.Request(url, headers={**HEADERS, 'Range': 'bytes=0-0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        cr = r.headers.get('Content-Range', '')
        total = int(cr.split('/')[-1]) if '/' in cr else 0
        r.read()
        return total


def fetch_seg(args):
    url, start, end, path = args
    req = urllib.request.Request(url, headers={**HEADERS, 'Range': f'bytes={start}-{end}'})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, 'wb') as f:
        while True:
            b = r.read(512 * 1024)
            if not b:
                break
            f.write(b)
    return os.path.getsize(path)


def check(path):
    with open(path, 'rb') as f:
        d = f.read(512 * 1024)
    hs, i = [], 0
    while True:
        i = d.find(b'hdlr', i + 1)
        if i < 0 or len(hs) > 10:
            break
        hs.append(d[i + 12:i + 16].decode('latin1', 'ignore'))
    return d[4:8] == b'ftyp', 'vide' in hs, 'soun' in hs


for c in cands:
    try:
        total = head(c['url'])
        if not total:
            print('NO_LENGTH', c['tag'], c['url'].split('/')[2]); continue
        print('TRY', c['tag'], c['url'].split('/')[2], 'total', round(total / 1e6, 1), 'MB')
        step = total // SEGMENTS
        ranges = []
        for i in range(SEGMENTS):
            s = i * step
            e = total - 1 if i == SEGMENTS - 1 else (i + 1) * step - 1
            ranges.append((c['url'], s, e, f'/tmp/dyseg_{VIDEO_ID}_{i}'))
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=SEGMENTS) as ex:
            sizes = list(ex.map(fetch_seg, ranges))
        print('  segments', sizes, 'elapsed', round(time.time() - t0, 1), 's')
        if sum(sizes) != total:
            print('  SIZE_MISMATCH', sum(sizes), total); continue
        tmp = target + '.part'
        with open(tmp, 'wb') as out:
            for _, _, _, p in ranges:
                with open(p, 'rb') as f:
                    while True:
                        b = f.read(4 * 1024 * 1024)
                        if not b: break
                        out.write(b)
        for _, _, _, p in ranges:
            os.remove(p)
        ok, hv, ha = check(tmp)
        if not (ok and hv and ha):
            print('  BAD_TRACKS', ok, hv, ha); os.remove(tmp); continue
        os.replace(tmp, target)
        print('DONE', os.path.basename(target), os.path.getsize(target), 'bytes', 'video+audio OK')
        break
    except Exception as e:
        print('  ERR', str(e)[:120])
else:
    print('ALL_CANDIDATES_FAILED')
