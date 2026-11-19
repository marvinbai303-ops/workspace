import csv
import html
import math
from pathlib import Path


BASE = Path(__file__).resolve().parent
rows = list(csv.DictReader((BASE / "iFinD_月度对照_202401_202610.csv").open(encoding="utf-8")))
rows = [r for r in rows if r["month"] <= "202609"]


def f(row, key):
    return float(row[key])


def corr(xs, ys):
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    xx = sum((x - mx) ** 2 for x in xs)
    yy = sum((y - my) ** 2 for y in ys)
    return xy / math.sqrt(xx * yy)


def comp(months, key):
    values = [f(r, key) for r in rows if r["month"] in months]
    return 100 * (math.prod(1 + v / 100 for v in values) - 1)


W, H = 1600, 880
navy = "#16324F"
blue = "#3478A8"
orange = "#DA6A44"
teal = "#24927F"
light = "#E5EBF0"
gray = "#637381"
els = []


def add(s):
    els.append(s)


def txt(x, y, value, size=22, color=navy, weight=400, anchor="start"):
    add(
        f'<text x="{x}" y="{y}" fill="{color}" font-family="STHeiti, PingFang SC, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'
    )


def line(x1, y1, x2, y2, color=light, width=1, dash=""):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{dash_attr}/>')


def rect(x, y, w, h, fill, radius=0):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
rect(0, 0, W, H, "#FFFFFF")
txt(76, 78, "全A成交活跃，不等于可预判的上涨", 38, navy, 700)
txt(76, 122, "全指的取舍：降低押错单一赛道的代价，也可能落后于最强赛道", 23, gray)
line(76, 148, 1524, 148, light, 2)

# Panel 1: month-level turnover versus return.
px, py, pw, ph = 110, 258, 600, 442
txt(78, 205, "全A：月度涨跌幅与日均成交额", 27, navy, 650)
txt(78, 239, "横轴：月内日均成交额（万亿元）", 18, gray)
xs = [f(r, "allA_avg_daily_turnover_trillion_cny") for r in rows]
ys = [f(r, "allA_return_pct") for r in rows]
rxy = corr(xs, ys)
txt(710, 206, f"相关系数  {rxy:.2f}", 22, gray, 600, "end")
xmin, xmax = 0.5, 3.35
ymin, ymax = -15, 25


def sx(v):
    return px + (v - xmin) / (xmax - xmin) * pw


def sy(v):
    return py + ph - (v - ymin) / (ymax - ymin) * ph


for y in [-15, -10, -5, 0, 5, 10, 15, 20, 25]:
    yy = sy(y)
    line(px, yy, px + pw, yy, "#CCD6DE" if y == 0 else light, 1.4 if y == 0 else 1)
    txt(px - 18, yy + 7, f"{y}%", 17, gray, 400, "end")
for x in [0.5, 1, 1.5, 2, 2.5, 3]:
    xx = sx(x)
    line(xx, py, xx, py + ph, light)
    txt(xx, py + ph + 30, f"{x:.1f}", 17, gray, 400, "middle")
colors = {"2024": blue, "2025": teal, "2026": orange}
for row in rows:
    x = sx(f(row, "allA_avg_daily_turnover_trillion_cny"))
    y = sy(f(row, "allA_return_pct"))
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.8" fill="{colors[row["month"][:4]]}" fill-opacity="0.82" stroke="#FFFFFF" stroke-width="1.5"/>')
for i, (year, color) in enumerate(colors.items()):
    cx = 136 + i * 115
    add(f'<circle cx="{cx}" cy="761" r="6" fill="{color}"/>')
    txt(cx + 14, 768, year, 18, gray)
line(790, 190, 790, 765, light, 2)

# Panel 2: preselected rotation example, compounded monthly returns.
txt(842, 205, "信息技术与医药：主线换挡的代价", 27, navy, 650)
txt(842, 239, "2026年第二、第三季度；月收益复利", 18, gray)
bx, by, bw, bh = 872, 286, 605, 414
vlo, vhi = -40, 80


def byv(v):
    return by + bh - (v - vlo) / (vhi - vlo) * bh


