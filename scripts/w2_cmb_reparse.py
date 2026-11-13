#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补读招商银行 2025 年报（CID 字体，需 fontTools）。"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_数据库" / "vendor"))
from pypdf import PdfReader  # noqa: E402

PDF = ROOT / "13_机构档案" / "招商银行" / "annual_2025.pdf"
OUT_CSV = ROOT / "20_数据库" / "w2_cmb_evidence.csv"
OUT_TXT = ROOT / "20_数据库" / "w2_annual_text" / "招商银行_2025_v2.txt"

KEYWORDS = [
    "科技金融", "科技贷款", "科技型企业", "科技金融部", "集团协同", "协同",
    "子公司", "招银投资", "招商证券", "招银国际", "招银金租", "招银理财", "金融资产投资",
]


def main() -> int:
    reader = PdfReader(str(PDF))
    page_texts = []
    for page in reader.pages:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            page_texts.append("")
    OUT_TXT.write_text("\n\n".join(page_texts), encoding="utf-8")
    print("pages:", len(page_texts), "chars:", sum(len(t) for t in page_texts))
    print("sample:", re.sub(r"\s+", "", page_texts[0])[:120])

    rows = []
    for keyword in KEYWORDS:
        hits = 0
        for page_no, text in enumerate(page_texts, 1):
            norm = re.sub(r"\s+", "", text)
            pos = norm.find(keyword)
            if pos < 0:
                continue
            rows.append(
                {
                    "银行": "招商银行",
                    "关键词": keyword,
                    "PDF页码": page_no,
                    "上下文": norm[max(0, pos - 120):pos + 240],
                    "来源URL": "http://static.cninfo.com.cn/finalpage/2026-03-28/1225047590.PDF",
                }
            )
            hits += 1
            if hits >= 3:
                break
        print(f"{keyword}: {hits}")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["银行", "关键词", "PDF页码", "上下文", "来源URL"])
        writer.writeheader()
        writer.writerows(rows)
    print("rows:", len(rows))
    print("written:", OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
