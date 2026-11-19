"""批量下载抖音完整视频（音视频合一 MP4），带候选地址回退与完整性校验。"""
import json, os, re, sys, time, urllib.request, concurrent.futures

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'videos')
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
    'Accept': '*/*',
}

urls = json.load(open(os.path.join(BASE, 'video_urls.json')))
order = json.load(open(os.path.join(BASE, 'videos.json')))


def safe_title(desc, limit=26):
    s = re.sub(r'#\S+', ' ', desc or '')
    s = re.sub(r'[\s\r\n]+', ' ', s).strip()
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', s)
    s = s[:limit].strip(' .·-')
    return s or 'video'


def check_mp4(path):
    """返回 (是否含视频轨, 是否含音频轨)；moov 在文件头，读取前 512KB 足够。"""
    with open(path, 'rb') as f:
        data = f.read(512 * 1024)
    if data[4:8] != b'ftyp':
        return False, False
    handlers = []
    i = 0
    while True:
        i = data.find(b'hdlr', i + 1)
        if i < 0 or len(handlers) > 10:
            break
        handlers.append(data[i + 12:i + 16].decode('latin1', 'ignore'))
    return 'vide' in handlers, 'soun' in handlers


def filename_for(idx, item, vid):
    date = item.get('date') or ''
    title = safe_title(item.get('desc'))
    return f"{idx:02d}_{date}_{vid}_{title}.mp4"


jobs = []
for idx, item in enumerate(order, 1):
    vid = str(item['id'])
    info = urls.get(vid)
    if not info or not info.get('candidates'):
        print('NO_URL', vid)
        continue
    jobs.append((idx, item, vid, info))


def dl(job):
    idx, item, vid, info = job
    path = os.path.join(OUT, filename_for(idx, item, vid))
    if os.path.exists(path):
        size = os.path.getsize(path)
        hv, ha = check_mp4(path)
        if size > 200000 and hv and ha:
            return dict(id=vid, file=os.path.basename(path), size=size, status='skip', video=hv, audio=ha)

    errors = []
    # 主地址 + 备用地址，最多尝试 8 个候选
    for c in info['candidates'][:8]:
        tmp = path + '.part'
        try:
            req = urllib.request.Request(c['url'], headers=HEADERS)
            t = time.time()
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
                while True:
                    chunk = r.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            size = os.path.getsize(tmp)
            expect = c.get('size') or 0
            hv, ha = check_mp4(tmp)
            if size < 200000 or not hv:
                raise ValueError(f'bad mp4 size={size} video={hv} audio={ha}')
            if expect and size < expect * 0.9:
                raise ValueError(f'incomplete {size}/{expect}')
            os.replace(tmp, path)
            return dict(id=vid, file=os.path.basename(path), size=size, status='ok',
                        tag=c['tag'], sec=round(time.time() - t, 1), video=hv, audio=ha,
                        duration=info.get('duration'), desc=item.get('desc'))
        except Exception as e:
            errors.append(f"{c['tag']}:{str(e)[:70]}")
            if os.path.exists(tmp):
                os.remove(tmp)
    return dict(id=vid, file=None, size=0, status='ERR', errors=errors)


workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
    results = list(ex.map(dl, jobs))

ok = [r for r in results if r['status'] in ('ok', 'skip')]
bad = [r for r in results if r['status'] == 'ERR']
no_audio = [r for r in ok if not r.get('audio')]
print('TOTAL', len(results), 'OK', len(ok), 'FAILED', len(bad), 'NO_AUDIO', len(no_audio))
print('BYTES_GB', round(sum(r['size'] for r in ok) / 1e9, 2), 'ELAPSED_S', round(time.time() - t0, 1))
for r in bad:
    print('  FAIL', r['id'], r.get('errors', [])[:3])
for r in no_audio:
    print('  NO_AUDIO', r['id'], r['file'])

manifest = {r['id']: r for r in ok}
json.dump(manifest, open(os.path.join(BASE, 'video_manifest.json'), 'w'), ensure_ascii=False, indent=1)
print('manifest -> video_manifest.json')
