import subprocess, glob, os, concurrent.futures, json, time

BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research'
os.chdir(BASE)
os.makedirs('frames', exist_ok=True)

def run(f):
    n = os.path.basename(f).split('_')[0]
    out = f'frames/{n}'
    os.makedirs(out, exist_ok=True)
    tf = f'times/{n}.txt'
    if not os.path.exists(tf):
        return dict(no=n, err='no times file')
    t0 = time.time()
    try:
        r = subprocess.run(['./frame_extract3', f, out, tf],
                           capture_output=True, text=True, timeout=300)
        return dict(no=n, out=r.stdout.strip(), err=r.stderr.strip()[:120],
                    rc=r.returncode, sec=round(time.time() - t0, 1))
    except Exception as e:
        return dict(no=n, err=str(e)[:120])

files = sorted(glob.glob('videos/*.mp4'))
print('videos', len(files), flush=True)
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for i, r in enumerate(ex.map(run, files), 1):
        results.append(r)
        print(i, r.get('no'), r.get('out', r.get('err')), r.get('sec', ''), flush=True)

json.dump(results, open('frames/_batch_log.json', 'w'), ensure_ascii=False, indent=1)
total = sum(len(glob.glob(f'frames/{r["no"]}/*.jpg')) for r in results)
print('TOTAL_FRAMES', total, flush=True)
