#!/usr/bin/env python3
"""Rebuild a source-limited PCLI-Beta interval and compare it with 885573.TI.

Only Python standard library and Pillow are required. Run from any directory.
"""

from __future__ import annotations

import csv
import math
import argparse
import calendar
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


parser = argparse.ArgumentParser()
parser.add_argument("--snapshot", default="2026-10-20", help="YYYY-MM-DD data snapshot")
args = parser.parse_args()
AS_OF = date.fromisoformat(args.snapshot)
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / args.snapshot
OUT = ROOT / "outputs" / args.snapshot
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(name):
    with (RAW / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def month_key(value):
    return value[:7]


def month_no(value):
    return int(value[:4]) * 12 + int(value[5:7]) - 1


def month_from_no(value):
    return f"{value // 12:04d}-{value % 12 + 1:02d}"


def score(growth_pct, scale_pct):
    return max(0.0, min(100.0, 50.0 - 50.0 * growth_pct / scale_pct))


def growth(current, earlier):
    return 100.0 * (current / earlier - 1.0)


release_dates = {}
if (RAW / "release_dates.csv").exists():
    release_dates = {(r["indicator_id"], month_key(r["observation_date"])):
                     date.fromisoformat(r["first_public_date"])
                     for r in read_csv("release_dates.csv")}


def choose_latest(scores, as_of, max_age, indicator_id):
    day = AS_OF if as_of == AS_OF.strftime("%Y-%m") else date(
        int(as_of[:4]), int(as_of[5:7]), calendar.monthrange(int(as_of[:4]), int(as_of[5:7]))[1])
    eligible = [(m, x) for m, x in scores.items()
                if (release_dates[(indicator_id, m)] <= day
                    if (indicator_id, m) in release_dates
                    else month_no(m) + 2 <= month_no(as_of))
                and month_no(as_of) - month_no(m) <= max_age]
    return max(eligible, key=lambda x: month_no(x[0])) if eligible else (None, None)


def fmt(value, digits=2):
    return "" if value is None else f"{value:.{digits}f}"


index_rows = read_csv("885573_monthly.csv")
index = {r["month"]: float(r["close"]) for r in index_rows}
index_status = {r["month"]: r["period_status"] for r in index_rows}
sow = {month_key(r["date"]): float(r["value"]) for r in read_csv("sow.csv")}
stock = {month_key(r["date"]): float(r["value"]) for r in read_csv("stock.csv")}
slaughter = {r["month"]: float(r["value"]) for r in read_csv("slaughter.csv")}
weight_weeks = {}
for row in read_csv("weight.csv"):
    weight_weeks.setdefault(month_key(row["date"]), []).append(float(row["value"]))
weight = {m: sum(values) / len(values) for m, values in weight_weeks.items()}


def year_prior(month):
    return month_from_no(month_no(month) - 12)


def six_month_prior(month):
    return month_from_no(month_no(month) - 6)


# Frozen, theory-led mapping: 50 points = flat supply; contraction raises score.
# Cutoffs are chosen before comparison with equity returns and are not calibrated.
sow_scores = {}
for m, value in sow.items():
    prior_y, prior_6m = sow.get(year_prior(m)), sow.get(six_month_prior(m))
    if prior_y is not None and prior_6m is not None:
        sow_scores[m] = (score(growth(value, prior_y), 8.0)
                         + score(growth(value, prior_6m), 5.0)) / 2.0

stock_scores = {m: score(growth(v, stock[year_prior(m)]), 15.0)
                for m, v in stock.items() if year_prior(m) in stock}
slaughter_scores = {m: score(growth(v, slaughter[year_prior(m)]), 20.0)
                      for m, v in slaughter.items() if year_prior(m) in slaughter}
weight_scores = {m: score(growth(v, weight[year_prior(m)]), 10.0)
                 for m, v in weight.items() if year_prior(m) in weight}


rows = []
for month in sorted(index):
    sow_m, sow_s = choose_latest(sow_scores, month, 6, "S002841992")
    stock_m, stock_s = choose_latest(stock_scores, month, 6, "S002841991")
    slaughter_m, slaughter_s = choose_latest(slaughter_scores, month, 3, "S002841990")
    weight_m, weight_s = choose_latest(weight_scores, month, 2, "S004320910")
    near_values = [x for x in (stock_s, slaughter_s) if x is not None]
    near_s = sum(near_values) / len(near_values) if near_values else None

    known = sum(w * x for w, x in [(0.45, sow_s), (0.20, near_s), (0.10, weight_s)]
                if x is not None)
    coverage = sum(w for w, x in [(0.45, sow_s), (0.20, near_s), (0.10, weight_s)]
                   if x is not None)
    # No public, continuous national newborn-piglet quantity series was retrieved.
    # Unknown modules are bounded at 0-100, never imputed as a measured score.
    lower = known if coverage >= 0.65 else None
    upper = known + 100.0 * (1.0 - coverage) if lower is not None else None
    midpoint = (lower + upper) / 2.0 if lower is not None else None
    rows.append({
        "month": month,
        "index_close": index[month],
        "index_period_status": ("partial_through_" + index_status[month]
                                if len(index_status[month]) == 10 else index_status[month]),
        "sow_observation_month": sow_m or "",
        "sow_release_date": (str(release_dates.get(("S002841992", sow_m), "")) if sow_m else ""),
        "sow_score": sow_s,
        "stock_observation_month": stock_m or "",
        "stock_release_date": (str(release_dates.get(("S002841991", stock_m), "")) if stock_m else ""),
        "stock_score": stock_s,
        "slaughter_observation_month": slaughter_m or "",
        "slaughter_score": slaughter_s,
        "effective_supply_score": near_s,
        "weight_observation_month": weight_m or "",
        "weight_score": weight_s,
        "piglet_score": None,
        "known_weight": coverage,
        "pcli_lower": lower,
        "pcli_upper": upper,
        "pcli_interval_midpoint_not_measured": midpoint,
    })

fields = list(rows[0])
with (OUT / "pcli_vs_885573_monthly.csv").open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: fmt(v, 4) if isinstance(v, float) else ("" if v is None else v)
                         for k, v in row.items()})


