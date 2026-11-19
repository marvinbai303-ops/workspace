import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def load_sheet(path, wanted_sheet):
    with zipfile.ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{{{NS_MAIN}}}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t")))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall(f"{{{NS_PKG}}}Relationship")}
        target = None
        for sheet in wb.find(f"{{{NS_MAIN}}}sheets"):
            if sheet.attrib["name"] == wanted_sheet:
                target = rel_map[sheet.attrib[f"{{{NS_REL}}}id"]]
                break
        if not target:
            raise ValueError(wanted_sheet)
        sheet_path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        root = ET.fromstring(zf.read(sheet_path))
        out = {}
        for cell in root.iter(f"{{{NS_MAIN}}}c"):
            ref = cell.attrib["r"]
            node = cell.find(f"{{{NS_MAIN}}}v")
            if node is None:
                out[ref] = None
            elif cell.attrib.get("t") == "s":
                out[ref] = shared[int(node.text)]
            elif cell.attrib.get("t") in ("str", "inlineStr"):
                out[ref] = node.text
            else:
                try:
                    out[ref] = float(node.text)
                except (TypeError, ValueError):
                    out[ref] = node.text
        return out


def xl_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def excel_date(value):
    return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()


main_path, sys_path = sys.argv[1:3]
nav = load_sheet(main_path, "实盘净值数据(iFinD公式)")
phases = load_sheet(main_path, "分期持仓明细")
codes = [str(phases[f"{xl_col(c)}3"]).zfill(6) for c in range(2, 26)]
names = [phases[f"{xl_col(c)}2"] for c in range(2, 26)]

latest_row = max(r for r in range(5, 1001) if isinstance(nav.get(f"B{r}"), (int, float)))
if len(sys.argv) > 3 and sys.argv[3] == "prior":
    latest_row -= 1
latest_date = excel_date(nav[f"A{latest_row}"])
date_to_row = {round(v): r for r in range(5, 1001) if isinstance((v := nav.get(f"A{r}")), (int, float))}
phase_rows = {"产业趋势": 17, "产业趋势基石": 18, "产业趋势2号": 19, "10-90": 20, "10-90基石": 21, "30-70": 22}

results = {}
for combo, row in phase_rows.items():
    effective_serial = phases[f"AA{row}"]
    effective_row = date_to_row[round(effective_serial)]
    values = []
    for idx, col in enumerate(range(2, 26)):
        c = xl_col(col)
        w = phases.get(f"{c}{row}") or 0
        start_nav = nav.get(f"{c}{effective_row}")
        end_nav = nav.get(f"{c}{latest_row}")
        value = w * end_nav / start_nav if w and start_nav and end_nav else 0
        values.append(value)
    total = sum(values)
    weights = [v / total for v in values]
    results[combo] = {
        "effective_date": excel_date(effective_serial),
        "weights": {codes[i]: weights[i] for i in range(len(codes)) if weights[i] > 1e-10},
    }

growth_codes = {"001170", "007044", "007045", "007817", "007818", "009993", "013840", "013841", "014201", "014202", "015453", "015454", "016370", "017488", "017489", "017612", "019632", "019633", "019923", "019924", "162214"}
trend_codes = {"001170", "007817", "007818", "009993", "013840", "013841", "016370", "017488", "017489", "017612", "019632", "019633", "162214"}
active_codes = {"001170", "009993", "013840", "013841", "016370", "017488", "017489", "017612", "162214"}
summaries = {}
for combo, payload in results.items():
    w = payload["weights"]
    growth = sum(w.get(code, 0) for code in growth_codes)
    trend = sum(w.get(code, 0) for code in trend_codes)
    active = [(code, w.get(code, 0)) for code in active_codes]
    active.sort(key=lambda item: item[1], reverse=True)
    summaries[combo] = {
        "growth": growth,
        "income": 1 - growth,
        "trend_within_growth": trend / growth if growth else None,
        "enhanced_within_growth": (growth - trend) / growth if growth else None,
        "max_active": active[0],
    }

system = load_sheet(sys_path, "产业趋势基石组合20260710")
sys_row = max(r for r in range(2, 200) if system.get(f"A{r}"))
sys_date = system[f"A{sys_row}"]
system_weights = {}
for c in range(2, 9):
    col = xl_col(c)
    header = str(system[f"{col}1"])
    code = re.search(r"(\d{6})$", header).group(1)
    system_weights[code] = float(system[f"{col}{sys_row}"])

compare = []
ours = results["产业趋势基石"]["weights"]
for code in sorted(set(ours) | set(system_weights)):
    compare.append({
        "code": code,
        "name": names[codes.index(code)] if code in codes else "",
        "ours": ours.get(code, 0),
        "system": system_weights.get(code, 0),
        "delta": ours.get(code, 0) - system_weights.get(code, 0),
    })

print(json.dumps({
    "latest_date": latest_date,
    "latest_row": latest_row,
    "previous_date": excel_date(nav[f"A{latest_row - 1}"]),
    "nav_changes_vs_previous": {
        codes[i]: (nav.get(f"{xl_col(i + 2)}{latest_row}") or 0) - (nav.get(f"{xl_col(i + 2)}{latest_row - 1}") or 0)
        for i in range(len(codes))
    },
    "system_date": sys_date,
    "results": results,
    "summaries": summaries,
    "compare": compare,
    "max_abs_delta": max(abs(x["delta"]) for x in compare),
    "sum_ours": sum(ours.values()),
    "sum_system": sum(system_weights.values()),
}, ensure_ascii=False, indent=2))
