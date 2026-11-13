#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补读招商银行 2025 年报摘要 / 2026 半年报（招行正文 CID 编码，改用摘要）。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_数据库" / "vendor"))
from pypdf import PdfReader  # noqa: E402

from w3_extract import download  # noqa: E402

OUT_CSV = ROOT / "20_数据库" / "w2_cmb_summary.csv"

DOCS = [
    ("2025年年度报告摘要", "2026-03-28", "http://static.cninfo.com.cn/finalpage/2026-03-28/1225047778.PDF"),
    ("2026年半年度报告", "2026-08-29", "http://static.cninfo.com.cn/finalpage/2026-08-29/1225530237.PDF"),
]

KEYWORDS = ["科技金融", "科技贷款", "科技型企业", "科技金融部", "集团协同", "协同", "子公司", "招银投资", "招商证券", "招银国际", "招银金租", "招银理财"]


def main() -> int:
    rows = []
    for title, date, url in DOCS:
        target = ROOT / "13_机构档案" / "招商银行" / f"{date}_{title}.pdf"
        print(f"\n== {title} ==")
        if not target.exists():
            download(url, target)
        reader = PdfReader(str(target))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                texts.append("")
        print("pages:", len(texts), "chars:", sum(len(t) for t in texts))
        print("sample:", re.sub(r"\s+", "", texts[0])[:100] if texts else "")
        for keyword in KEYWORDS:
            for page_no, text in enumerate(texts, 1):
                norm = re.sub(r"\s+", "", text)
                pos = norm.find(keyword)
                if pos < 0:
                    continue
                rows.append(
                    {
                        "文档": title,
                        "日期": date,
                        "关键词": keyword,
                        "PDF页码": page_no,
                        "上下文": norm[max(0, pos - 100):pos + 220],
                        "来源URL": url,
                    }
                )
                break
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["文档", "日期", "关键词", "PDF页码", "上下文", "来源URL"])
        writer.writeheader()
        writer.writerows(rows)
    print("\nrows:", len(rows), "written:", OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
