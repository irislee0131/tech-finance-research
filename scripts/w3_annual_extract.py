#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取宁德时代/中国中车 2025 年报，补充银行关系与授信线索。"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from w3_extract import GROUPS, download, extract_text

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "14_原始公告"
DB_DIR = ROOT / "20_数据库"

DOCS = [
    {"company": "宁德时代", "title": "2025年年度报告", "date": "2026-03-10", "url": "http://static.cninfo.com.cn/finalpage/2026-03-10/1225002214.PDF"},
    {"company": "中国中车", "title": "2025年年度报告", "date": "2026-03-28", "url": "http://static.cninfo.com.cn/finalpage/2026-03-28/1225047457.PDF"},
]


def main() -> int:
    docs = []
    relations = []
    credit = []

    for idx, doc in enumerate(DOCS, 1):
        company_dir = OUT_DIR / doc["company"]
        company_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = company_dir / f"{doc['date']}_annual_2025.pdf"
        txt_path = pdf_path.with_suffix(".txt")
        print(f"[{idx}/{len(DOCS)}] {doc['company']} {doc['title']}")
        try:
            if not pdf_path.exists():
                download(doc["url"], pdf_path)
            text = extract_text(pdf_path)
            txt_path.write_text(text, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print("  ERROR:", type(exc).__name__, exc)
            docs.append({**doc, "pdf": str(pdf_path), "text_len": 0, "error": f"{type(exc).__name__}: {exc}"})
            continue

        norm = re.sub(r"\s+", "", text)
        docs.append({**doc, "pdf": str(pdf_path), "txt": str(txt_path), "text_len": len(norm), "error": ""})
        print("  text_len:", len(norm))

        seen = set()
        for group, brands in GROUPS.items():
            for brand in brands:
                start = 0
                while True:
                    pos = norm.find(brand, start)
                    if pos < 0:
                        break
                    tail = norm[pos:pos + 40]
                    entity = re.split(r"[，。；、:：（）()\[\]【】]", tail)[0][:40]
                    context = norm[max(0, pos - 90):pos + 140]
                    key = (group, entity, context[:50])
                    if key not in seen:
                        seen.add(key)
                        relations.append(
                            {
                                "企业": doc["company"],
                                "文档": doc["title"],
                                "文档日期": doc["date"],
                                "银行集团": group,
                                "法人/品牌": entity,
                                "上下文": context,
                                "证据等级": "B",
                                "来源URL": doc["url"],
                            }
                        )
                    start = pos + len(brand)

        # 授信线索：所有“授信”上下文，供人工判断是否列明银行
        for m in re.finditer("授信", norm):
            ctx = norm[max(0, m.start() - 100):m.start() + 180]
            if len(credit) < 80:
                credit.append({"企业": doc["company"], "上下文": ctx})

    (DB_DIR / "w3_annual_documents.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    with (DB_DIR / "w3_annual_relations.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["企业", "文档", "文档日期", "银行集团", "法人/品牌", "上下文", "证据等级", "来源URL"])
        writer.writeheader()
        writer.writerows(relations)
    (DB_DIR / "w3_annual_credit.json").write_text(json.dumps(credit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n文档：{len(docs)}；关系行：{len(relations)}；授信线索：{len(credit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
