"""Read the named official Overall three-month series, never page/header numbers."""
import json
import sys
from datetime import datetime
import math
import openpyxl


def parse(path):
    with open(path, "rb") as source:
        book = openpyxl.load_workbook(source, read_only=True, data_only=True)
        if "data_overall" not in book.sheetnames:
            raise RuntimeError("WGT data_overall sheet not found")
        rows = book["data_overall"].iter_rows(max_col=20, values_only=True)
        value_col = None
        output = []
        for row in rows:
            if value_col is None:
                matches = [i for i, value in enumerate(row) if value == "Overall"]
                if len(matches) == 1:
                    value_col = matches[0]
                continue
            date, value = row[0], row[value_col]
            if not isinstance(date, datetime) or date.day != 1:
                continue
            if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                continue
            if not -20 <= value <= 30:
                raise ValueError(f"WGT value out of range: {date}: {value}")
            output.append({"date": date.strftime("%Y-%m-%d"), "value": value})
        book.close()
    if value_col is None or len(output) < 60:
        raise RuntimeError("WGT Overall header or monthly series missing")
    output.sort(key=lambda item: item["date"])
    if len({x["date"] for x in output}) != len(output):
        raise RuntimeError("Duplicate WGT observation dates")
    print(json.dumps(output))


if __name__ == "__main__":
    parse(sys.argv[1])
