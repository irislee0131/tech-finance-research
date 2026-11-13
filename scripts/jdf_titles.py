#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3 备选：京东方公告标题扫描。"""

from __future__ import annotations

import http.client
import json
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "20_数据库" / "jdf_titles.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"
STOCK = "000725,gssz0000725"

KEYWORDS = [
    ("债券", "债券"), ("募集说明书", "募集说明书"), ("担保", "担保"), ("授信", "授信"),
    ("募集资金", "募集资金"), ("公司债", "公司债"), ("中期票据", "中期票据"),
    ("银团", "银团"), ("并购贷款", "并购贷款"), ("保理", "保理"), ("供应链", "供应链"),
    ("可转债", "可转债"), ("ABS", "资产支持证券"),
]


def query(key: str, page_size: int = 30, attempts: int = 3):
    form = {
        "pageNum": "1", "pageSize": str(page_size), "column": "szse", "tabName": "fulltext",
        "plate": "", "stock": STOCK, "searchkey": key, "secDate": "", "tdate": "",
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
    for attempt in range(attempts):
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


def main() -> int:
    out = {}
    for label, key in KEYWORDS:
        data = query(key)
        count = int(data.get("totalAnnouncement") or 0)
        items = []
        for item in (data.get("announcements") or [])[:12]:
            title = str(item.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")
            items.append(
                {
                    "title": title,
                    "date": item.get("announcementTime"),
                    "url": f"http://static.cninfo.com.cn/{item.get('adjunctUrl')}",
                }
            )
        out[label] = {"count": count, "items": items}
        print(f"{label}: {count}")
        if items:
            print("  -", items[0]["title"])
        time.sleep(0.2)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入：{OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
