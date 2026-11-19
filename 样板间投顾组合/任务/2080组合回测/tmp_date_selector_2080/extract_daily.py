import json
from pathlib import Path

import openpyxl


book = openpyxl.load_workbook("../2080样板间回测模型.xlsx", data_only=False, read_only=False)
sheet = book["2080回测"]
rows = [
    [sheet.cell(row, col).value for col in range(2, 44)]
    for row in range(42, 1657)
]
Path("daily_original.json").write_text(
    json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
print("extracted", len(rows), "rows", len(rows[0]), "columns")
