#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, time, datetime
from faster_whisper import WhisperModel

AUDIO = "东阳光业务转型与估值分析.m4a"
OUT_TS = "东阳光业务转型与估值分析_转写_带时间.txt"
OUT_TXT = "东阳光业务转型与估值分析_转写.txt"
PROG = "transcribe_progress.log"

def hhmmss(s):
    return str(datetime.timedelta(seconds=int(s)))

def log(msg):
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, flush=True)

t0 = time.time()
log(f"[{datetime.datetime.now():%H:%M:%S}] 加载模型 large-v3-turbo (int8)...")

model = WhisperModel(
    "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    device="cpu",
    compute_type="int8",
    cpu_threads=8,
)

log(f"[{datetime.datetime.now():%H:%M:%S}] 模型加载完成，开始转写...")

segments, info = model.transcribe(
    AUDIO,
    language="zh",
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
    initial_prompt="以下是一篇关于东阳光（东阳光集团/东阳光药）公司业务转型、磁材、电极箔、化成箔、合金箔、医药、PVDF、制冷剂与公司估值分析的财经研究汇报。",
)

total = info.duration
log(f"音频总时长: {hhmmss(total)}  语言: {info.language} (p={info.language_probability:.2f})")

# reset outputs
open(OUT_TS, "w", encoding="utf-8").close()
open(OUT_TXT, "w", encoding="utf-8").close()

last_report = 0
plain_buf = []
for seg in segments:
    text = seg.text.strip()
    line_ts = f"[{hhmmss(seg.start)} -> {hhmmss(seg.end)}] {text}"
    with open(OUT_TS, "a", encoding="utf-8") as f:
        f.write(line_ts + "\n")
    with open(OUT_TXT, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    # progress report roughly every 60s of audio processed
    if seg.end - last_report >= 60:
        pct = seg.end / total * 100
        elapsed = time.time() - t0
        speed = seg.end / elapsed if elapsed > 0 else 0
        eta = (total - seg.end) / speed if speed > 0 else 0
        log(f"  进度 {pct:5.1f}%  已转写到 {hhmmss(seg.end)}  用时 {hhmmss(elapsed)}  速度 {speed:.1f}x  预计剩余 {hhmmss(eta)}")
        last_report = seg.end

elapsed = time.time() - t0
log(f"[{datetime.datetime.now():%H:%M:%S}] 转写完成！总用时 {hhmmss(elapsed)}")
log(f"输出: {OUT_TS}")
log(f"输出: {OUT_TXT}")
