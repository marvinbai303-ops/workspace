#!/bin/bash
# 用 curl 稳健下载 faster-whisper-large-v3 模型文件（带重试+断点续传），
# 规避 huggingface_hub 客户端在国内镜像上的 SSL 掐流问题。
# 下完后用：python3 douyin_transcribe.py transcribe --model models/faster-whisper-large-v3
set -u
BASE="https://hf-mirror.com/Systran/faster-whisper-large-v3/resolve/main"
DIR="$(cd "$(dirname "$0")" && pwd)/models/faster-whisper-large-v3"
mkdir -p "$DIR"; cd "$DIR" || exit 1

# faster-whisper 加载所需文件（model.bin 最大，放最后）
FILES="config.json preprocessor_config.json tokenizer.json vocabulary.json model.bin"

for f in $FILES; do
  echo ">>> 下载 $f"
  ok=0
  for attempt in $(seq 1 80); do
    if curl -L --connect-timeout 30 --retry 5 --retry-delay 2 --retry-all-errors -C - \
            -o "$f" "$BASE/$f"; then
      ok=1; break
    fi
    echo "    $f 第 $attempt 次中断，2秒后续传重试..."
    sleep 2
  done
  [ "$ok" = 1 ] && echo "    ✅ $f 完成" || echo "    ❌ $f 多次失败"
done

echo "=== 全部文件 ==="
ls -lh
