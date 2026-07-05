#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音博主视频内容批量转写流水线
===============================

把目标博主主页的所有视频 -> 拿到列表 -> 下载音频 -> Whisper 转写 -> 输出文字稿。
最终生成符合《00_抖音视频批量转写操作指引.md》第三节格式的合并文稿，可直接交给后续蒸馏。

三个阶段（可分开跑，可断点续传）：
  1) collect    用 Playwright 打开主页、滚动加载、拦截抖音接口，抓全视频列表 -> videos.json
  2) download   逐条下载音频（优先 yt-dlp 重新解析，省空间只取音轨）-> audio/
  3) transcribe 用 faster-whisper 把音频转文字 -> transcripts/*.txt + 合并稿.md
  all           依次跑完三步

设计要点：
  - 抖音有登录墙 + 风控，collect 阶段用「持久化登录态」：第一次跑会弹出浏览器，
    你用抖音 App 扫码登录一次，cookie 存在 user_data/ 里，之后不用再登。
  - 抓列表靠拦截抖音自己发出的 aweme/post 接口响应，不逆向签名，最稳。
  - 默认只抓「博主自己发布」的视频（不含合集/喜欢）。

用法见同目录 README.md。
"""

import os
# 国内直连 huggingface.co 经常超时，默认改走镜像下载 Whisper 模型。
# 必须在 import faster_whisper / huggingface_hub 之前设置才生效。
# 如果你在海外或不想用镜像，运行前设环境变量覆盖：export HF_ENDPOINT=https://huggingface.co
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")  # 镜像偶尔慢，放宽单请求超时

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "output"
USER_DATA_DIR = HERE / "user_data"          # Playwright 持久化登录态
CST = timezone(timedelta(hours=8))           # 抖音时间戳是秒级，转北京时间

# 抖音「发布列表」接口特征（拦截这个；放宽匹配以兼容不同版本路径）
AWEME_POST_API = "aweme/post/"


def _write_netscape_cookies(cookies, path: Path):
    """把 Playwright 的 cookie 写成 yt-dlp 能读的 Netscape 格式。"""
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path_ = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = int(c.get("expires", 0)) if c.get("expires", -1) > 0 else 0
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, flag, path_, secure, str(expires), name, value]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 阶段 1：采集视频列表
# ---------------------------------------------------------------------------
async def collect(user_url: str, out_dir: Path, headless: bool, max_scroll: int):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("缺少 playwright，请先: pip install playwright && playwright install chromium")

    out_dir.mkdir(parents=True, exist_ok=True)
    videos = {}          # aweme_id -> 视频信息
    done = asyncio.Event()

    def handle_aweme_list(aweme_list):
        new = 0
        for a in aweme_list or []:
            aid = a.get("aweme_id")
            if not aid or aid in videos:
                continue
            video = a.get("video", {}) or {}
            play = video.get("play_addr", {}) or {}
            url_list = play.get("url_list", []) or []
            ct = a.get("create_time")
            videos[aid] = {
                "aweme_id": aid,
                "desc": (a.get("desc") or "").strip(),
                "create_time": ct,
                "create_time_str": datetime.fromtimestamp(ct, CST).strftime("%Y-%m-%d %H:%M") if ct else "",
                "duration_sec": round((video.get("duration") or 0) / 1000, 1),
                "share_url": f"https://www.douyin.com/video/{aid}",
                "play_url_list": url_list,   # 可能过期，下载时优先用 yt-dlp 重解析
            }
            new += 1
        return new

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        async def on_response(resp):
            if AWEME_POST_API in resp.url:
                try:
                    data = await resp.json()
                except Exception:
                    return
                n = handle_aweme_list(data.get("aweme_list"))
                if n:
                    print(f"  + 拦截到 {n} 条，累计 {len(videos)}")
                if data.get("has_more") == 0:
                    done.set()

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("response", on_response)

        print(f"打开主页：{user_url}")
        await page.goto(user_url, wait_until="domcontentloaded", timeout=60000)

        # 关键：停下来等用户登录。脚本只等固定几秒来不及扫码，所以改为等你按回车。
        print("\n" + "=" * 60)
        print("请在弹出的【浏览器窗口】里完成以下操作：")
        print("  1) 如出现登录框 -> 用手机抖音App扫码登录（只需第一次）")
        print("  2) 登录后确认页面显示出博主的作品列表（看到视频缩略图）")
        print("  3) 然后回到【本终端窗口】按一下回车键，脚本开始自动抓取")
        print("=" * 60)
        loop = asyncio.get_event_loop()
        # 用线程执行 input，避免阻塞事件循环（登录期间仍能拦截接口）
        await loop.run_in_executor(None, input, ">>> 准备好后按回车继续... ")

        # 登录后重新加载主页，确保作品列表接口被触发
        print("重新加载主页，开始抓取...")
        try:
            await page.goto(user_url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass
        await asyncio.sleep(3)
        if not videos:
            print("（暂未拦截到作品接口，继续滚动尝试。如果一直是0，多半是没登录成功或被风控。）")

        # 滚动到底，触发分页加载
        last_count = -1
        stable_rounds = 0
        for i in range(max_scroll):
            if done.is_set():
                print("接口返回 has_more=0，已到末尾。")
                break
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2.0)
            cur = len(videos)
            if cur == last_count:
                stable_rounds += 1
                # 连续多轮没新增，再多等等（可能在加载）
                if stable_rounds >= 8:
                    print(f"连续 8 轮无新增，判定加载完毕（共 {cur} 条）。")
                    break
            else:
                stable_rounds = 0
            last_count = cur
            if (i + 1) % 10 == 0:
                print(f"  ...已滚动 {i+1} 次，累计 {cur} 条")

        # 导出 cookie（Netscape 格式）给 yt-dlp 用，显著提升下载成功率
        try:
            cookies = await ctx.cookies()
            _write_netscape_cookies(cookies, out_dir / "cookies.txt")
            print(f"已导出登录 cookie -> {out_dir / 'cookies.txt'}")
        except Exception as e:
            print(f"导出 cookie 失败（不影响列表采集）：{e}")

        await ctx.close()

    vids = sorted(videos.values(), key=lambda x: x.get("create_time") or 0, reverse=True)
    out_file = out_dir / "videos.json"
    out_file.write_text(json.dumps(vids, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 采集完成：共 {len(vids)} 条视频 -> {out_file}")
    if not vids:
        print("⚠️ 没抓到视频。常见原因：未登录 / 主页结构变化 / 被风控。可加 --show 看浏览器排查。")
    return vids


# ---------------------------------------------------------------------------
# 阶段 2：下载音频
# ---------------------------------------------------------------------------
def have(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None


MEDIA_EXTS = (".mp3", ".m4a", ".mp4", ".webm", ".aac", ".wav", ".mov")


def _existing_media(audio_dir: Path, aid: str):
    """该视频是否已下载过（任意媒体后缀）。"""
    for f in audio_dir.glob(f"{aid}.*"):
        if f.suffix.lower() in MEDIA_EXTS:
            return f
    return None


def download(out_dir: Path, limit: int, videos_path: str = ""):
    # 默认下载全部；传 --videos 指向筛选后的列表（如 videos_selected.json）则只下那些
    videos_file = Path(videos_path) if videos_path else (out_dir / "videos.json")
    if not videos_file.exists():
        sys.exit(f"找不到 {videos_file}，请先跑 collect（或检查 --videos 路径）。")
    print(f"下载清单来源：{videos_file}")
    videos = json.loads(videos_file.read_text(encoding="utf-8"))
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    use_ytdlp = have("yt-dlp")
    has_ffmpeg = have("ffmpeg")
    if not use_ytdlp:
        print("⚠️ 未检测到 yt-dlp（推荐，能重新解析最稳）。安装：python3 -m pip install yt-dlp")
    if not has_ffmpeg:
        print("ℹ️ 未检测到 ffmpeg：将直接下载整段视频文件，转写时由 Whisper 自带解码器读取（无需 ffmpeg）。")

    cookies_file = out_dir / "cookies.txt"  # collect 时导出的登录 cookie，供 yt-dlp 用

    ok, fail = 0, 0
    todo = videos[:limit] if limit > 0 else videos
    for i, v in enumerate(todo, 1):
        aid = v["aweme_id"]
        existing = _existing_media(audio_dir, aid)
        if existing:
            print(f"[{i}/{len(todo)}] 已存在，跳过 {aid}")
            ok += 1
            continue
        print(f"[{i}/{len(todo)}] 下载 {aid}  {v.get('desc','')[:30]}")

        success = False
        if use_ytdlp:
            cmd = ["yt-dlp", v["share_url"], "--no-playlist",
                   "--no-warnings", "--quiet",
                   "-o", str(audio_dir / f"{aid}.%(ext)s")]
            if has_ffmpeg:
                # 有 ffmpeg：直接抽成 mp3，最省空间
                cmd += ["-x", "--audio-format", "mp3"]
            else:
                # 无 ffmpeg：下载单文件（已含音轨），Whisper 直接读
                cmd += ["-f", "b"]
            if cookies_file.exists():
                cmd += ["--cookies", str(cookies_file)]
            try:
                subprocess.run(cmd, check=True)
                success = _existing_media(audio_dir, aid) is not None
            except subprocess.CalledProcessError:
                success = False

        # 兜底：用 collect 拦截到的 play_url 直接拉流（需要 ffmpeg 转码时才用）
        if not success and v.get("play_url_list") and has_ffmpeg:
            target = audio_dir / f"{aid}.mp3"
            for purl in v["play_url_list"]:
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-headers",
                         "Referer: https://www.douyin.com/\r\nUser-Agent: Mozilla/5.0",
                         "-i", purl, "-vn", "-ar", "16000", "-ac", "1",
                         str(target)],
                        check=True, capture_output=True,
                    )
                    success = target.exists()
                    if success:
                        break
                except subprocess.CalledProcessError:
                    continue

        if success:
            ok += 1
        else:
            fail += 1
            print(f"   ❌ 失败 {aid}（链接可能已过期，可重跑 collect 刷新后再 download）")
        time.sleep(2)  # 批量下载时轻微限速，降低被风控概率

    print(f"\n✅ 下载完成：成功 {ok}，失败 {fail} -> {audio_dir}")


# ---------------------------------------------------------------------------
# 阶段 3：转写
# ---------------------------------------------------------------------------
def _ensure_model(model_size: str, retries: int = 8):
    """
    稳健下载 Whisper 模型并返回本地路径。
    国内镜像在并发拉文件时常出现 SSL 断流，用 max_workers=1 串行下载 + 多次重试规避。
    若本地已完整缓存，snapshot_download 会直接返回缓存路径（离线可用）。
    """
    from huggingface_hub import snapshot_download
    # 直接给本地路径/含 model.bin 的目录就不当作仓库名下载
    if Path(model_size).exists():
        return model_size
    repo = f"Systran/faster-whisper-{model_size}"
    # 先查本地缓存（不联网）：已缓存就直接用，避免在flaky镜像上做无谓的联网校验
    try:
        path = snapshot_download(repo, local_files_only=True)
        print(f"  使用本地缓存模型：{path}")
        return path
    except Exception:
        pass
    last = None
    for attempt in range(1, retries + 1):
        try:
            path = snapshot_download(repo, max_workers=1)  # 串行，避开镜像并发掐流
            print(f"  模型就绪：{path}")
            return path
        except Exception as e:
            last = e
            print(f"  模型下载第 {attempt}/{retries} 次中断（{type(e).__name__}），3秒后续传重试...")
            time.sleep(3)
    sys.exit(
        f"\n❌ 模型多次下载失败：{last}\n"
        "可尝试：1) 换个网络/稍后再试（已下分片会续传）；\n"
        "       2) 先用已缓存的小模型出结果：加 --model small（质量略低，术语易错）；\n"
        f"      3) 手动下载：HF_ENDPOINT=https://hf-mirror.com huggingface-cli download {repo}\n"
    )


def _load_corrections():
    """读取同目录 corrections.json 术语纠错表（忽略 _ 开头的说明键）。"""
    f = HERE / "corrections.json"
    if not f.exists():
        return {}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return {k: v for k, v in d.items() if not k.startswith("_")}
    except Exception as e:
        print(f"读取 corrections.json 失败，跳过纠错：{e}")
        return {}


def merge_transcripts(out_dir: Path):
    """把 transcripts/ 下所有 txt 合并成《合并转写稿.md》（按发布时间倒序，应用术语纠错）。
    与转写解耦：分片并行跑完后，单独跑一次 merge 即可汇总全部。"""
    videos_file = out_dir / "videos.json"
    videos = json.loads(videos_file.read_text(encoding="utf-8")) if videos_file.exists() else []
    by_id = {v["aweme_id"]: v for v in videos}
    tr_dir = out_dir / "transcripts"
    txts = sorted(tr_dir.glob("*.txt"))
    if not txts:
        print("transcripts/ 下还没有转写稿，跳过合并。")
        return
    corrections = _load_corrections()
    n_fix = [0]

    def fix(t):
        for wrong, right in corrections.items():
            if wrong in t:
                n_fix[0] += t.count(wrong)
                t = t.replace(wrong, right)
        return t

    items = [(by_id.get(tp.stem, {"aweme_id": tp.stem}), tp.read_text(encoding="utf-8"))
             for tp in txts]
    items.sort(key=lambda r: r[0].get("create_time") or 0, reverse=True)
    lines = ["# 博主视频转写合集\n",
             f"> 生成时间：{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}　共 {len(items)} 条"
             f"（已应用 {len(corrections)} 条术语纠错）\n"]
    for idx, (meta, text) in enumerate(items, 1):
        lines.append(f"\n### 视频 {idx}")
        lines.append(f"- 标题/主题：{(meta.get('desc') or '').strip() or '（无文案）'}")
        lines.append(f"- 发布日期：{meta.get('create_time_str', '')}")
        lines.append(f"- 链接：{meta.get('share_url', '')}")
        lines.append(f"- 时长：{meta.get('duration_sec', '')} 秒")
        lines.append("- 转写正文：")
        lines.append(fix(text) if text else "（转写为空）")
    merged = out_dir / "合并转写稿.md"
    merged.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ 合并完成：{len(items)} 条 -> {merged}（术语纠错命中 {n_fix[0]} 处）")


def transcribe(out_dir: Path, model_size: str, limit: int, threads: int = 0,
               beam: int = 1, shard: str = ""):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("缺少 faster-whisper，请先: pip install faster-whisper")

    videos_file = out_dir / "videos.json"
    videos = json.loads(videos_file.read_text(encoding="utf-8")) if videos_file.exists() else []
    by_id = {v["aweme_id"]: v for v in videos}

    audio_dir = out_dir / "audio"
    tr_dir = out_dir / "transcripts"
    tr_dir.mkdir(parents=True, exist_ok=True)
    audios = sorted(f for f in audio_dir.glob("*")
                    if f.suffix.lower() in MEDIA_EXTS)
    if limit > 0:
        audios = audios[:limit]
    if shard:  # --shard i/n：多进程各跑一部分（audios[i::n]），并行提速
        try:
            si, sn = (int(x) for x in shard.split("/"))
        except Exception:
            sys.exit("--shard 格式应为 i/n，例如 0/2")
        audios = audios[si::sn]
        print(f"分片模式 {si}/{sn}：本进程负责 {len(audios)} 条")
    if not audios:
        sys.exit(f"{audio_dir} 下没有要处理的音频（检查 download / --shard）。")

    if threads <= 0:
        threads = min(8, os.cpu_count() or 4)  # 物理核约8个，开满提速
    print(f"加载 Whisper 模型：{model_size}（CPU {threads} 线程，beam={beam}）")
    print(f"模型下载源 HF_ENDPOINT = {os.environ.get('HF_ENDPOINT')}")
    model_path = _ensure_model(model_size)
    # CPU 上跑：compute_type=int8 更快；有 NVIDIA 显卡可改 device='cuda'
    model = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=threads)

    done_n = 0
    for i, ap in enumerate(audios, 1):
        aid = ap.stem
        txt_path = tr_dir / f"{aid}.txt"
        meta = by_id.get(aid, {})
        if txt_path.exists():        # 断点续传：已转写的跳过
            done_n += 1
            continue
        title = (meta.get("desc") or "").splitlines()[0][:40] if meta.get("desc") else aid
        dur = meta.get("duration_sec") or 0
        print(f"[{i}/{len(audios)}] 转写 {aid}  ({dur:.0f}s)  {title}")
        t0 = time.time()
        try:
            segments, _ = model.transcribe(
                str(ap), language="zh", beam_size=beam,
                vad_filter=True,  # 去静音，减少幻觉
                initial_prompt="以下是关于产业趋势、行业研究、A股投资的普通话讲解。",
            )
            text = "".join(s.text for s in segments).strip()
        except Exception as e:
            # 单个文件损坏/解码失败时跳过并记录，绝不让它崩掉整批
            print(f"     ⚠️ 跳过（解码失败，可能文件损坏需重下）：{type(e).__name__}")
            with open(out_dir / "failed.txt", "a", encoding="utf-8") as fp:
                fp.write(f"{aid}\t{(meta.get('desc') or '')[:50]}\t{type(e).__name__}\n")
            continue
        txt_path.write_text(text, encoding="utf-8")
        el = time.time() - t0
        print(f"     用时 {el:.0f}s（{dur/el if el else 0:.1f}x 实时），剩 {len(audios)-i} 条")
    if done_n:
        print(f"（{done_n} 条此前已转写，跳过）")

    # 分片跑时各进程只处理一部分，统一在最后单独 merge；非分片则直接合并
    if shard:
        print("\n✅ 本分片转写完成。等所有分片都跑完后，运行一次合并：")
        print('   python3 douyin_transcribe.py merge')
    else:
        merge_transcripts(out_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="抖音博主视频批量转写流水线")
    ap.add_argument("stage", choices=["collect", "download", "transcribe", "merge", "all"],
                    help="执行哪个阶段")
    ap.add_argument("--url", default="https://www.douyin.com/user/"
                    "MS4wLjABAAAAsCMIUu_MVRxX0GKtrzyEoNYA2KoITYBWjPFTTvZAmGLsiTSUOydpWBbRqFDnj6Wi",
                    help="博主主页 URL")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="输出目录")
    ap.add_argument("--show", action="store_true", help="显示浏览器（首次登录/排查时用）")
    ap.add_argument("--max-scroll", type=int, default=200, help="最大滚动次数")
    ap.add_argument("--model", default="large-v3",
                    help="Whisper 模型: tiny/base/small/medium/large-v3，或本地模型目录路径")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条（0=全部，调试用）")
    ap.add_argument("--threads", type=int, default=0, help="转写用的CPU线程数（0=自动，约8）")
    ap.add_argument("--beam", type=int, default=1, help="解码beam大小（1=贪心最快，5=略准略慢）")
    ap.add_argument("--videos", default="", help="下载用的视频清单json（默认全部；筛选后传 videos_selected.json）")
    ap.add_argument("--shard", default="", help="分片并行: i/n，开n个进程各传 0/n 1/n ... 各跑一部分")
    args = ap.parse_args()

    out_dir = Path(args.out)

    if args.stage in ("collect", "all"):
        # collect 始终显示浏览器：首次需要扫码登录，且可观察加载是否正常
        asyncio.run(collect(args.url, out_dir, headless=False, max_scroll=args.max_scroll))
    if args.stage in ("download", "all"):
        download(out_dir, args.limit, videos_path=args.videos)
    if args.stage in ("transcribe", "all"):
        transcribe(out_dir, args.model, args.limit, threads=args.threads,
                   beam=args.beam, shard=args.shard)
    if args.stage == "merge":
        merge_transcripts(out_dir)


if __name__ == "__main__":
    main()
