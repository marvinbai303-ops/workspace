from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pandas as pd


WORKSPACE = Path("/Users/yangguang/Documents/Codex/workspace/样板间投顾组合")
SOURCE = WORKSPACE / "净值序列1.xls"
OUTPUT_DIR = WORKSPACE / "outputs/20260820-1090-repair"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

NAME_MAP = {
    "003504.OF": "景顺长城景颐丰利债券", "000143.OF": "鹏华双债加利债券",
    "000385.OF": "景顺长城景颐双利债券", "002065.OF": "景顺长城景盛双息收益债券",
    "002969.OF": "易方达丰和债券", "014088.OF": "永赢稳健增强债券",
    "001751.OF": "华商信用增强债券", "014846.OF": "博时恒乐债券",
    "000171.OF": "易方达裕丰回报债券", "202101.OF": "南方宝元债券",
    "470010.OF": "汇添富多元收益债券", "000406.OF": "汇添富双利增强债券",
    "018595.OF": "华商利欣回报债券", "020218.OF": "万家锦利债券发起式",
}

SCALE_MAP = {
    "003504.OF": 712, "000143.OF": 584, "000385.OF": 576, "002065.OF": 393,
    "002969.OF": 391, "014088.OF": 365, "001751.OF": 361, "014846.OF": 359,
    "000171.OF": 342, "202101.OF": 314, "000406.OF": 293, "018595.OF": 283,
    "470010.OF": 274, "020218.OF": 180,
}

RED = "#9E0000"; LEADER = "#0B8F78"; TEXT = "#172033"; MUTED = "#667085"
GRID = "#D9DEE7"; PEER = "#B7BEC9"; BORDER = "#98A2B3"; HEADER = "#EEF2F7"; HI = "#FFF2F0"
POS = "#C2413B"; NEG = "#13856A"

def font(size):
    return ImageFont.truetype(FONT_PATH, size=size)

F54 = font(54); F31 = font(31); F26 = font(26); F24 = font(24); F22 = font(22); F20 = font(20); F18 = font(18)

def pct(v, d=2):
    return f"{v * 100:,.{d}f}%"

def text_center(draw, xy, text, fnt, fill):
    draw.text(xy, text, font=fnt, fill=fill, anchor="mm")

def load_group(sheet_name):
    raw = pd.read_excel(SOURCE, sheet_name=sheet_name, engine="openpyxl")
    raw.iloc[:, 0] = pd.to_datetime(raw.iloc[:, 0])
    raw = raw[(raw.iloc[:, 0] >= "2026-06-18") & (raw.iloc[:, 0] <= "2026-08-18")].copy()
    selected = pd.concat([raw.iloc[:, [0, 2]], raw.iloc[:, 3:13]], axis=1)
    selected.columns = ["date", "1090", *[str(c) for c in raw.columns[3:13]]]
    nav = selected.set_index("date").apply(pd.to_numeric, errors="coerce")
    normalized = nav.divide(nav.iloc[0])
    rows = []
    for code in nav.columns:
        s = nav[code].dropna()
        n = s / s.iloc[0]
        established = s.iloc[-1] / s.iloc[0] - 1
        max_drawdown = (n / n.cummax() - 1).min()
        distance = s.iloc[-1] / s.max() - 1
        rebound = s.iloc[-1] / s.min() - 1
        repair = rebound / abs(max_drawdown) if abs(max_drawdown) > 1e-12 else np.inf
        rows.append({
            "code": code, "name": "1090组合" if code == "1090" else NAME_MAP.get(code, code),
            "established": established, "max_drawdown": max_drawdown, "distance": distance,
            "rebound": rebound, "repair": repair, "scale": SCALE_MAP.get(code),
        })
    metrics = pd.DataFrame(rows)
    return normalized, metrics

def draw_frame(draw, box):
    draw.rectangle(box, outline=BORDER, width=2, fill="#FFFFFF")

def draw_rotated_label(img, xy, text, angle=68):
    label = Image.new("RGBA", (120, 34), (255, 255, 255, 0))
    ld = ImageDraw.Draw(label)
    ld.text((60, 17), text, font=F18, fill=MUTED, anchor="mm")
    label = label.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    img.paste(label, (int(xy[0] - label.width / 2), int(xy[1])), label)


def wrap_name(name):
    if len(name) <= 10:
        return name
    split = (len(name) + 1) // 2
    return name[:split] + "\n" + name[split:]


