#!/usr/bin/env python3
import time
from faster_whisper import WhisperModel

LARGE = "/Users/yangguang/Documents/Claude/Projects/产业趋势研究&选股/scraper/models/faster-whisper-large-v3"
AUDIO = "光模块市场发展趋势分析.m4a"
CLIP = "150,320"
PROMPT = ("以下是关于光模块、光通信、数据中心、AI算力、800G、1.6T、3.2T、CPO、LPO、"
          "硅光、锡膏、助焊剂、超细粉、焊点、唯特偶、中际旭创、新易盛、华为海思、"
          "贺利氏、铟泰、千住、T5、T6、T7、T8料号的卖方分析师路演。")

def run(tag, model_path):
    t0 = time.time()
    m = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=6)
    t1 = time.time()
    segs, info = m.transcribe(AUDIO, language="zh", beam_size=5,
                              vad_filter=True, condition_on_previous_text=True,
                              initial_prompt=PROMPT, clip_timestamps=CLIP)
    txt = "".join(s.text for s in segs)
    print(f"\n########## {tag} (load {t1-t0:.0f}s, transcribe {time.time()-t1:.0f}s "
          f"for ~170s audio) ##########")
    print(txt)

if __name__ == "__main__":
    run("TURBO (good settings)", "large-v3-turbo")
    run("LARGE-V3 (good settings)", LARGE)
