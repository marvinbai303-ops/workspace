#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测速：在本机CPU上，small 和 large-v3 各转写约120秒音频，算出速度与25.4h总耗时估计。"""
import os, time
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
from faster_whisper import WhisperModel

AUDIO = "output/audio/7651891863795944767.mp4"
THREADS = min(8, os.cpu_count() or 4)
TOTAL_HOURS = 25.4

def bench(model_ref, label):
    print(f"\n=== {label}（{THREADS}线程, beam=1）===")
    t_load = time.time()
    m = WhisperModel(model_ref, device="cpu", compute_type="int8", cpu_threads=THREADS)
    print(f"模型加载用时 {time.time()-t_load:.0f}s")
    segs, _ = m.transcribe(AUDIO, language="zh", beam_size=1, vad_filter=True,
                           initial_prompt="以下是关于产业趋势、行业研究、A股投资的普通话讲解。")
    t0 = time.time(); audio_done = 0.0; sample = []
    for s in segs:
        audio_done = s.end
        sample.append(s.text)
        if audio_done >= 120:
            break
    el = time.time() - t0
    speed = audio_done / el if el else 0
    eta_h = TOTAL_HOURS / speed if speed else float("inf")
    print(f"处理 {audio_done:.0f}s 音频，用时 {el:.0f}s -> 速度 {speed:.2f}x 实时")
    print(f"按此速度，全部25.4h音频约需 {eta_h:.1f} 小时")
    print(f"试听转写片段：{''.join(sample)[:120]}")
    return speed

bench("small", "small 模型")
bench("models/faster-whisper-large-v3", "large-v3 模型(本地)")
