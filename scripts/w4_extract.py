#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W4：立讯/美的/比亚迪关键公告抽取，比较第二试点可行性。"""

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
    # 立讯精密
    {"company": "立讯精密", "title": "2026年度对外担保额度预计", "date": "2025-12-02", "url": "http://static.cninfo.com.cn/finalpage/2025-12-02/1224841714.PDF"},
    {"company": "立讯精密", "title": "申请增加银行间债券市场DFI发行规模", "date": "2026-04-15", "url": "http://static.cninfo.com.cn/finalpage/2026-04-15/1225104920.PDF"},
    {"company": "立讯精密", "title": "向银行申请综合授信额度", "date": "2026-04-15", "url": "http://static.cninfo.com.cn/finalpage/2026-04-15/1225104931.PDF"},
    {"company": "立讯精密", "title": "可转换公司债券2026年跟踪评级报告", "date": "2026-06-06", "url": "http://static.cninfo.com.cn/finalpage/2026-06-06/1225354295.PDF"},
    # 美的集团
    {"company": "美的集团", "title": "2026年度为下属控股子公司提供担保", "date": "2026-03-31", "url": "http://static.cninfo.com.cn/finalpage/2026-03-31/1225058122.PDF"},
    {"company": "美的集团", "title": "2026年度资产池业务担保", "date": "2026-03-31", "url": "http://static.cninfo.com.cn/finalpage/2026-03-31/1225058121.PDF"},
    {"company": "美的集团", "title": "拟注册发行超短期融资券和中期票据", "date": "2025-04-30", "url": "http://static.cninfo.com.cn/finalpage/2025-04-30/1223412443.PDF"},
    {"company": "美的集团", "title": "发行H股可转换公司债券", "date": "2026-05-14", "url": "http://static.cninfo.com.cn/finalpage/2026-05-14/1225304414.PDF"},
    # 比亚迪
    {"company": "比亚迪", "title": "2026年度对外担保额度", "date": "2026-03-28", "url": "http://static.cninfo.com.cn/finalpage/2026-03-28/1225045363.PDF"},
    {"company": "比亚迪", "title": "资产池业务并进行对外担保", "date": "2026-08-29", "url": "http://static.cninfo.com.cn/finalpage/2026-08-29/1225531838.PDF"},
    {"company": "比亚迪", "title": "2025年度对外担保额度", "date": "2025-03-25", "url": "http://static.cninfo.com.cn/finalpage/2025-03-25/1222881490.PDF"},
]


def main() -> int:
    docs = []
    relations = []

    for idx, doc in enumerate(DOCS, 1):
        company_dir = OUT_DIR / doc["company"]
        company_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", doc["title"])[:50]
        pdf_path = company_dir / f"{doc['date']}_{idx:02d}_{safe}.pdf"
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
                    key = (group, entity, context[:60])
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
                                "证据等级": "A",
                                "来源URL": doc["url"],
                            }
                        )
                    start = pos + len(brand)

    (DB_DIR / "w4_documents.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    with (DB_DIR / "w4_relations.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["企业", "文档", "文档日期", "银行集团", "法人/品牌", "上下文", "证据等级", "来源URL"])
        writer.writeheader()
        writer.writerows(relations)

    print(f"\n文档：{len(docs)}；关系行：{len(relations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
