from pathlib import Path
import glob
from faster_whisper import WhisperModel


ROOT = Path('/Users/yangguang/Documents/Codex/workspace/基金经理研究')
AUDIO_DIR = ROOT / 'ima_recordings'
OUT_DIR = ROOT / 'ima_transcripts'
OUT_DIR.mkdir(parents=True, exist_ok=True)

model_candidates = glob.glob('/Users/yangguang/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*')
if not model_candidates:
    raise SystemExit('cached faster-whisper-small model not found')

model = WhisperModel(model_candidates[0], device='cpu', compute_type='int8', cpu_threads=8)

prompts = {
    '民生加银刘浩交流': '这是中文基金经理交流录音，涉及全球资产配置、深度价值、消费、公用事业、银行、地产、铜、汽车、电力设备、思源电气、宁德、福耀。',
    '万家基金乔良路演': '这是中文基金经理路演录音，涉及主动量化、885001、红利、自由现金流、PB-ROE、可转债、权益基金、等权、分散化、回撤。',
    '嘉实基金龙昌伦交流': '这是中文量化基金经理交流录音，涉及指数、ETF、量化、主观、投顾、衍生品、场内期权、跟踪误差、传统因子、AI、价值、成长、质量、小盘、超额收益回撤。',
}

for audio in sorted(AUDIO_DIR.glob('*.m4a')):
    stem = audio.stem
    out = OUT_DIR / f'{stem}.txt'
    if out.exists() and out.stat().st_size > 1000:
        print(f'SKIP {audio.name}', flush=True)
        continue
    print(f'TRANSCRIBE {audio.name}', flush=True)
    segments, info = model.transcribe(
        str(audio),
        language='zh',
        beam_size=5,
        best_of=5,
        temperature=0,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=prompts.get(stem, ''),
    )
    with out.open('w', encoding='utf-8') as f:
        f.write(f'# {stem}\n')
        f.write(f'# detected_language={info.language} probability={info.language_probability:.3f}\n')
        f.write(f'# duration_seconds={info.duration:.1f}\n\n')
        for seg in segments:
            line = seg.text.strip()
            if line:
                f.write(f'[{seg.start:08.1f}-{seg.end:08.1f}] {line}\n')
                f.flush()
    print(f'DONE {out}', flush=True)
