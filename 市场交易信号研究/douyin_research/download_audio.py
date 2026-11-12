import json, os, sys, urllib.request, concurrent.futures

os.makedirs('audio', exist_ok=True)
urls = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'audio_urls.json'))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
}

def dl(item):
    vid, url = item
    path = f'audio/{vid}.mp4'
    if os.path.exists(path) and os.path.getsize(path) > 100000:
        return vid, os.path.getsize(path), 'skip'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=90) as r, open(path, 'wb') as f:
            f.write(r.read())
        return vid, os.path.getsize(path), 'ok'
    except Exception as e:
        return vid, 0, 'ERR ' + str(e)[:80]

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(dl, urls.items()))
ok = [r for r in results if r[2] in ('ok', 'skip')]
bad = [r for r in results if r[2].startswith('ERR')]
print('OK', len(ok), 'BAD', len(bad), 'TOTAL_MB', round(sum(r[1] for r in ok) / 1e6, 1))
for r in bad:
    print(' ', r)
json.dump({r[0]: f'audio/{r[0]}.mp4' for r in ok}, open('audio_files.json', 'w'), ensure_ascii=False, indent=1)
