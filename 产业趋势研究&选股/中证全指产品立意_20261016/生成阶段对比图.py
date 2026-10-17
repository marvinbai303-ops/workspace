"""用已核验的 iFinD 全A点位和中证官网历史行情生成 PPT 图表。"""

import csv
import datetime as dt
import math
import statistics
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
OFFICIAL = BASE / "中证官网_月度指数行情_202001_202610.csv"
IFIND_PRICE = ROOT / "全A指数行情.xlsx"
IFIND_TURNOVER = BASE / "iFinD_月度对照_202401_202610.csv"
MONTHS = [r for r in csv.DictReader(OFFICIAL.open(encoding="utf-8")) if r["month"] <= "202609"]


def all_a_monthly_close():
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = {}
    with zipfile.ZipFile(IFIND_PRICE) as z:
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        for row in root.findall(".//x:sheetData/x:row", ns)[2:]:
            cells = {}
            for c in row.findall("x:c", ns):
                v = c.find("x:v", ns)
                if v is not None:
                    cells[c.attrib["r"][0]] = v.text
            if "A" in cells and "B" in cells:
                day = dt.datetime(1899, 12, 30) + dt.timedelta(days=int(float(cells["A"])))
                values[day.strftime("%Y%m")] = float(cells["B"])
    return values


ALL_A = all_a_monthly_close()
for row in MONTHS:
    assert row["month"] in ALL_A, row["month"]


def episodes(is_up):
    groups, current = [], []
    for i in range(1, len(MONTHS)):
        if is_up(i):
            current.append(i)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


VOLUME_GROUPS = episodes(
    lambda i: float(MONTHS[i]["csi_avg_turnover_yi"])
    > float(MONTHS[i - 1]["csi_avg_turnover_yi"])
)
VOLUME_EVENTS = []
for e in VOLUME_GROUPS:
    b, z = MONTHS[e[0] - 1], MONTHS[e[-1]]
    VOLUME_EVENTS.append(
        dict(
            baseline_month=b["month"],
            start_month=MONTHS[e[0]]["month"],
            end_month=z["month"],
            months=len(e),
            turnover_change_pct=100 * (float(z["csi_avg_turnover_yi"]) / float(b["csi_avg_turnover_yi"]) - 1),
            csi_change_pct=100 * (float(z["csi_close"]) / float(b["csi_close"]) - 1),
        )
    )

SECTORS = [
    ("半导体", "semiconductor_close"),
    ("新能源", "newenergy_close"),
    ("医药", "healthcare_close"),
    ("黄金股*", "gold_close"),
    ("港股通50*", "hkconnect50_rmb_close"),
    ("光通信**", "optical_close"),
]
RALLY_GROUPS = episodes(
    lambda i: ALL_A[MONTHS[i]["month"]] > ALL_A[MONTHS[i - 1]["month"]]
)
RALLY_EVENTS = []
for e in RALLY_GROUPS:
    b, z = MONTHS[e[0] - 1], MONTHS[e[-1]]
    out = dict(
        baseline_month=b["month"],
        start_month=MONTHS[e[0]]["month"],
        end_month=z["month"],
        months=len(e),
        all_a_change_pct=100 * (ALL_A[z["month"]] / ALL_A[b["month"]] - 1),
        csi_change_pct=100 * (float(z["csi_close"]) / float(b["csi_close"]) - 1),
    )
    for name, key in SECTORS:
        # 光通信指数于2023-10-31发布；之前的官网回溯值不作可投资比较。
        out[key.replace("_close", "_change_pct")] = (
            None
            if key == "optical_close" and b["month"] < "202310"
            else 100 * (float(z[key]) / float(b[key]) - 1)
        )
    available = [out[k.replace("_close", "_change_pct")] for _, k in SECTORS]
    out["weakest_sector_gap_pp"] = out["csi_change_pct"] - min(v for v in available if v is not None)
    RALLY_EVENTS.append(out)


def save_table(name, data):
    with (BASE / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, data[0].keys())
        writer.writeheader()
        for row in data:
            writer.writerow({k: "" if v is None else round(v, 4) if isinstance(v, float) else v for k, v in row.items()})


save_table("成交回暖事件_2020至2026.csv", VOLUME_EVENTS)
save_table("全A上涨阶段_赛道对比_2020至2026.csv", RALLY_EVENTS)


# 16:9 的 2400×1350 位图，可直接插入 PPT。
W, H = 2400, 1350
S = 2
BG = "#F7F9FC"
NAVY = "#17324D"
BLUE = "#3D739C"
RED = "#BD463C"
TEAL = "#318C82"
INK = "#25384B"
MUTED = "#637588"
GRID = "#DCE5EC"
LIGHT = "#EAF0F5"
FONT = "/System/Library/Fonts/STHeiti Light.ttc"
BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"


