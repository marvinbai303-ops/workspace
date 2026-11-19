import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def q(ns, tag):
    return "{" + ns + "}" + tag


def excel_date(value):
    try:
        number = float(value)
        return (datetime(1899, 12, 30) + timedelta(days=number)).strftime("%Y-%m-%d")
    except Exception:
        value = str(value).strip()
        for fmt in ("%d-%b-%Y", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        if len(value) >= 10 and value[4] == "-":
            return value[:10]
        return value


def cell_value(cell, shared):
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        node = cell.find(".//" + q(NS_MAIN, "t"))
        return "" if node is None else node.text or ""
    node = cell.find(q(NS_MAIN, "v"))
    value = "" if node is None else node.text or ""
    if kind == "s" and value:
        return shared[int(value)]
    return value


def parse(path):
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(q(NS_MAIN, "si")):
                shared.append("".join(x.text or "" for x in item.iter(q(NS_MAIN, "t"))))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall(q(NS_PKG, "Relationship"))}
        sheet_path = None
        for sheet in workbook.find(q(NS_MAIN, "sheets")):
            if sheet.attrib.get("name") == "ACM Daily":
                target = rel_map[sheet.attrib[q(NS_REL, "id")]]
                sheet_path = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
                break
        if sheet_path is None:
            raise RuntimeError("ACM Daily sheet not found")

        root = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row in root.findall(".//" + q(NS_MAIN, "row")):
            values = {}
            for cell in row.findall(q(NS_MAIN, "c")):
                ref = cell.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())
                values[col] = cell_value(cell, shared)
            rows.append(values)

        header_index = None
        headers = None
        for index, row in enumerate(rows):
            if "ACMTP10" in row.values():
                header_index = index
                headers = {value: key for key, value in row.items()}
                break
        if header_index is None:
            raise RuntimeError("ACMTP10 header not found")

        date_col = headers.get("Date") or headers.get("DATE") or "A"
        output = []
        for row in rows[header_index + 1:]:
            date = row.get(date_col, "")
            tp = row.get(headers["ACMTP10"], "")
            if not date or not tp:
                continue
            output.append({"date": excel_date(date), "ACMTP10": float(tp)})
        print(json.dumps(output))


if __name__ == "__main__":
    parse(sys.argv[1])
