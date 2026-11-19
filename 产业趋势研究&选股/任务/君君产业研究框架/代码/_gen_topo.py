# -*- coding: utf-8 -*-
# 生成 AI 产业链网格拓扑图 SVG（680 宽，6 列产业链 × 纵向价值链深度）
cols = [
    ("光通信链", "c-blue", [
        ("MP/SOI衬底", "材料设备019632", 1),
        ("光源EML/CW", "通信007817", 1),
        ("硅光SiPh", "通信007817", 0),
        ("光引擎FAU", "通信007817", 0),
        ("MPO连接器", "通信007817", 0),
        ("DSP", "通信007817", 0),
        ("模块CPO/LPO", "通信007817", 0),
        ("OCS·光纤缆", "通信007817", 0),
    ]),
    ("算力半导体", "c-amber", [
        ("半导体设备", "材料设备019632", 1),
        ("硅片/材料", "材料设备019632", 0),
        ("代工·中芯", "科创芯片017469", 1),
        ("GPU算力卡", "半导体008887", 1),
        ("ASIC设计", "芯片设计027574", 0),
        ("CPU(海外)", "半导体008887", 0),
    ]),
    ("存储·封装", "c-teal", [
        ("HBM", "半导体008887", 1),
        ("DRAM/NAND", "半导体008887", 0),
        ("存储模组", "半导体008887", 0),
        ("先进封装", "半导体008887", 1),
        ("封测", "半导体008887", 0),
        ("ABF膜/玻基", "电子001617", 1),
        ("MLCC", "电子001617", 0),
    ]),
    ("PCB·电子·端侧", "c-purple", [
        ("电子布Tglass", "电子001617", 1),
        ("覆铜板CCL", "电子001617", 0),
        ("ABF载板", "电子001617", 1),
        ("PCB高速板", "电子001617", 0),
        ("端侧PC/手机", "电子001617", 0),
    ]),
    ("AI·云·模型", "c-green", [
        ("云算力/涨价", "云计算021397", 0),
        ("大模型", "人工智能012733", 0),
        ("AI应用Agent", "软件018385", 0),
        ("GEO入口", "计算机160224", 0),
        ("港股大模型", "恒生013402", 0),
    ]),
    ("旁支·配套", "c-cyan", [
        ("散热液冷", "电子001617", 0),
        ("电源/燃机", "电力016185", 0),
        ("储能锂电", "电池012862", 0),
        ("商业航天", "军工512710", 0),
        ("机器人", "机器人018344", 0),
    ]),
]

W = 90
STEP = 102
X0 = 40
HEAD_Y = 64
HEAD_H = 30
CHIP_Y0 = 102
CHIP_H = 30
CHIP_STEP = 34

maxchips = max(len(c[2]) for c in cols)
last_bottom = CHIP_Y0 + (maxchips - 1) * CHIP_STEP + CHIP_H
H = int(last_bottom + 70)

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

parts = []
parts.append(f'<svg width="100%" viewBox="0 0 680 {H}" role="img" xmlns="http://www.w3.org/2000/svg">')
parts.append('<title>AI产业链网格拓扑图与ETF联接基金匹配</title>')
parts.append('<desc>按博主147条视频蒸馏：6条产业链分列，纵向上游到下游，每个环节标注最相关的ETF联接基金代码，红点标注卡脖子环节。</desc>')
parts.append('<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5"/></marker></defs>')

# 标题
parts.append('<text class="th" x="40" y="26" style="font-size:16px">AI 产业链 · 网格拓扑图 × ETF 联接基金</text>')
parts.append('<text class="ts" x="40" y="44" style="font-size:10.5px">列＝产业链　纵向＝价值链（上游↑→下游↓）　每格＝该环节最相关 ETF 联接代码　<tspan style="fill:var(--color-danger)">●</tspan>＝卡脖子(建议打个股)</text>')

# 列
for ci, (title, cls, chips) in enumerate(cols):
    cx = X0 + ci * STEP
    mid = cx + W / 2
    # 列头
    parts.append(f'<g class="{cls}">')
    parts.append(f'<rect x="{cx}" y="{HEAD_Y}" width="{W}" height="{HEAD_H}" rx="7"/>')
    parts.append(f'<text class="th" x="{mid:.0f}" y="{HEAD_Y+19}" text-anchor="middle" style="font-size:11px">{esc(title)}</text>')
    parts.append('</g>')
    # 环节 chips
    for ri, (name, etf, kp) in enumerate(chips):
        cy = CHIP_Y0 + ri * CHIP_STEP
        parts.append(f'<g class="{cls}">')
        parts.append(f'<rect x="{cx}" y="{cy}" width="{W}" height="{CHIP_H}" rx="6"/>')
        parts.append(f'<text class="th" x="{mid:.0f}" y="{cy+13}" text-anchor="middle" style="font-size:9.8px">{esc(name)}</text>')
        parts.append(f'<text class="ts" x="{mid:.0f}" y="{cy+24}" text-anchor="middle" style="font-size:8px">{esc(etf)}</text>')
        parts.append('</g>')
        if kp:
            parts.append(f'<circle cx="{cx+7}" cy="{cy+7}" r="3.2" style="fill:var(--color-danger)"/>')

# 底部说明
fy = last_bottom + 22
parts.append(f'<text class="ts" x="40" y="{fy}" style="font-size:9.5px">核心配置：光通信 通信007817｜算力 半导体008887+材料设备019632｜PCB真β 电子001617｜应用 软件018385+人工智能012733+恒生013402</text>')
parts.append(f'<text class="ts" x="40" y="{fy+16}" style="font-size:9px" fill="var(--color-text-tertiary)">代码经 iFinD 基金库核实(2026-06，均为场外 ETF 联接，C 类约 A 类+1)。ETF 是一篮子，颗粒度低于个股，不构成投资建议。</text>')

parts.append('</svg>')
svg = "\n".join(parts)
open("_topo.svg", "w").write(svg)
print("H =", H, "maxchips =", maxchips, "bytes =", len(svg))
