#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 W3 公告标题与 URL，便于挑选下载。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "20_数据库" / "w3_titles.json").read_text(encoding="utf-8"))

for company, categories in data["companies"].items():
    print(f"\n######## {company} ########")
    for label, payload in categories.items():
        if payload["count"] <= 0:
            continue
        print(f"\n== {label} ({payload['count']}) ==")
        for idx, item in enumerate(payload["items"], 1):
            print(f"{idx:02d} | {item['title']} | {item['url']}")
