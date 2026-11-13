#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 W4 候选企业的关键公告标题与 URL。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "20_数据库" / "w4_titles.json").read_text(encoding="utf-8"))

WANTED = {
    "立讯精密": ["授信", "担保", "债券"],
    "美的集团": ["担保", "中期票据", "债券"],
    "比亚迪": ["担保", "债券", "募集资金"],
}

for company, labels in WANTED.items():
    print(f"\n######## {company} ########")
    for label in labels:
        payload = data.get(company, {}).get(label, {})
        print(f"\n== {label} ({payload.get('count')}) ==")
        for idx, item in enumerate(payload.get("items", []), 1):
            print(f"{idx:02d} | {item['title']} | {item['url']}")
