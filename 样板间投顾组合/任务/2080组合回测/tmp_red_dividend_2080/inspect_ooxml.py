from collections import Counter
from pathlib import Path
from zipfile import ZipFile
import json
import re
import xml.etree.ElementTree as ET

BOOK = Path("../2080红利样板间回测模型.xlsx")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_letters(address: str) -> str:
    return re.match(r"[A-Z]+", address).group(0)


with ZipFile(BOOK) as archive:
    shared = []
    shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    for item in shared_root.findall("m:si", NS):
        shared.append("".join(node.text or "" for node in item.iterfind(".//m:t", NS)))

    styles_root = ET.fromstring(archive.read("xl/styles.xml"))
    cell_xfs = styles_root.find("m:cellXfs", NS)
    fill_ids = [int(xf.attrib.get("fillId", "0")) for xf in cell_xfs]

    sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = sheet_root.findall(".//m:sheetData/m:row", NS)

    sample = []
    yellow_counts = Counter()
    source_rows = {}
    for row in rows:
        row_num = int(row.attrib["r"])
        for cell in row.findall("m:c", NS):
            addr = cell.attrib["r"]
            style_id = int(cell.attrib.get("s", "0"))
            fill_id = fill_ids[style_id]
            value_node = cell.find("m:v", NS)
            value = value_node.text if value_node is not None else None
            if cell.attrib.get("t") == "s" and value is not None:
                value = shared[int(value)]
            formula_node = cell.find("m:f", NS)
            formula = formula_node.text if formula_node is not None else None

            if 1 <= row_num <= 8:
                sample.append(
                    {
                        "cell": addr,
                        "style": style_id,
                        "fill": fill_id,
                        "value": value,
                        "formula": formula,
                    }
                )
            if 4 <= row_num <= 1618 and fill_id in (5, 14):
                yellow_counts[col_letters(addr)] += 1
            if 4 <= row_num <= 1618 and col_letters(addr) in {"A", "G", "H", "I", "J", "K", "T", "U", "V"}:
                source_rows.setdefault(row_num, {})[col_letters(addr)] = value

print("SAMPLE_ROWS_1_8")
print(json.dumps(sample, ensure_ascii=False, indent=2))
print("YELLOW_CELL_COUNTS_BY_COLUMN")
print(json.dumps(dict(sorted(yellow_counts.items())), ensure_ascii=False, indent=2))

columns = ["A", "G", "H", "I", "J", "K", "T", "U", "V"]
matrix = []
for row_num in range(4, 1619):
    row = source_rows.get(row_num, {})
    matrix.append([float(row[col]) if row.get(col) not in (None, "") else None for col in columns])

stats = {}
for idx, col in enumerate(columns):
    values = [row[idx] for row in matrix if row[idx] is not None]
    stats[col] = {
        "count": len(values),
        "missing": len(matrix) - len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "first": values[0] if values else None,
        "last": values[-1] if values else None,
    }

Path("source_cached_values.json").write_text(
    json.dumps({"columns": columns, "rows": matrix, "stats": stats}, ensure_ascii=False),
    encoding="utf-8",
)
print("SOURCE_STATS")
print(json.dumps(stats, ensure_ascii=False, indent=2))
