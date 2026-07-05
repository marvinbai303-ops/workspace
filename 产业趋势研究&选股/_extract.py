# -*- coding: utf-8 -*-
"""按视频号抽取完整正文到分桶文件,供深度卡精读。只读不改原稿。
用法: python3 _extract.py 桶名 视频号列表(逗号分隔)
例:   python3 _extract.py 光 1,6,10,16,...
"""
import re, sys

src = "scraper/output/合并转写稿.md"
text = open(src, encoding="utf-8").read()
blocks = re.split(r'(?m)^### 视频 (\d+)\s*$', text)
data = {}
for i in range(1, len(blocks), 2):
    data[int(blocks[i])] = blocks[i+1] if i+1 < len(blocks) else ""

def field(body, key):
    m = re.search(r'- %s[：:]\s*(.*)' % re.escape(key), body)
    return m.group(1).strip() if m else ""

bucket = sys.argv[1]
nums = [int(x) for x in sys.argv[2].split(",")]
out = "_full_%s.md" % bucket
with open(out, "w", encoding="utf-8") as f:
    for n in nums:
        body = data.get(n, "")
        title = field(body, "标题/主题")
        date = field(body, "发布日期")
        m = re.search(r'- 转写正文[：:]\s*\n?(.*)', body, re.S)
        raw = (m.group(1) if m else "").strip()
        f.write(f"### V{n} | {date} | {title}\n{raw}\n\n---\n\n")
total = sum(len(re.search(r'- 转写正文[：:]\s*\n?(.*)', data.get(n,""), re.S).group(1)) for n in nums if re.search(r'- 转写正文[：:]\s*\n?(.*)', data.get(n,""), re.S))
print(f"wrote {out}: {len(nums)} videos, ~{total:,} chars")
