import av,json,sys,time
from pathlib import Path
from PIL import Image,ImageDraw
from concurrent.futures import ThreadPoolExecutor
base=Path(__file__).resolve().parents[1]
manifest=json.load(open(base/'video_manifest.json'))
ids=set(map(int,sys.argv[1:]))
def extract(v):
 idx=v['idx']; out=base/f'formula_audit/scanframes/{idx:02d}';out.mkdir(parents=True,exist_ok=True)
 c=av.open(str(base/'videos'/v['file']));s=c.streams.video[0];s.thread_type='AUTO';target=0; n=0; cards=[]
 for f in c.decode(s):
  if f.time is None or f.time+0.02<target:continue
  im=f.to_image(); im.thumbnail((720,1280));im.save(out/f'{target:05d}.jpg',quality=78)
  if target%10==0:
   thumb=im.copy();thumb.thumbnail((135,240));card=Image.new('RGB',(135,260),'white');card.paste(thumb,(0,20));ImageDraw.Draw(card).text((3,3),f'{idx:02d} {target//60:02d}:{target%60:02d}',fill='black');cards.append(card)
  n+=1;target+=2
 for j in range(0,len(cards),24):
  batch=cards[j:j+24];sheet=Image.new('RGB',(135*8,260*((len(batch)+7)//8)),'#ddd')
  for k,im in enumerate(batch):sheet.paste(im,((k%8)*135,(k//8)*260))
  sheet.save(base/f'formula_audit/contact_sheets/all_{idx:02d}_{j//24}.jpg',quality=88)
 print(f'DONE {idx:02d} {n}',flush=True);return idx,n
rows=sorted((v for v in manifest.values() if not ids or v['idx'] in ids),key=lambda v:v['idx'])
with ThreadPoolExecutor(max_workers=3) as ex: results=list(ex.map(extract,rows))
json.dump(dict(results),open(base/'formula_audit/frame_counts.json','w'),indent=2)
