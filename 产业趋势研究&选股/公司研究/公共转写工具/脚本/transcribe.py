#!/usr/bin/env python3
import sys, time, argparse
from faster_whisper import WhisperModel

PROMPT = ("以下是一场关于光模块、光通信、数据中心、AI算力、英伟达、800G、1.6T、3.2T、"
          "CPO、LPO、硅光、相干、锡膏、助焊剂、超细粉、唯特偶、中际旭创、新易盛、"
          "华为海思、贺利氏、铟泰、千住、Alpha、T5、T6、T7、T8料号的卖方分析师路演。")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--clip", default=None, help='e.g. "0,150" to limit')
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--beam", type=int, default=5)
    args = ap.parse_args()

    t0 = time.time()
    m = WhisperModel(args.model, device="cpu", compute_type="int8",
                     cpu_threads=args.threads)
    load_t = time.time() - t0
    print(f"[{args.model}] model load: {load_t:.1f}s", flush=True)

    kw = dict(language="zh", beam_size=args.beam, vad_filter=True,
              condition_on_previous_text=True, initial_prompt=PROMPT,
              vad_parameters=dict(min_silence_duration_ms=2000))
    if args.clip:
        kw["clip_timestamps"] = args.clip

    t1 = time.time()
    segs, info = m.transcribe(args.audio, **kw)
    lines, chars = [], 0
    with open(args.out, "w") as f:
        for s in segs:
            line = f"[{s.start:7.1f}-{s.end:7.1f}] {s.text.strip()}"
            f.write(line + "\n"); f.flush()
            lines.append(line); chars += len(s.text)
            # progress heartbeat every ~60s of audio
            if len(lines) % 25 == 0:
                el = time.time() - t1
                print(f"  ..audio {s.end:6.1f}s done, wall {el:5.1f}s, "
                      f"speed {s.end/el:4.2f}x", flush=True)
    trans_t = time.time() - t1
    audio_end = lines and float(lines[-1].split("-")[1].split("]")[0]) or 0
    print(f"[{args.model}] transcribe wall: {trans_t:.1f}s for {audio_end:.1f}s "
          f"audio -> {audio_end/trans_t:.2f}x realtime, {chars} chars, "
          f"{len(lines)} segs", flush=True)
    print("---- sample (first 900 chars) ----", flush=True)
    print("\n".join(lines)[:900], flush=True)

if __name__ == "__main__":
    main()
