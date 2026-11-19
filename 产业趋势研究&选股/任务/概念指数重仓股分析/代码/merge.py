#!/usr/bin/env python3
"""Merge a batch into results.json and track attempts.
stdin lines (any order):
  ATTEMPTED:code1,code2,...    -> mark these concept codes as attempted (queried this turn)
  HARDFAIL:code1,code2,...     -> mark these as hard-failed (give up in forward pass; manual sweep later)
  <conceptcode>;<scode,sname,rawmktcap>;...   -> a success row (auto-marked attempted)
Prints status + next un-attempted concepts.
"""
import json, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
def load(p, d):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else d
def dump(p, o):
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

concepts = load(os.path.join(BASE, 'concepts.json'), [])
cmap = {c['code']: c for c in concepts}
results = load(os.path.join(BASE, 'results.json'), {})
attempted = set(load(os.path.join(BASE, 'attempted.json'), []))
hardfail = set(load(os.path.join(BASE, 'hardfail.json'), []))

added = []
for raw in sys.stdin:
    line = raw.strip()
    if not line:
        continue
    if line.startswith('ATTEMPTED:'):
        for c in line[len('ATTEMPTED:'):].split(','):
            if c.strip():
                attempted.add(c.strip())
        continue
    if line.startswith('HARDFAIL:'):
        for c in line[len('HARDFAIL:'):].split(','):
            if c.strip():
                attempted.add(c.strip()); hardfail.add(c.strip())
        continue
    parts = line.split(';')
    ccode = parts[0].strip()
    holdings = []
    for h in parts[1:]:
        h = h.strip()
        if not h:
            continue
        f = h.split(',')
        holdings.append({'code': f[0].strip(), 'name': f[1].strip(),
                         'mktcap_yi': round(float(f[2].strip())/1e8, 1)})
    ci = cmap.get(ccode, {})
    results[ccode] = {'name': ci.get('name'), 'ytd': ci.get('ytd'), 'holdings': holdings}
    attempted.add(ccode)
    hardfail.discard(ccode)  # a success clears any prior hardfail
    added.append(ccode)

dump(os.path.join(BASE, 'results.json'), results)
dump(os.path.join(BASE, 'attempted.json'), sorted(attempted))
dump(os.path.join(BASE, 'hardfail.json'), sorted(hardfail))

done = set(results.keys())
unattempted = [c['code'] for c in concepts if c['code'] not in attempted]
print(f'Added {len(added)}. DONE={len(done)}/{len(concepts)}  attempted={len(attempted)}  '
      f'unattempted={len(unattempted)}  hardfail={len(hardfail)}')
print('--- next un-attempted (up to 10) ---')
for code in unattempted[:10]:
    print(f'  {code}  {cmap[code]["name"]}')
if hardfail:
    print('--- hardfail (need manual sweep) ---')
    for code in sorted(hardfail):
        print(f'  {code}  {cmap[code]["name"]}')