class Canvas:
    def __init__(self):
        self.im = Image.new("RGB", (W * S, H * S), BG)
        self.d = ImageDraw.Draw(self.im)

    def font(self, n, bold=False):
        return ImageFont.truetype(BOLD if bold else FONT, int(n * S))

    def text(self, xy, value, size=26, color=INK, bold=False, anchor="la"):
        self.d.text(tuple(int(x * S) for x in xy), str(value), font=self.font(size, bold), fill=color, anchor=anchor)

    def rect(self, xy, fill, radius=0, outline=None, width=1):
        self.d.rounded_rectangle(tuple(int(x * S) for x in xy), radius=int(radius * S), fill=fill, outline=outline, width=width * S)

    def line(self, xy, fill=GRID, width=1):
        self.d.line(tuple(int(x * S) for x in xy), fill=fill, width=width * S)

    def save(self, name):
        self.im.resize((W, H), Image.Resampling.LANCZOS).save(BASE / name, optimize=True)


def label_period(row):
    a, b = row["start_month"], row["end_month"]
    return f"{a[:4]}.{a[4:]}" if a == b else f"{a[:4]}.{a[4:]}—{b[4:] if a[:4] == b[:4] else b[:4]+'.'+b[4:]}"


def pct(x):
    return f"{x:+.1f}%"


c = Canvas()
c.text((100, 82), "成交回暖的 17 轮：中证全指 14 轮同期上涨", 54, NAVY, True)
c.text((100, 137), "2020.02—2026.09 ｜ 以中证全指样本月均日成交额连续环比上升定义回暖", 28, MUTED)
c.line((100, 181, 2300, 181), GRID, 2)
c.text((100, 225), "回暖区间", 27, INK, True)
c.text((600, 225), "样本成交额较基期月增幅", 27, INK, True)
c.text((1450, 225), "同期中证全指涨跌幅", 27, INK, True)
c.line((1510, 251, 1510, 1183), "#AABBC8", 2)
for j, row in enumerate(VOLUME_EVENTS):
    y = 272 + j * 53
    if j % 2 == 0:
        c.rect((88, y - 18, 2310, y + 33), "#FFFFFF", 9)
    c.text((100, y + 6), label_period(row), 23, INK, False, "lm")
    tv = row["turnover_change_pct"]
    c.rect((600, y - 10, 600 + min(tv, 250) / 250 * 675, y + 14), BLUE, 4)
    c.text((1310, y + 6), pct(tv), 22, BLUE, True, "rm")
    ret = row["csi_change_pct"]
    end = 1510 + ret / 30 * 700 if ret >= 0 else 1510 + ret / 10 * 340
    c.rect((min(1510, end), y - 10, max(1510, end), y + 14), RED if ret >= 0 else TEAL, 4)
    anchor = "lm" if ret >= 0 else "rm"
    x_text = min(2245, end + 14) if ret >= 0 else max(1155, end - 14)
    c.text((x_text, y + 6), pct(ret), 22, RED if ret >= 0 else TEAL, True, anchor)
c.line((100, 1208, 2300, 1208), GRID, 2)
c.text((100, 1244), "注：2026.10 非完整月未纳入。成交额为中证全指样本证券成交额，不等同全 A 全部股票成交额。", 21, MUTED)
c.text((100, 1277), "数据：中证指数官网 000985 历史行情；已与 iFinD 同花顺全 A 成交额在 2024.01—2026.09 的方向逐月核对。", 21, MUTED)
c.text((100, 1310), "同期相关不代表可用成交额事先预测涨跌；负例为 2022.03、2023.10—11、2026.03—05。", 21, MUTED)
c.save("图1_成交回暖与中证全指_2020至2026.png")


def heat_color(v):
    if v is None:
        return "#E9EDF1", MUTED
    power = min(abs(v) / 60, 1)
    if v >= 0:
        rgb = tuple(round(255 * (1 - power) + z * power) for z in (201, 78, 69))
    else:
        rgb = tuple(round(255 * (1 - power) + z * power) for z in (56, 139, 129))
    return "#%02x%02x%02x" % rgb, "#FFFFFF" if power > 0.55 else INK