# Standalone research figure. Panels share the calendar axis to avoid a misleading
# two-scale overlay, and the interval is shown rather than an invented exact PCLI.
W, H, S = 1700, 1120, 2
im = Image.new("RGB", (W * S, H * S), "#F7F8FA")
draw = ImageDraw.Draw(im)
font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def font(size):
    return ImageFont.truetype(font_path, size * S)


def xy(*numbers):
    return tuple(round(n * S) for n in numbers)


def line(points, color, width=2, joint="curve"):
    draw.line([(round(x * S), round(y * S)) for x, y in points],
              fill=color, width=width * S, joint=joint)


def text_at(point, text, fill, size=20, anchor=None):
    draw.text(xy(*point), text, font=font(size), fill=fill, anchor=anchor)


left, right = 135, 1570
top1, bottom1 = 190, 530
top2, bottom2 = 665, 980
visible = [r for r in rows if r["month"] >= "2022-11"]
first_no, last_no = month_no(visible[0]["month"]), month_no(visible[-1]["month"])
xcoord = lambda m: left + (month_no(m) - first_no) / (last_no - first_no) * (right - left)
index_min = math.floor(min(r["index_close"] for r in visible) / 250) * 250
index_max = math.ceil(max(r["index_close"] for r in visible) / 250) * 250
y_index = lambda v: bottom1 - (v - index_min) / (index_max - index_min) * (bottom1 - top1)
y_pcli = lambda v: bottom2 - v / 100.0 * (bottom2 - top2)

draw.rounded_rectangle(xy(70, 125, 1630, 1035), radius=24 * S, fill="white")
text_at((82, 42), "PCLI-Beta 可识别区间 与 同花顺猪肉指数", "#14283F", 35)
last_close_date = index_status[visible[-1]["month"]]
timing_label = "按已知发布日期或保守滞后入图" if release_dates else "供应收缩信号按次月末可见处理"
text_at((82, 93), f"2022.11—{last_close_date}  |  {timing_label}  |  885573.TI 收盘", "#64748B", 19)

