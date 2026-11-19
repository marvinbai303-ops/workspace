import pathlib,json,av,numpy as np
from faster_whisper import WhisperModel
b=pathlib.Path('douyin_research');vid='7700469388663999720';x=json.load(open(b/'video_manifest.json'))[vid];p=b/'videos'/x['file'];start=485
parts=[]
with av.open(str(p)) as c:
 s=c.streams.audio[0];c.seek(int(start/s.time_base),stream=s,backward=True);rs=av.AudioResampler(format='fltp',layout='mono',rate=16000)
 for f in c.decode(audio=0):
  for o in rs.resample(f):
   ot=float(o.pts*o.time_base);a=o.to_ndarray().ravel();a=a[max(0,int((start-ot)*16000)):];parts.append(a)
audio=np.concatenate(parts);model=WhisperModel('/Users/yangguang/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120',device='cpu',compute_type='int8',cpu_threads=2)
segs,info=model.transcribe(audio,language='zh',beam_size=1,vad_filter=False)
out=[]
for s in segs:
 row={'start':round(s.start+start,3),'end':round(s.end+start,3),'text':s.text};out.append(row);print(row,flush=True)
(b/'formula_audit'/'38尾部补核.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
