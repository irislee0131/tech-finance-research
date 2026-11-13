#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询宁德时代、中国中车 2025 年度报告标题与链接。"""

from __future__ import annotations

import http.client
import json
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "20_数据库" / "w3_annual_titles.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2025-01-01~2026-11-12"

COMPANIES = [
    ("宁德时代", "300750,GD165627"),
    ("中国中车", "601766,9900005127"),
]


def query(stock: str, key: str):
    form = {
        "pageNum": "1", "pageSize": "20", "column": "szse", "tabName": "fulltext",
        "plate": "", "stock": stock, "searchkey": key, "secDate": "", "tdate": "",
        "type": "", "category": "", "trade": "", "seDate": SE_DATE,
        "sortName": "", "sortType": "", "isHLtitle": "true",
    }
    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": UA,
        "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
        "X-Requested-With": "XMLHttpRequest",
    }
    for attempt in range(3):
        conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=25)
        try:
            conn.request("POST", "/new/hisAnnouncement/query", body=body, headers=headers)
            resp = conn.getresponse()
            return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (attempt + 1))
        finally:
            conn.close()
    return {"totalAnnouncement": -1, "announcements": []}


out = {}
for name, stock in COMPANIES:
    data = query(stock, "年度报告")
    print(f"\n== {name} == total={data.get('totalAnnouncement')}")
    items = []
    for item in (data.get("announcements") or [])[:12]:
        title = str(item.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")
        url = f"http://static.cninfo.com.cn/{item.get('adjunctUrl')}"
        items.append({"title": title, "date": item.get("announcementTime"), "url": url})
        print("  -", title, "|", url)
    out[name] = items

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已写入：{OUT}")
