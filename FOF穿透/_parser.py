"""Parse iFinD markdown responses, group by tier-3 industry, compute CR5."""
import json, os, re, glob

RAW_DIR = "/Users/yangguang/Documents/Claude/Projects/FOF穿透/_ifind_raw"
INDICES = "/Users/yangguang/Documents/Claude/Projects/FOF穿透/_indices.json"
OUT_JSON = "/Users/yangguang/Documents/Claude/Projects/FOF穿透/_cr5.json"


def yi_to_float(s):
    s = s.strip()
    if not s or s == "-":
        return None
    if "万亿" in s:
        return float(s.replace("万亿", "").strip()) * 1e12
    if "亿" in s:
        return float(s.replace("亿", "").strip()) * 1e8
    if "万" in s:
        return float(s.replace("万", "").strip()) * 1e4
    try:
        return float(s)
    except Exception:
        return None


def parse_markdown_tables(text):
    """Return list of tables; each table = list of dicts (header → cell)."""
    tables = []
    current = []
    header = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if header is None:
                header = cells
            elif set(cells) == {"---"} or all(c.startswith("---") or c == "" for c in cells):
                continue
            else:
                if len(cells) == len(header):
                    current.append(dict(zip(header, cells)))
        else:
            if header and current:
                tables.append((header, current))
            header = None
            current = []
    if header and current:
        tables.append((header, current))
    return tables


def parse_response(text):
    """From one iFinD response answer, return list of (code, name, mcap_yuan, industry_name, industry_code)."""
    tables = parse_markdown_tables(text)
    mcap = {}        # code → mcap_yuan
    name = {}        # code → name
    industry = {}    # code → tier-3 industry name
    icode = {}       # code → tier-3 industry CI code
    for hdr, rows in tables:
        for r in rows:
            code = r.get("证券代码") or r.get("股票代码")
            if not code or not code.startswith(("0", "3", "6", "8", "9")) and "." not in code:
                continue
            # standardize code: prefer with .SH/.SZ/.BJ suffix
            if "." not in code:
                continue
            nm = r.get("证券简称") or r.get("股票简称") or r.get("股票简称（行情端）")
            if nm:
                name[code] = nm
            mv = r.get("自由流通市值（单位：元）") or r.get("自由流通市值")
            if mv:
                v = yi_to_float(mv)
                if v:
                    mcap[code] = v
            # industry: prefer the column where tier-3 is implied
            ind = r.get("所属中信行业")
            if ind:
                industry[code] = ind
            ic = r.get("所属中信行业代码")
            if ic:
                icode[code] = ic
    out = []
    for code, mv in mcap.items():
        out.append({
            "code": code,
            "name": name.get(code, ""),
            "mcap": mv,
            "industry": industry.get(code, ""),
            "industry_code": icode.get(code, ""),
        })
    return out


def build_cr5():
    """Process all raw files; group by industry; compute CR5 per industry; map to indices."""
    indices = json.load(open(INDICES, encoding="utf-8"))
    # industry_name (with "指数" stripped) → index meta
    name2idx = {}
    for it in indices:
        nm = it["name"]
        ind_nm = nm[:-2] if nm.endswith("指数") else nm
        name2idx[ind_nm] = it

    # accumulate all stocks across all raw files
    all_stocks = {}  # code → record
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "*.md"))):
        text = open(path, encoding="utf-8").read()
        recs = parse_response(text)
        for r in recs:
            if r["code"] not in all_stocks:
                all_stocks[r["code"]] = r
            else:
                ex = all_stocks[r["code"]]
                for k in ("industry", "industry_code"):
                    if not ex[k] and r[k]:
                        ex[k] = r[k]
                if not ex["mcap"] and r["mcap"]:
                    ex["mcap"] = r["mcap"]
    # also load inline-saved master JSON if exists
    # Master JSON is curated/authoritative — it OVERRIDES industry from MD files,
    # because MD files often misclassify (loose 板块 vs strict 中信三级行业).
    master_path = "/Users/yangguang/Documents/Claude/Projects/FOF穿透/_stocks_master.json"
    if os.path.exists(master_path):
        for rec in json.load(open(master_path, encoding="utf-8")):
            code, name, mcap_yi, ind, ind_code = rec
            mcap = float(mcap_yi) * 1e8
            if code not in all_stocks:
                all_stocks[code] = {"code": code, "name": name, "mcap": mcap, "industry": ind, "industry_code": ind_code}
            else:
                ex = all_stocks[code]
                if ind:
                    ex["industry"] = ind
                if ind_code:
                    ex["industry_code"] = ind_code
                if mcap:
                    ex["mcap"] = mcap

    # Exclusion list: stocks whose CURRENT 三级行业 was recently reclassified
    # but the corresponding CITIC index has NOT yet rebalanced to include them.
    # Verified against iFinD's actual index constituents.
    EXCLUDE = {
        ("603993.SH", "其他稀有金属"),  # 洛阳钼业: recently moved to CI123060, not in CI005403 index
    }

    # group by tier-3 industry name
    by_ind = {}
    for r in all_stocks.values():
        ind = r["industry"]
        if not ind:
            continue
        if (r["code"], ind) in EXCLUDE:
            continue
        by_ind.setdefault(ind, []).append(r)

    # Manual injections for CITIC 三级 indices not covered by canonical 中信行业 column
    by_ind["核电"] = [
        {"code": "601985.SH", "name": "中国核电", "mcap": 696.8012e8, "industry": "核电", "industry_code": "CI201040"},
        {"code": "003816.SZ", "name": "中国广核", "mcap": 275.9306e8, "industry": "核电", "industry_code": "CI201040"},
    ]

    # build CR5 per index
    out = []
    for ind_nm, idx_meta in name2idx.items():
        stocks = by_ind.get(ind_nm, [])
        stocks = [s for s in stocks if s["mcap"]]
        stocks.sort(key=lambda x: x["mcap"], reverse=True)
        total = sum(s["mcap"] for s in stocks)
        top = stocks[:5]
        for rank, s in enumerate(top, 1):
            out.append({
                "index_code": idx_meta["code"],
                "index_name": idx_meta["name"],
                "n_xlsx": idx_meta["n"],
                "n_industry": len(stocks),
                "rank": rank,
                "stock_code": s["code"],
                "stock_name": s["name"],
                "mcap_yi": round(s["mcap"] / 1e8, 4),
                "weight_pct": round(s["mcap"] / total * 100, 2) if total else None,
            })
        if not top:
            out.append({
                "index_code": idx_meta["code"],
                "index_name": idx_meta["name"],
                "n_xlsx": idx_meta["n"],
                "n_industry": 0,
                "rank": None, "stock_code": "", "stock_name": "",
                "mcap_yi": None, "weight_pct": None,
            })
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    miss = [i for i in indices if i["name"][:-2] not in by_ind]
    print(f"indices total={len(indices)} matched={len(indices)-len(miss)} missing={len(miss)}")
    if miss:
        print("missing industries (first 30):", [m["name"] for m in miss[:30]])


if __name__ == "__main__":
    os.makedirs(RAW_DIR, exist_ok=True)
    build_cr5()
