#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W2 补读：抽取三家银行 2025 年报关键章节与页码。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_数据库" / "vendor"))
from pypdf import PdfReader  # noqa: E402

from w3_extract import download  # noqa: E402

DB_DIR = ROOT / "20_数据库"
OUT_CSV = DB_DIR / "w2_annual_evidence.csv"
OUT_TXT = DB_DIR / "w2_annual_text"
OUT_TXT.mkdir(parents=True, exist_ok=True)

BANKS = [
    {
        "name": "招商银行",
        "dir": "招商银行",
        "url": "http://static.cninfo.com.cn/finalpage/2026-03-28/1225047590.PDF",
    },
    {
        "name": "中信银行",
        "dir": "中信银行",
        "url": "http://static.cninfo.com.cn/finalpage/2026-03-21/1225022321.PDF",
    },
    {
        "name": "兴业银行",
        "dir": "兴业银行",
        "url": "http://static.cninfo.com.cn/finalpage/2026-03-27/1225039240.PDF",
    },
]

KEYWORDS = [
    "科技金融", "科技贷款", "科技型企业", "科技金融部", "科技金融中心",
    "集团协同", "协同", "子公司", "并表",
    "金融资产投资", "招银投资", "信银金投", "兴银投资", "AIC",
    "招商证券", "中信证券", "中信信托", "中信建投", "兴业证券",
    "招银国际", "招银金租", "招银理财", "信银理财", "信银投资", "中信金租",
    "兴业信托", "兴业金租", "兴银理财", "兴业基金",
]


def main() -> int:
    rows = []
    for bank in BANKS:
        target_dir = ROOT / "13_机构档案" / bank["dir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = target_dir / "annual_2025.pdf"
        txt_path = OUT_TXT / f"{bank['name']}_2025.txt"
        print(f"\n== {bank['name']} ==")
        if not pdf_path.exists():
            print("  downloading...")
            download(bank["url"], pdf_path)
        print("  extracting...")
        reader = PdfReader(str(pdf_path))
        page_texts = []
        for page in reader.pages:
            try:
                page_texts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                page_texts.append("")
        txt_path.write_text("\n\n".join(page_texts), encoding="utf-8")
        print(f"  pages={len(page_texts)} chars={sum(len(t) for t in page_texts)}")

        for keyword in KEYWORDS:
            hits = 0
            for page_no, text in enumerate(page_texts, 1):
                norm = re.sub(r"\s+", "", text)
                pos = norm.find(keyword)
                if pos < 0:
                    continue
                context = norm[max(0, pos - 120):pos + 220]
                rows.append(
                    {
                        "银行": bank["name"],
                        "关键词": keyword,
                        "PDF页码": page_no,
                        "上下文": context,
                        "来源URL": bank["url"],
                    }
                )
                hits += 1
                if hits >= 3:
                    break
            if hits == 0:
                rows.append(
                    {
                        "银行": bank["name"],
                        "关键词": keyword,
                        "PDF页码": "",
                        "上下文": "未找到",
                        "来源URL": bank["url"],
                    }
                )
        print(f"  keyword rows: {sum(1 for r in rows if r['银行'] == bank['name'])}")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["银行", "关键词", "PDF页码", "上下文", "来源URL"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n已写入：{OUT_CSV}")
    print(f"文本目录：{OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