for year in range(2023, 2027):
    month = f"{year}-01"
    if first_no <= month_no(month) <= last_no:
        x = xcoord(month)
        line([(x, top1), (x, bottom2)], "#EBEFF3", 1)
        text_at((x, 1000), str(year), "#64748B", 17, "mt")

for tick in range(index_min, index_max + 1, 250):
    y = y_index(tick)
    line([(left, y), (right, y)], "#E8EDF2", 1)
    text_at((left - 15, y), str(tick), "#66788A", 16, "rm")
for tick in [0, 25, 50, 70, 100]:
    y = y_pcli(tick)
    line([(left, y), (right, y)], "#E8EDF2", 1)
    text_at((left - 15, y), str(tick), "#66788A", 16, "rm")

text_at((135, 150), "885573.TI 指数点位", "#25445C", 20)
line([(left, y_index(visible[0]["index_close"]))] +
     [(xcoord(r["month"]), y_index(r["index_close"])) for r in visible],
     "#CC563A", 4)
last = visible[-1]
draw.ellipse(xy(xcoord(last["month"]) - 5, y_index(last["index_close"]) - 5,
                xcoord(last["month"]) + 5, y_index(last["index_close"]) + 5),
             fill="#CC563A")
text_at((right - 10, top1 + 10),
        f"最新 {last['index_close']:.1f}  ({last_close_date[5:].replace('-', '/')})", "#B74730", 18, "rt")

text_at((135, 616), "PCLI-Beta 区间：缺失分项按 0—100 约束；虚线仅为区间中点", "#25445C", 20)
valid = [r for r in visible if r["pcli_lower"] is not None]
poly = [(xcoord(r["month"]), y_pcli(r["pcli_lower"])) for r in valid]
poly += [(xcoord(r["month"]), y_pcli(r["pcli_upper"])) for r in reversed(valid)]
draw.polygon([(round(x * S), round(y * S)) for x, y in poly], fill="#DCE8F0")
line([(xcoord(r["month"]), y_pcli(r["pcli_lower"])) for r in valid], "#4385A7", 2)
line([(xcoord(r["month"]), y_pcli(r["pcli_upper"])) for r in valid], "#4385A7", 2)
midpoints = [(xcoord(r["month"]), y_pcli(r["pcli_interval_midpoint_not_measured"]))
             for r in valid]
for a, b in zip(midpoints[::2], midpoints[1::2]):
    line([a, b], "#255C79", 2)
line([(left, y_pcli(70)), (right, y_pcli(70))], "#D7AA4B", 2)
text_at((right - 5, y_pcli(70) - 6), "旧阈值 70（未经校准）", "#A87818", 16, "rb")
last_valid = valid[-1]
text_at((right - 6, y_pcli(last_valid["pcli_upper"]) - 6),
        f"上界 {last_valid['pcli_upper']:.1f}", "#255C79", 18, "rb")
text_at((right - 6, y_pcli(last_valid["pcli_lower"]) + 6),
        f"下界 {last_valid['pcli_lower']:.1f}", "#255C79", 18, "rt")

text_at((82, 1050), "来源：同花顺 iFinD；国家统计局；农业农村部；国家生猪市场。2026-10 为未完月。", "#64748B", 16)
timing_note = ("9月末官方产能数据按10月实际发布日期纳入；其余历史值用保守滞后，非逐期首次发布回测。"
               if release_dates else "本图是修订后历史数据的保守滞后重建，不是逐日首次发布版本或择时回测。")
text_at((82, 1080), timing_note, "#64748B", 16)
im.save(OUT / "pcli_vs_885573.png", optimize=True)

print(f"Saved {len(rows)} monthly rows, {len(valid)} plotted PCLI intervals.")
print("Latest:", {key: last_valid[key] for key in ["month", "sow_observation_month",
      "stock_observation_month", "slaughter_observation_month", "weight_observation_month",
      "known_weight", "pcli_lower", "pcli_upper", "index_close"]})
