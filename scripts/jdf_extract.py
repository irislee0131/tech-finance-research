#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3 备选：京东方科创债募集说明书文本抽取与银行法人识别。"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from w3_extract import GROUPS, download, extract_text

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "14_原始公告" / "京东方"
DB_DIR = ROOT / "20_数据库"
DOC_JSON = DB_DIR / "jdf_documents.json"
REL_CSV = DB_DIR / "jdf_relations.csv"

DOCS = [
    {"company": "京东方", "title": "2026年科技创新公司债券（第二期）募集说明书", "date": "2026-03-13", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-03-13/1225008126.PDF"},
    {"company": "京东方", "title": "2026年科技创新公司债券（第一期）募集说明书", "date": "2026-01-20", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-01-20/1224942551.PDF"},
    {"company": "京东方", "title": "2025年科技创新公司债券（第三期）募集说明书", "date": "2025-11-11", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-11-11/1224799190.PDF"},
    {"company": "京东方", "title": "2025年科技创新公司债券（第二期）募集说明书", "date": "2025-11-03", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-11-03/1224785112.PDF"},
    {"company": "京东方", "title": "2025年科技创新公司债券（第一期）募集说明书", "date": "2025-06-10", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-06-10/1223836933.PDF"},
    {"company": "京东方", "title": "2026年度控股子公司担保额度预计", "date": "2026-04-14", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-04-14/1225098320.PDF"},
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    docs = []
    relations = []

    for idx, doc in enumerate(DOCS, 1):
        safe = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", doc["title"])[:50]
        pdf_path = OUT_DIR / f"{doc['date']}_{idx:02d}_{safe}.pdf"
        txt_path = pdf_path.with_suffix(".txt")
        print(f"[{idx}/{len(DOCS)}] {doc['title']}")
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
                                "企业": "京东方",
                                "文档": doc["title"],
                                "文档日期": doc["date"],
                                "银行集团": group,
                                "法人/品牌": entity,
                                "上下文": context,
                                "证据等级": doc["level"],
                                "来源URL": doc["url"],
                            }
                        )
                    start = pos + len(brand)

    DOC_JSON.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    with REL_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["企业", "文档", "文档日期", "银行集团", "法人/品牌", "上下文", "证据等级", "来源URL"])
        writer.writeheader()
        writer.writerows(relations)

    print(f"\n文档：{len(docs)}；关系行：{len(relations)}")
    print(f"已写入：{DOC_JSON}")
    print(f"已写入：{REL_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