def draw_rally_page(years, title, filename):
    rows = [r for r in RALLY_EVENTS if r["start_month"][:4] in years]
    c = Canvas()
    c.text((100, 82), title, 53, NAVY, True)
    c.text((100, 136), "按 iFinD 同花顺全 A 连续上涨月定义区间 ｜ 单元格为同期价格指数涨跌幅", 27, MUTED)
    c.line((100, 181, 2300, 181), GRID, 2)
    headers = ["全 A", "中证全指", "半导体", "新能源", "医药", "黄金股*", "港股通50*", "光通信**", "最弱差距"]
    xs = [335, 505, 720, 930, 1140, 1350, 1560, 1770, 1980]
    widths = [150, 190, 190, 190, 190, 190, 190, 190, 240]
    c.text((100, 245), "上涨区间", 26, INK, True)
    for x, h in zip(xs, headers):
        c.text((x + 8, 245), h, 24, INK, True)
    top = 294
    height = 102 if len(rows) <= 7 else 92
    for j, r in enumerate(rows):
        y = top + j * height
        c.rect((88, y - 10, 2310, y + height - 13), "#FFFFFF", 12)
        c.text((100, y + (height - 23) / 2), label_period(r), 24, INK, True, "lm")
        vals = [r["all_a_change_pct"], r["csi_change_pct"]]
        vals += [r[k.replace("_close", "_change_pct")] for _, k in SECTORS]
        vals += [r["weakest_sector_gap_pp"]]
        for i, (x, width, v) in enumerate(zip(xs, widths, vals)):
            if i == 1:
                fill, color = NAVY, "#FFFFFF"
            elif i == 0:
                fill, color = LIGHT, INK
            elif i == 8:
                fill, color = "#FFF1DE", "#8E5718"
            else:
                fill, color = heat_color(v)
            c.rect((x, y + 9, x + width - 16, y + height - 32), fill, 10)
            value = "未发布" if v is None else f"{v:+.{2 if 0 < abs(v) < 0.05 else 1}f}{'pp' if i == 8 else '%'}"
            c.text((x + (width - 16) / 2, y + (height - 23) / 2), value, 23, color, i in (1, 8), "mm")
    foot_y = 1130
    c.line((100, foot_y, 2300, foot_y), GRID, 2)
    c.text((100, foot_y + 40), "* 黄金股为沪深港黄金产业股票指数（含港股），港股通50为人民币价格指数；两者与 A 股行业指数市场范围不同。", 21, MUTED)
    c.text((100, foot_y + 74), "** 光通信为 CPO 相关产业代理，指数 2023.10.31 发布；发布前历史回溯值不参与比较。", 21, MUTED)
    c.text((100, foot_y + 108), "最弱差距 = 中证全指收益率 − 本页所列可用赛道中最低收益率；仅反映事后选错赛道的样本代价。", 21, MUTED)
    c.text((100, foot_y + 142), "数据：iFinD 同花顺全 A 700001.TI；中证指数官网 000985、931865、930771、000991、931238、930934、931723。", 20, MUTED)
    c.save(filename)


draw_rally_page({"2020", "2021"}, "市场上涨时，押错赛道可能错过反弹｜2020—2021", "图2A_赛道轮动_2020至2021.png")
draw_rally_page({"2022", "2023"}, "市场上涨时，押错赛道可能错过反弹｜2022—2023", "图2B_赛道轮动_2022至2023.png")
draw_rally_page({"2024", "2025", "2026"}, "市场上涨时，押错赛道可能错过反弹｜2024—2026", "图2C_赛道轮动_2024至2026.png")


# 与 iFinD 全A成交额核对趋势，不用这一核对结果筛选事件。
ifind = {r["month"]: float(r["allA_avg_daily_turnover_trillion_cny"]) * 10000 for r in csv.DictReader(IFIND_TURNOVER.open(encoding="utf-8")) if r["month"] <= "202609"}
overlap = [r for r in MONTHS if r["month"] in ifind]
off = [float(r["csi_avg_turnover_yi"]) for r in overlap]
ia = [ifind[r["month"]] for r in overlap]
off_dir = [off[i] > off[i - 1] for i in range(1, len(off))]
ia_dir = [ia[i] > ia[i - 1] for i in range(1, len(ia))]
print({
    "volume_events": len(VOLUME_EVENTS),
    "volume_csi_up": sum(r["csi_change_pct"] > 0 for r in VOLUME_EVENTS),
    "all_a_up_episodes": len(RALLY_EVENTS),
    "csi_up_during_all_a_up": sum(r["csi_change_pct"] > 0 for r in RALLY_EVENTS),
    "sector_negative_during_all_a_up": sum(any(r[k.replace("_close", "_change_pct")] is not None and r[k.replace("_close", "_change_pct")] < 0 for _, k in SECTORS) for r in RALLY_EVENTS),
    "turnover_overlap_months": len(overlap),
    "turnover_direction_agreement": sum(a == b for a, b in zip(off_dir, ia_dir)),
    "turnover_level_correlation": statistics.correlation(off, ia),
    "turnover_change_correlation": statistics.correlation([off[i] / off[i - 1] - 1 for i in range(1, len(off))], [ia[i] / ia[i - 1] - 1 for i in range(1, len(ia))]),
})
