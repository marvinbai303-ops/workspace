from __future__ import annotations

import json
import sys
from pathlib import Path

from faster_whisper import BatchedInferencePipeline, WhisperModel
from faster_whisper.audio import decode_audio


AUDIO = Path(
    "/Users/yangguang/Documents/Codex/workspace/选股素材/万泽股份/"
    "建投keycall-高温合金与生物医药业务分析.m4a"
)
OUT_DIR = Path(
    "/Users/yangguang/Documents/Codex/workspace/选股素材/万泽股份"
)
SMALL_MODEL = Path(
    "/Users/yangguang/.cache/huggingface/hub/"
    "models--Systran--faster-whisper-small/snapshots/"
    "536b0662742c02347bc0e980a01041f333bce120"
)
TURBO_MODEL = Path(
    "/Users/yangguang/.cache/huggingface/hub/"
    "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/"
    "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
)
FULL_MD = OUT_DIR / "建投keycall-高温合金与生物医药业务分析_全程转写.md"
QA_MD = OUT_DIR / "建投keycall-高温合金与生物医药业务分析_尾部Q&A精校.md"
RAW_JSON = OUT_DIR / "建投keycall-高温合金与生物医药业务分析_转写分段.json"

PROMPT = (
    "这是一场关于万泽股份、应流股份、高温合金、燃气轮机热端叶片、航空发动机"
    "和微生态医药的中信建投 key call。常见词包括：万泽股份、应流股份、西门子能源、"
    "安萨尔多、GE Vernova、Howmet、PCC、单晶叶片、定向叶片、良率、产能、稼动率、"
    "订单、认证、航发、商发、CJ-1000A、金双歧、定君生、SOFC、AI CAPEX、沙特。"
)
HOTWORDS = (
    "万泽股份 应流股份 西门子能源 安萨尔多 GE Vernova Howmet PCC 燃气轮机 "
    "单晶叶片 定向叶片 高温合金 良率 产能 稼动率 订单 认证 航发 商发 "
    "CJ-1000A 金双歧 定君生 SOFC AI CAPEX 沙特"
)
QA_START_SECONDS = 2200.0


def timestamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def transcribe(
    model_path: Path,
    start_seconds: float,
    beam_size: int,
    batched: bool,
    batch_size: int = 8,
) -> tuple[list[dict], dict]:
    model = WhisperModel(
        str(model_path),
        device="cpu",
        compute_type="int8",
        cpu_threads=8,
        num_workers=1,
    )
    common_args = dict(
        language="zh",
        task="transcribe",
        beam_size=beam_size,
        best_of=beam_size,
        temperature=0.0,
        condition_on_previous_text=True,
        initial_prompt=PROMPT,
        hotwords=HOTWORDS,
        repetition_penalty=1.1,
        no_repeat_ngram_size=6,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350},
        word_timestamps=False,
    )
    if batched:
        audio_input = str(AUDIO)
        if start_seconds:
            audio = decode_audio(str(AUDIO), sampling_rate=16000)
            audio_input = audio[int(start_seconds * 16000) :]
        pipeline = BatchedInferencePipeline(model)
        segments, info = pipeline.transcribe(
            audio_input,
            batch_size=batch_size,
            without_timestamps=False,
            **common_args,
        )
    else:
        segments, info = model.transcribe(
            str(AUDIO),
            clip_timestamps=str(start_seconds),
            **common_args,
        )
    rows: list[dict] = []
    for idx, segment in enumerate(segments, 1):
        row = {
            "start": round(segment.start + start_seconds, 3),
            "end": round(segment.end + start_seconds, 3),
            "text": segment.text.strip(),
            "avg_logprob": round(segment.avg_logprob, 4),
            "no_speech_prob": round(segment.no_speech_prob, 4),
        }
        if row["text"]:
            rows.append(row)
        if idx % 10 == 0:
            print(
                f"progress {timestamp(segment.end + start_seconds)} segments={len(rows)}",
                flush=True,
            )
    meta = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration + start_seconds,
        "duration_after_vad": info.duration_after_vad,
    }
    return rows, meta


def write_markdown(
    path: Path,
    title: str,
    rows: list[dict],
    meta: dict,
    model_name: str,
    note: str,
) -> None:
    lines = [
        f"# {title}",
        "",
        f"- 音频：`{AUDIO.name}`",
        f"- 本地识别模型：{model_name}",
        f"- 语言：{meta['language']}（置信度 {meta['language_probability']:.3f}）",
        f"- 音频时长：{timestamp(meta['duration'])}",
        f"- 说明：{note}",
        "",
        "## 转写正文",
        "",
    ]
    lines.extend(
        f"[{timestamp(row['start'])} - {timestamp(row['end'])}] {row['text']}"
        for row in rows
    )
    path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode == "full":
        print("starting full transcription with faster-whisper-small", flush=True)
        rows, meta = transcribe(
            SMALL_MODEL,
            0.0,
            beam_size=1,
            batched=True,
        )
        write_markdown(
            FULL_MD,
            "建投 key call：高温合金与生物医药业务分析 - 全程转写",
            rows,
            meta,
            "faster-whisper-small / CPU int8",
            "AI 本地转写，专有名词和数字需结合录音、演示稿复核。",
        )
        RAW_JSON.write_text(
            json.dumps(
                {"audio": AUDIO.name, "full_model": "small", "meta": meta, "segments": rows},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"saved {FULL_MD}", flush=True)
        print(f"saved {RAW_JSON}", flush=True)
    elif mode == "qa":
        print(
            f"starting tail transcription at {timestamp(QA_START_SECONDS)} "
            "with faster-whisper-large-v3-turbo",
            flush=True,
        )
        rows, meta = transcribe(
            TURBO_MODEL,
            QA_START_SECONDS,
            beam_size=3,
            batched=True,
            batch_size=4,
        )
        write_markdown(
            QA_MD,
            "建投 key call：尾部 Q&A 精校转写",
            rows,
            meta,
            "faster-whisper-large-v3-turbo / CPU int8",
            "从 00:36:40 起重转，覆盖录音尾部问答；AI 本地转写，专有名词和数字仍需结合原音复核。",
        )
        raw = json.loads(RAW_JSON.read_text(encoding="utf-8")) if RAW_JSON.exists() else {}
        raw["qa_model"] = "large-v3-turbo"
        raw["qa_start_seconds"] = QA_START_SECONDS
        raw["qa_meta"] = meta
        raw["qa_segments"] = rows
        RAW_JSON.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"saved {QA_MD}", flush=True)
        print(f"updated {RAW_JSON}", flush=True)
    else:
        raise SystemExit("usage: transcribe_wz.py [full|qa]")


if __name__ == "__main__":
    main()