for y in [-40, -20, 0, 20, 40, 60, 80]:
    yy = byv(y)
    line(bx, yy, bx + bw, yy, "#A8B8C5" if y == 0 else light, 1.5 if y == 0 else 1)
    txt(bx - 20, yy + 6, f"{y}%", 17, gray, 400, "end")
groups = [
    ("2026年二季度", ["202604", "202605", "202606"]),
    ("2026年三季度", ["202607", "202608", "202609"]),
]
series = [
    ("全指信息", "csi_IT_return_pct", orange),
    ("全指医药", "csi_healthcare_return_pct", teal),
    ("中证全指", "csi_allshare_return_pct", navy),
]
for gi, (label, months) in enumerate(groups):
    center = 1052 + gi * 295
    for si, (name, key, color) in enumerate(series):
        value = comp(months, key)
        x = center - 85 + si * 70
        y0, y1 = byv(0), byv(value)
        rect(x, min(y0, y1), 47, abs(y0 - y1), color, 3)
        txt(x + 23.5, min(y0, y1) - 9 if value >= 0 else max(y0, y1) + 24,
            f"{value:+.1f}%", 18, color, 650, "middle")
    txt(center, by + bh + 45, label, 19, navy, 600, "middle")
for i, (name, key, color) in enumerate(series):
    x = 891 + i * 187
    rect(x, 766, 24, 10, color, 2)
    txt(x + 34, 779, name, 18, gray)

line(76, 810, 1524, 810, light)
txt(76, 840, "数据：同花顺 iFinD。全A为同花顺全A（加权）；行业指数与宽基均为价格指数。样本：2024年1月至2026年9月。", 17, gray)
txt(76, 865, "右图仅展示科技与医药轮动的案例，不代表全部行业；未计入分红、产品费率及交易成本。", 17, gray)
add("</svg>")
(BASE / "全A成交与行业轮动_证据图.svg").write_text("\n".join(els), encoding="utf-8")

# Render the same vector chart to PNG for easy insertion into presentations.
from xml.etree import ElementTree as ET
from PIL import Image, ImageColor, ImageDraw, ImageFont

scale = 2
canvas = Image.new("RGB", (W * scale, H * scale), "white")
draw = ImageDraw.Draw(canvas)
regular_font = "/System/Library/Fonts/STHeiti Light.ttc"
bold_font = "/System/Library/Fonts/STHeiti Medium.ttc"
root = ET.fromstring("\n".join(els))


def point(element, name):
    return float(element.attrib[name]) * scale


for element in root:
    kind = element.tag.rsplit("}", 1)[-1]
    if kind == "rect":
        xy = (point(element, "x"), point(element, "y"),
              point(element, "x") + point(element, "width"),
              point(element, "y") + point(element, "height"))
        draw.rounded_rectangle(
            xy,
            radius=float(element.attrib.get("rx", "0")) * scale,
            fill=element.attrib["fill"],
        )
    elif kind == "line":
        draw.line(
            (point(element, "x1"), point(element, "y1"),
             point(element, "x2"), point(element, "y2")),
            fill=element.attrib["stroke"],
            width=max(1, round(float(element.attrib.get("stroke-width", "1")) * scale)),
        )
    elif kind == "circle":
        x, y, radius = point(element, "cx"), point(element, "cy"), point(element, "r")
        rgb = ImageColor.getrgb(element.attrib["fill"])
        opacity = float(element.attrib.get("fill-opacity", "1"))
        fill = tuple(round(c * opacity + 255 * (1 - opacity)) for c in rgb)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill,
                     outline=element.attrib.get("stroke"),
                     width=max(1, round(float(element.attrib.get("stroke-width", "0")) * scale)))
    elif kind == "text":
        size = round(float(element.attrib["font-size"]) * scale)
        weight = int(element.attrib.get("font-weight", "400"))
        font = ImageFont.truetype(bold_font if weight >= 600 else regular_font, size)
        anchor = {"start": "ls", "middle": "ms", "end": "rs"}[
            element.attrib.get("text-anchor", "start")
        ]
        draw.text(
            (point(element, "x"), point(element, "y")),
            element.text or "",
            font=font,
            fill=element.attrib["fill"],
            anchor=anchor,
        )

canvas.resize((W, H), Image.Resampling.LANCZOS).save(
    BASE / "全A成交与行业轮动_证据图.png", optimize=True
)
