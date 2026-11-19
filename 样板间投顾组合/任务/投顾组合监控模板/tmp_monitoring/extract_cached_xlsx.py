import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def col_num(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - 64
    return value


path, wanted_sheet = sys.argv[1:3]
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
        raise SystemExit(f"sheet not found: {wanted_sheet}")
    sheet_path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
    root = ET.fromstring(zf.read(sheet_path))
    out = {}
    for cell in root.iter(f"{{{NS_MAIN}}}c"):
        ref = cell.attrib["r"]
        value_node = cell.find(f"{{{NS_MAIN}}}v")
        formula_node = cell.find(f"{{{NS_MAIN}}}f")
        if value_node is None:
            value = None
        elif cell.attrib.get("t") == "s":
            value = shared[int(value_node.text)]
        elif cell.attrib.get("t") == "str":
            value = value_node.text
        else:
            try:
                value = float(value_node.text)
            except (TypeError, ValueError):
                value = value_node.text
        out[ref] = {"v": value, "f": formula_node.text if formula_node is not None else None}
    print(json.dumps(out, ensure_ascii=False))
