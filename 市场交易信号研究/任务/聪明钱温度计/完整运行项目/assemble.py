import json
from pathlib import Path
from build_data import build
ROOT=Path(__file__).resolve().parent
d=build()
encoded=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
html=(ROOT/'dashboard.template.html').read_text().replace('__BOOTSTRAP__',encoded)
(ROOT/'聪明钱温度计.html').write_text(html)
(ROOT/'worker/index.js').write_text('const PAGE = '+json.dumps(html,ensure_ascii=False)+';\nconst SEED = '+encoded+';\n'+(ROOT/'worker/runtime.js').read_text())
manifest=ROOT/'.openai/hosting.json'
m=json.loads(manifest.read_text());m.update(r2='BUCKET',capabilities=['mcp']);manifest.write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps({'latest':d['latestDate'],'snapshots':len(d['snapshots']),'mcl_days':len(d['mcl']),'html_bytes':len(html.encode())},ensure_ascii=False))
