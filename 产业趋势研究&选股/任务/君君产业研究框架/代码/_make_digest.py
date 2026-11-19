# -*- coding: utf-8 -*-
"""把合并转写稿切成每条视频的紧凑摘要,便于建索引。只读不改原稿。"""
import re, json

src = "scraper/output/合并转写稿.md"
text = open(src, encoding="utf-8").read()

# 按 "### 视频 N" 切块
blocks = re.split(r'(?m)^### 视频 (\d+)\s*$', text)
# blocks[0]=前言; 之后 (num, body) 交替
pairs = []
for i in range(1, len(blocks), 2):
    num = int(blocks[i])
    body = blocks[i+1] if i+1 < len(blocks) else ""
    pairs.append((num, body))

def field(body, key):
    m = re.search(r'- %s[：:]\s*(.*)' % re.escape(key), body)
    return m.group(1).strip() if m else ""

# 关键词→产业链粗标签(用于覆盖面统计,后续人工修正)
TAGS = {
    "光模块/光通信": ["光模块","光波化","光波块","CPO","可插拔","硅光","光芯片","光引擎","光源","EML","DSP","旭创","新易盛","天孚","光通信","800G","1.6T","3.2T","CW激光"],
    "存储": ["存储","HBM","DRAM","NAND","美光","江波龙","澜起","德明利","颗粒","模组","闪存","SSD"],
    "先进封装": ["先进封装","CoWoS","2.5D","3D封装","盛合晶微","封装","Chiplet","HBM封装","混合键合"],
    "PCB/CCL": ["PCB","覆铜板","CCL","电子布","铜箔","沪电","生益","高频高速","载板"],
    "硅片/半导体材料": ["硅片","硅料","外延片","抛光片","SOI","立昂微","沪硅","退火片","12寸","8寸","晶圆"],
    "铜连接": ["铜连接","铜缆","高速铜","224G","112G","连接器","线缆"],
    "算力/GPU/芯片": ["GPU","英伟达","算力","ASIC","博通","台积电","制程","英特尔","Intel","DeepSeek","中芯","芯片","推理","训练"],
    "散热/电源": ["散热","液冷","电源","功耗","BBU","供电"],
    "方法论/复盘/宏观": ["方法论","复盘","仿真","景气","舆情","β","α","卡脖子","产融","映射","滞胀","美联储","组合","买方","颗粒度","拓扑","网格","应对"],
}

def autotags(s):
    hits = []
    for tag, kws in TAGS.items():
        c = sum(s.count(k) for k in kws)
        if c > 0:
            hits.append((tag, c))
    hits.sort(key=lambda x: -x[1])
    return hits

out = []
tally = {}
for num, body in pairs:
    title = field(body, "标题/主题")
    date = field(body, "发布日期")
    link = field(body, "链接")
    dur = field(body, "时长")
    # 正文 = "转写正文：" 之后的内容
    m = re.search(r'- 转写正文[：:]\s*\n?(.*)', body, re.S)
    raw = (m.group(1) if m else "").strip()
    nchar = len(raw)
    lead = raw[:320].replace("\n", " ")
    # 用 标题+lead 做粗标签
    tags = autotags(title + " " + raw[:1500])
    primary = tags[0][0] if tags else "未分类"
    tally[primary] = tally.get(primary, 0) + 1
    out.append({
        "num": num, "title": title, "date": date, "link": link,
        "dur_s": dur, "nchar": nchar,
        "primary": primary,
        "tags": [t for t, _ in tags[:3]],
        "lead": lead,
    })

# 写紧凑摘要(供我读入建索引)
with open("_digest.md", "w", encoding="utf-8") as f:
    f.write("# 视频摘要(自动抽取,供建索引)\n\n")
    f.write("## 粗标签覆盖统计\n")
    for tag, c in sorted(tally.items(), key=lambda x: -x[1]):
        f.write(f"- {tag}: {c} 条\n")
    f.write(f"\n总字数(正文): {sum(o['nchar'] for o in out):,}\n\n---\n\n")
    for o in out:
        f.write(f"### V{o['num']} | {o['date']} | {o['nchar']}字 | [{o['primary']}]\n")
        f.write(f"**{o['title']}**\n")
        f.write(f"标签:{'/'.join(o['tags'])} | {o['link']}\n")
        f.write(f"导语: {o['lead']}\n\n")

print("done. videos=%d" % len(out))
print("tally:", json.dumps(tally, ensure_ascii=False))
print("max_char video:", max(out, key=lambda o: o['nchar'])['num'], max(o['nchar'] for o in out))
