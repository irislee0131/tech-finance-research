#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3：下载宁德时代/中国中车关键公告，抽取文本并识别股份行集团法人。

输出：
    14_原始公告/{企业}/*.pdf / *.txt
    20_数据库/w3_documents.json
    20_数据库/w3_relations.csv
"""

from __future__ import annotations

import csv
import http.client
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_数据库" / "vendor"))
from pypdf import PdfReader  # noqa: E402

OUT_DIR = ROOT / "14_原始公告"
DB_DIR = ROOT / "20_数据库"
DOC_JSON = DB_DIR / "w3_documents.json"
REL_CSV = DB_DIR / "w3_relations.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

DOCS = [
    # 宁德时代
    {"company": "宁德时代", "title": "2026年科技创新公司债券（第一期）募集说明书", "date": "2026-02-10", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-02-10/1224974760.PDF"},
    {"company": "宁德时代", "title": "2026年科技创新公司债券（第二期）募集说明书", "date": "2026-06-16", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-06-16/1225373024.PDF"},
    {"company": "宁德时代", "title": "2026年度综合授信额度公告", "date": "2026-03-10", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-03-10/1225002248.PDF"},
    {"company": "宁德时代", "title": "2025年度综合授信额度公告", "date": "2025-03-15", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-03-15/1222807005.PDF"},
    {"company": "宁德时代", "title": "2026年度担保额度预计公告", "date": "2026-03-10", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-03-10/1225002226.PDF"},
    {"company": "宁德时代", "title": "境外全资子公司在境外发行债券并由公司提供担保", "date": "2025-03-15", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-03-15/1222806919.PDF"},
    {"company": "宁德时代", "title": "2026年半年度募集资金存放与使用专项报告", "date": "2026-07-25", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-07-25/1225441590.PDF"},
    {"company": "宁德时代", "title": "变更部分A股募集资金用途后新签订募集资金三方监管协议", "date": "2026-04-03", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-04-03/1225080691.PDF"},
    {"company": "宁德时代", "title": "2026年度第八期绿色科技创新债券发行完成", "date": "2026-09-28", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-09-28/1225584204.PDF"},
    # 中国中车
    {"company": "中国中车", "title": "2026年度担保安排公告", "date": "2026-03-28", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-03-28/1225048436.PDF"},
    {"company": "中国中车", "title": "2025年度担保安排公告", "date": "2025-03-29", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-03-29/1222949497.PDF"},
    {"company": "中国中车", "title": "全资子公司向参股公司提供担保的进展公告", "date": "2026-03-13", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-03-13/1225006525.PDF"},
    {"company": "中国中车", "title": "全资子公司向参股公司提供担保的进展公告", "date": "2026-01-23", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2026-01-23/1224945781.PDF"},
    {"company": "中国中车", "title": "全资子公司向参股公司提供担保的进展公告", "date": "2025-10-11", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-10-11/1224705849.PDF"},
    {"company": "中国中车", "title": "全资子公司向参股公司提供担保的公告", "date": "2025-09-10", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-09-10/1224647180.PDF"},
    {"company": "中国中车", "title": "全资子公司向参股公司提供担保的进展公告", "date": "2025-03-04", "level": "A", "url": "http://static.cninfo.com.cn/finalpage/2025-03-04/1222692952.PDF"},
]

GROUPS = {
    "招商银行集团": [
        "招商银行", "招银国际", "招银租赁", "招银金租", "招银理财", "招银投资", "招银欧洲", "招商永隆", "招商基金", "招商信诺",
    ],
    "中信集团": [
        "中信银行", "中信证券", "中信信托", "信银理财", "信银投资", "信银金投", "中信金租", "中信保诚",
    ],
    "兴业银行集团": [
        "兴业银行", "兴业信托", "兴业金租", "兴银理财", "兴银投资", "兴业基金", "兴业研究", "兴业消费金融",
    ],
    "非中信系（中信建投）": ["中信建投"],
    "非兴业系（兴业证券）": ["兴业证券"],
    "招商局集团（招商证券）": ["招商证券"],
}


def download(url: str, target: Path, attempts: int = 5) -> None:
    parsed = urlparse(url)
    last = None
    for attempt in range(attempts):
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=90)
        try:
            conn.request("GET", parsed.path, headers={"User-Agent": UA, "Connection": "close"})
            resp = conn.getresponse()
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")
            target.write_bytes(resp.read())
            return
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)

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
