# 抖音博主视频批量转写脚本

把目标博主主页的**全部视频口播内容**变成文字稿。三步流水线，跑完直接产出
符合《00_抖音视频批量转写操作指引.md》第三节格式的 `合并转写稿.md`。

```
collect    打开主页 → 扫码登录(仅第一次) → 滚动加载 → 拦截抖音接口 → videos.json
download   逐条下载音频(只取音轨, mp3) → audio/
transcribe faster-whisper 中文转写 → transcripts/*.txt + 合并转写稿.md
```

---

## 一、安装环境（一次性）

> ✅ 本机已由 Claude 装好并验证：playwright + chromium、faster-whisper、yt-dlp、av 全部就绪，
> 全链路（下载→中文转写→生成合并稿）已端到端跑通。下面命令仅供换机器/重装时参考。

```bash
cd "/Users/yangguang/Documents/Claude/Projects/产业趋势研究&选股/scraper"

# 1) Python 依赖（注意是 python3 / pip3）
python3 -m pip install -r requirements.txt

# 2) Playwright 的浏览器内核
python3 -m playwright install chromium
```

> - **不需要 ffmpeg**：脚本会直接下载整段视频，由 Whisper 自带的解码器(av/PyAV)读取。
>   （若你愿意装 ffmpeg，下载会改成只存 mp3，更省空间，但非必需。）
> - 没有 NVIDIA 显卡也能跑，Whisper 默认走 CPU（int8 加速）。
> - 中文准确率最高用 `large-v3`（默认），CPU 上较慢；想先快速验证可用 `--model small`。
>   ⚠️ 实测 `small` 会把"碳化硅/光伏逆变器"等专业词转错，正式跑务必用 `large-v3`。

---

## 二、运行（注意：命令用 python3）

完整流程五步（分阶段，便于断点续传）：

```bash
# 1) 采集列表（弹浏览器，首次扫码登录，看到作品缩略图后回终端按回车）
python3 douyin_transcribe.py collect

# 2) 按标题筛选，剔除宏观/消费/基金八卦等非核心 -> output/videos_selected.json
python3 filter_videos.py

# 3) 只下载筛选后的视频音频
python3 douyin_transcribe.py download --videos output/videos_selected.json

# 4) 准备 large-v3 模型（国内用 curl 下，绕开镜像 SSL 掐流；~3GB 可续传）
bash get_model.sh

# 5) 转写（见下方挂机方案）
```

### 转写：长任务，挂机跑（large-v3 在 CPU 上约 0.6x 实时）

本机是 Intel CPU，large-v3 转写很慢。务必：① 在**自己的终端**跑（关掉 Claude 也不断）；
② 用 `caffeinate -i` 防止 Mac 休眠；③ `python3 -u` 让进度实时刷新。

**单进程（最简单，约30小时）：**
```bash
caffeinate -i python3 -u douyin_transcribe.py transcribe \
  --model models/faster-whisper-large-v3 2>&1 | tee transcribe.log
```

**双进程分片并行（约16-20小时，开两个终端窗口各跑一条）：**
```bash
# 终端A
caffeinate -i python3 -u douyin_transcribe.py transcribe \
  --model models/faster-whisper-large-v3 --shard 0/2 2>&1 | tee t0.log
# 终端B
caffeinate -i python3 -u douyin_transcribe.py transcribe \
  --model models/faster-whisper-large-v3 --shard 1/2 2>&1 | tee t1.log
# 两个都跑完后，合并成最终稿
python3 douyin_transcribe.py merge
```

- **断点续传**：中断后重跑同一条命令，已转写的会自动跳过。
- 想先小批量验证：加 `--limit 3`。
- 嫌慢可换 `--model small`（约8小时，但半导体术语错得多，见 corrections.json 纠错表）。

常用参数：

| 参数 | 说明 |
|------|------|
| `--model` | `small/medium/large-v3` 或本地模型目录（如 `models/faster-whisper-large-v3`） |
| `--videos` | 下载用的清单 json（筛选后传 `output/videos_selected.json`） |
| `--shard i/n` | 分片并行：开 n 个进程各传 `0/n 1/n …` |
| `--threads` | 转写 CPU 线程数（0=自动，约8） |
| `--beam` | 解码 beam（1=最快，5=略准略慢） |
| `--limit N` | 只处理前 N 条，调试用 |
| `--url` | 换一个博主主页 |

---

## 三、首次运行会发生什么

1. `collect` 阶段会弹出一个 Chromium 窗口打开博主主页。
2. **如果弹出登录框 → 用抖音 App 扫码登录一次。** 登录态存在 `scraper/user_data/`，以后不用再登。
3. 登录后脚本自动滚动到底、把所有作品的列表抓下来存进 `output/videos.json`。
4. 之后 `download` + `transcribe` 全自动，无人值守。

---

## 四、输出物

```
output/
├── videos.json          # 视频列表元数据（id/文案/发布时间/链接/时长）
├── audio/               # 每条视频的音频 .mp3
├── transcripts/         # 每条视频的转写 .txt
└── 合并转写稿.md         # ⭐ 汇总稿，按发布时间倒序，可直接交给后续蒸馏
```

---

## 五、注意事项

- 仅用于个人学习研究，勿传播下载内容。
- 抖音反爬/风控会变，若 `collect` 抓不到：加 `--show` 看浏览器、确认已登录、或稍后重试。
- `play_url` 有时效，下载优先用 yt-dlp 重新解析；若大量失败，重跑一次 `collect` 刷新链接再 `download`。
- 行业黑话/数字转写可能出错（如"碳化硅"），后续蒸馏时会按上下文还原。
