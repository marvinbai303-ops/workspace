from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1536
NAVY = (16, 47, 87)
BLUE = (23, 105, 194)
ACCENT = (46, 141, 230)
BODY = (86, 115, 143)
BG = (247, 251, 255)
WHITE = (255, 255, 255)
PALE = (234, 244, 255)
BORDER = (196, 221, 244)

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"

def f(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

def text(x, y, s, size, fill=NAVY, bold=False, anchor=None):
    d.text((x, y), s, font=f(size, bold), fill=fill, anchor=anchor)

def card(x, y, w, h, num, title, body, tag, accent):
    d.rounded_rectangle((x, y, x+w, y+h), radius=18, fill=WHITE, outline=BORDER, width=2)
    d.rounded_rectangle((x+22, y+25, x+92, y+73), radius=11, fill=accent)
    text(x+57, y+49, num, 27, WHITE, True, "mm")
    text(x+120, y+26, title, 28, NAVY, True)
    text(x+120, y+68, body, 23, BODY)
    text(x+120, y+h-28, tag, 18, BLUE)

# Header
d.rectangle((0, 0, W, 118), fill=NAVY)
d.rectangle((0, 112, W, 118), fill=ACCENT)
text(54, 37, "基金研究小组 ｜ 科技热点 · 市场底色", 31, WHITE, True)
text(965, 37, "2026.08.11", 27, WHITE, True, "ra")

# Hero
d.rounded_rectangle((44, 150, 980, 432), radius=22, fill=PALE, outline=(185, 217, 246), width=2)
text(72, 212, "英伟达把AI融资做到", 49, NAVY, True)
text(72, 272, "5000亿美元", 49, NAVY, True)
text(74, 333, "联手六大金融机构，为AI基础设施撬动第三方资本", 25, BODY)

# Hero icon: AI chip + network
d.rounded_rectangle((808, 266, 920, 346), radius=10, fill=(22, 86, 156))
d.rounded_rectangle((826, 282, 902, 330), radius=6, fill=(217, 239, 255))
d.line((786, 306, 808, 306), fill=ACCENT, width=8)
d.line((920, 306, 942, 306), fill=ACCENT, width=8)
d.line((864, 244, 864, 266), fill=ACCENT, width=8)
d.line((864, 346, 864, 368), fill=ACCENT, width=8)
d.line((828, 260, 848, 240), fill=ACCENT, width=7)
d.line((900, 260, 880, 240), fill=ACCENT, width=7)
d.line((828, 352, 848, 372), fill=ACCENT, width=7)
d.line((900, 352, 880, 372), fill=ACCENT, width=7)
d.ellipse((850, 300, 870, 320), fill=ACCENT)
d.ellipse((878, 300, 898, 320), fill=ACCENT)
d.line((870, 310, 878, 310), fill=WHITE, width=5)

text(54, 464, "热点速览", 30, NAVY, True)
d.rounded_rectangle((54, 493, 128, 498), radius=3, fill=ACCENT)

card(44, 525, 936, 145, "01", "英伟达开始为客户“找钱”", "超5000亿美元第三方资本将进入AI基础设施，芯片供应商开始参与资本组织。", "英伟达｜华尔街｜AI基础设施", NAVY)
card(44, 691, 936, 145, "02", "英特尔拟募资150亿美元扩建代工", "AI基础设施融资潮继续外溢，芯片制造也开始争夺长期资本。", "英特尔｜晶圆代工｜资本开支", BLUE)
card(44, 857, 936, 145, "03", "亚马逊德州AI数据中心配7.65GW电厂", "35台燃气轮机自供电，AI算力扩张开始直接重塑能源与环保议题。", "数据中心｜能源｜环保", NAVY)
card(44, 1023, 936, 145, "04", "FCC拟限制中国光模块", "据报道，可能年内推出；AI数据中心互联器件进入安全审查。", "监管｜光通信｜AI基础设施", BLUE)
card(44, 1189, 936, 145, "05", "AI安全开始影响模型发布节奏", "OpenAI内部评估Astra网络能力可能达“关键”级别，发布让位于安全测试。", "大模型｜网络安全｜产品节奏", NAVY)

# Market bottom panel
d.rounded_rectangle((44, 1360, 980, 1484), radius=18, fill=NAVY)
text(68, 1378, "市场底色", 24, WHITE, True)
text(68, 1412, "海外流动性：联储维持3.50%—3.75%，利率路径仍在拉锯", 17, WHITE)
text(68, 1437, "地缘与大类资产：霍尔木兹谈判反复，油金汇继续交易避险与通胀", 17, WHITE)
text(68, 1462, "国内政策：政治局强调积极财政、适度宽松，并谋划增量政策", 17, (143, 200, 255))

text(512, 1510, "本期基于公开报道整理｜仅作信息分享", 16, BODY, False, "ma")

img.save("科技温度计_初稿_20260811.png", optimize=True)
