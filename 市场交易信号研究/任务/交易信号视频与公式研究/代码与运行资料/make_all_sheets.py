import subprocess, glob, os, json

BASE = '/Users/yangguang/WorkBuddy/市场交易信号研究/douyin_research'
os.chdir(BASE)
os.makedirs('sheets', exist_ok=True)

index = {}
for d in sorted(glob.glob('frames/[0-9][0-9]')):
    no = os.path.basename(d)
    frames = sorted(glob.glob(f'{d}/t_*.jpg'))
    if not frames:
        continue
    out = f'sheets/{no}.jpg'
    r = subprocess.run(['./make_sheet', d, out, '6', '200'], capture_output=True, text=True)
    index[no] = dict(sheet=os.path.abspath(out),
                     frames=[os.path.basename(f) for f in frames],
                     times=[os.path.basename(f)[2:-4] for f in frames])
json.dump(index, open('sheets/_index.json', 'w'), ensure_ascii=False, indent=1)
print('sheets', len(index), 'total frames', sum(len(v['frames']) for v in index.values()))
