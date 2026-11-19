import pathlib,json,time
from faster_whisper import WhisperModel
base=pathlib.Path('douyin_research'); vid='7685362553472801187'; m=json.load(open(base/'video_manifest.json'))[vid]; p=base/'videos'/m['file']
model=WhisperModel('/Users/yangguang/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf',device='cpu',compute_type='int8',cpu_threads=4)
segments,info=model.transcribe(str(p),language='zh',beam_size=5,vad_filter=True,initial_prompt='股票，交易系统，期权，期货，市场宽广度，阿姆氏指标，PCR，资金流向。')
lines=[f'# 修复转写｜01｜{vid}', '',f'> 来源：本地完整视频 `{m["file"]}`；原逐字稿误用第03音频。本稿由原视频音轨重新ASR，非人工逐字校订。', '',f'> 重新转写模型：faster-whisper-large-v3-turbo，language=zh，CPU int8。','']
rows=[]; t=time.time()
for s in segments:
 line=f'[{int(s.start//60):02}:{s.start%60:06.3f}–{int(s.end//60):02}:{s.end%60:06.3f}] {s.text}'
 print(line,flush=True);lines.append(line);rows.append({'start':s.start,'end':s.end,'text':s.text})
 (base/'formula_audit'/'transcripts_corrected'/f'{vid}.md').write_text('\n'.join(lines)+'\n')
 (base/'formula_audit'/'transcripts_corrected'/f'{vid}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print('FINISHED_SECONDS',time.time()-t,flush=True)
