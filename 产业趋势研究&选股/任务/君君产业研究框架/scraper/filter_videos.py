#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按标题/标签初筛：剔除宏观/汇率/黄金/消费医药/基金制度八卦/纯大盘点评等非核心内容，
只保留 AI算力·半导体·光模块·存储·先进封装·新能源 等产业链研究 + 买方方法论。
输出 output/videos_selected.json，并打印 保留/剔除 两份清单供人工复核。"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"
videos = json.loads((OUT / "videos.json").read_text(encoding="utf-8"))

# 命中任一即【剔除】（非核心：宏观汇率/贵金属/消费医药/基金制度八卦/纯大盘情绪点评）
EXCLUDE = [
    "日元", "人民币", "加息", "降息", "美联储", "紧缩", "滞胀", "黄金", "白银", "沃什",
    "铜价", "有色金属", "商品期货", "焦煤", "海南封关",
    "白酒", "茅台", "创新药", "炒药", "医药", "AI医疗",
    "基金新规", "基金经理", "老鼠仓", "量化新规", "微盘股", "量化收割", "监管降温",
    "券商", "北交所", "马斯克", "雷布斯", "小米", "4000点",
]
# 命中任一即【强制保留】（即使含上面的词，也算核心：新能源/算力能源等）
KEEP_FORCE = [
    "锂电", "锂矿", "六氟", "储能", "电力设备", "电网", "光伏", "特高压", "燃气轮机", "燃机",
    "电池", "新能源",
]


def decide(v):
    t = (v.get("desc") or "")
    if any(k in t for k in KEEP_FORCE):
        return True, "新能源/能源核心"
    for k in EXCLUDE:
        if k in t:
            return False, f"非核心:{k}"
    return True, "产业/方法论"


keep, drop = [], []
for v in sorted(videos, key=lambda a: a.get("create_time") or 0, reverse=True):
    ok, reason = decide(v)
    (keep if ok else drop).append((v, reason))

(OUT / "videos_selected.json").write_text(
    json.dumps([v for v, _ in keep], ensure_ascii=False, indent=2), encoding="utf-8")


def hrs(items):
    return sum((v.get("duration_sec") or 0) for v, _ in items) / 3600


print(f"【保留 {len(keep)} 条 / {hrs(keep):.1f} 小时】 【剔除 {len(drop)} 条 / {hrs(drop):.1f} 小时】")
print(f"原始 172 条 / {hrs(keep)+hrs(drop):.1f} 小时\n")
print("=" * 70)
print(f"以下 {len(drop)} 条被【剔除】（如有你想保留的，告诉我编号）：")
print("=" * 70)
for i, (v, reason) in enumerate(drop, 1):
    print(f"{i:2d}. [{v.get('duration_sec',0):.0f}s] {v.get('create_time_str','')[:10]}  "
          f"{v.get('desc','')[:42]}  ←{reason}")
