import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


SOURCE = Path("../2080样板间测算底稿.xlsx")
OUTPUT = Path("yellow_input_snapshot.json")
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def numeric_value(cell):
    value = cell.find("x:v", NS)
    if value is None or value.text is None:
        return None
    return float(value.text)


with zipfile.ZipFile(SOURCE) as archive:
    root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

rows = []
for row in root.findall(".//x:sheetData/x:row", NS):
    row_no = int(row.attrib["r"])
    if not 4 <= row_no <= 1618:
        continue
    cells = {cell.attrib["r"].rstrip("0123456789"): numeric_value(cell) for cell in row.findall("x:c", NS)}
    rows.append({
        "source_row": row_no,
        "date_serial": cells.get("A"),
        "industry_nav": cells.get("F"),
        "index_nav": cells.get("O"),
        "bond_nav": cells.get("P"),
        "gold_nav": cells.get("Q"),
    })

OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {len(rows)} rows to {OUTPUT}")
