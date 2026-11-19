"""下载当前批量取数回执中的结果文件，并记录大小与行数。"""
import csv,io,json,re,hashlib
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent
manifest=ROOT/'download_manifest.json'
prior={x['file']:x['url'] for x in json.loads(manifest.read_text())} if manifest.exists() else {}
out=[]
for p in sorted((ROOT/'raw').glob('*.json')):
    r=json.loads(p.read_text())
    result=r.get('result',r)
    urls=re.findall(r'https?://o\.thsi\.cn/[^\s"\\<>]+\.csv',str(result))
    for i,url in enumerate(dict.fromkeys(urls)):
        target=ROOT/'downloads'/f'{p.stem}_{i}.csv'
        target.parent.mkdir(exist_ok=True)
        if not target.exists() or prior.get(str(target)) != url:
            with urlopen(url,timeout=60) as response: target.write_bytes(response.read())
        data=target.read_bytes()
        for enc in ['utf-8-sig','gb18030']:
            try:s=data.decode(enc);break
            except UnicodeDecodeError:continue
        rows=list(csv.reader(io.StringIO(s)))
        rec={'response':p.name,'url':url,'file':str(target),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
             'encoding':enc,'data_rows':max(0,len(rows)-1),'columns':rows[0] if rows else []}
        out.append(rec)
        print(f'{p.stem}: {rec["data_rows"]} rows, {rec["bytes"]} bytes')
(ROOT/'download_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
