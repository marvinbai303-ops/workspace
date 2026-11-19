import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def q(tag):
    return "{" + NS + "}" + tag


def date_value(value):
    number = float(value)
    return (datetime(1899, 12, 30) + timedelta(days=number)).strftime("%Y-%m-%d")


def parse(path):
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(q("si")):
                shared.append("".join(x.text or "" for x in item.iter(q("t"))))
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        output = []
        for row in root.findall(".//" + q("row")):
            cells = {}
            for cell in row.findall(q("c")):
                ref = cell.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())
                node = cell.find(q("v"))
                value = "" if node is None else node.text or ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                cells[col] = value
            if "A" not in cells or "B" not in cells:
                continue
            try:
                output.append({"date": date_value(cells["A"]), "value": float(cells["B"])})
            except (TypeError, ValueError):
                continue
        print(json.dumps(output))


if __name__ == "__main__":
    parse(sys.argv[1])