def render_group(sheet_name, group_title, file_name):
    nav, metrics = load_group(sheet_name)
    table_rows = pd.concat([
        metrics[metrics.code == "1090"],
        metrics[metrics.code != "1090"].sort_values("scale", ascending=False),
    ], ignore_index=True)

    img = Image.new("RGB", (2560, 1440), "white")
    draw = ImageDraw.Draw(img)

    # Header copied from the reference composition.
    draw.rectangle((70, 58, 152, 140), fill=RED)
    text_center(draw, (111, 99), "2.5", F31, "#FFFFFF")
    draw.text((175, 57), "账户思维落地示范：以1090账户样板间为例", font=F54, fill=RED)
    draw.line((110, 174, 2445, 174), fill=RED, width=6)

    text_center(draw, (720, 245), "净值走势", F31, TEXT)
    text_center(draw, (1945, 245), "回撤与修复统计", F31, TEXT)

    # Left: only 1090 is red; all comparison funds use the same gray.
    px0, py0, px1, py1 = 145, 315, 1330, 1110
    vals = nav.to_numpy(dtype=float)
    ymin = np.floor((np.nanmin(vals) - 0.01) * 100) / 100
    ymax = np.ceil((np.nanmax(vals) + 0.01) * 100) / 100
    def sx(i): return px0 + i * (px1 - px0) / (len(nav.index) - 1)
    def sy(v): return py1 - (v - ymin) * (py1 - py0) / (ymax - ymin)
    for i in range(7):
        yv = ymin + (ymax - ymin) * i / 6
        yy = sy(yv)
        draw.line((px0, yy, px1, yy), fill="#D6D6D6", width=1)
        label = f"{yv:.2f}".rstrip("0").rstrip(".")
        draw.text((px0 - 22, yy), label, font=F18, fill="#555555", anchor="rm")
    for code in nav.columns:
        if code == "1090":
            continue
        draw.line([(sx(i), sy(v)) for i, v in enumerate(nav[code].to_numpy())], fill="#AEB4BE", width=2)
    draw.line([(sx(i), sy(v)) for i, v in enumerate(nav["1090"].to_numpy())], fill="#C00000", width=6)
    for idx in range(0, len(nav.index), 2):
        xx = sx(idx)
        draw.line((xx, py1, xx, py1 + 6), fill="#C8CDD4", width=1)
        draw_rotated_label(img, (xx, py1 + 10), nav.index[idx].strftime("%Y/%-m/%-d"))
    draw.line((430, 1265, 490, 1265), fill="#C00000", width=6)
    draw.text((505, 1265), "10-90账户", font=F24, fill="#555555", anchor="lm")
    draw.line((735, 1265, 795, 1265), fill="#AEB4BE", width=3)
    draw.text((810, 1265), "对照组基金", font=F24, fill="#555555", anchor="lm")

    # Right: 1090 first, remaining funds sorted by Q2 scale descending.
    tx0, ty0 = 1420, 315
    widths = [260, 135, 150, 150, 180, 195]
    headers = ["组合/基金", "Q2规模\n（亿元）", "成立以来*", "最大回撤", "离最高点\n的距离", "累计修复\n幅度"]
    header_h, row_h = 90, 70
    x = tx0
    for w, header in zip(widths, headers):
        draw.rectangle((x, ty0, x + w, ty0 + header_h), fill="#F0F3F7", outline="#111111", width=2)
        draw.multiline_text((x + w / 2, ty0 + header_h / 2), header, font=F22, fill="#344054", anchor="mm", align="center", spacing=4)
        x += w
    for ri, row in table_rows.iterrows():
        y0 = ty0 + header_h + ri * row_h
        fill = "#F3F6FA" if row.code == "1090" else "#FFFFFF"
        name = "10-90样板间\n组合" if row.code == "1090" else wrap_name(row["name"])
        values = [
            name,
            "—" if row.code == "1090" else f"{int(row['scale'])}",
            pct(row.established),
            pct(row.max_drawdown),
            pct(row.distance),
            pct(row.repair, 1 if row.code == "1090" else 2),
        ]
        x = tx0
        for ci, (w, value) in enumerate(zip(widths, values)):
            draw.rectangle((x, y0, x + w, y0 + row_h), fill=fill, outline="#111111", width=2)
            if ci == 0:
                color = "#2563EB" if row.code == "1090" else "#13856A"
            elif ci == 4:
                color = "#00A3E0"
            elif ci == 5:
                color = "#C00000"
            else:
                color = "#13856A" if ci in (2, 3) else "#344054"
            draw.multiline_text((x + w / 2, y0 + row_h / 2), value, font=F18, fill=color, anchor="mm", align="center", spacing=1)
            x += w

    draw.text((100, 1370), "业绩数据来源： 嘉实财富； 数据区间为6.18-8.18。10-90样板间组合与产业趋势组合的成立时间为6.18。", font=F20, fill="#667085")
    output = OUTPUT_DIR / file_name
    img.save(output, quality=95)
    return output, table_rows

outputs = [
    render_group("全市场前十", "全市场Q2规模前十固收+", "1090_vs_全市场Q2规模前十固收+_净值修复分析.png"),
    render_group("全市场增长前十", "全市场Q2规模增长前十固收+", "1090_vs_全市场Q2规模增长前十固收+_净值修复分析.png"),
]
for output, metrics in outputs:
    print(output)
    print(metrics[["name", "code", "scale", "established", "max_drawdown", "distance", "rebound", "repair"]].to_string(index=False))
