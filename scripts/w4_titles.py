#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W4：立讯精密、美的集团、比亚迪公告标题扫描，选第二试点。"""

from __future__ import annotations

import http.client
import json
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORGIDS = json.loads((ROOT / "20_数据库" / "cninfo_orgids.json").read_text(encoding="utf-8"))
OUT = ROOT / "20_数据库" / "w4_titles.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"

COMPANIES = [
    ("立讯精密", "002475.SZ"),
    ("美的集团", "000333.SZ"),
    ("比亚迪", "002594.SZ"),
]

KEYWORDS = [
    ("债券", "债券"), ("募集说明书", "募集说明书"), ("担保", "担保"), ("授信", "授信"),
    ("募集资金", "募集资金"), ("公司债", "公司债"), ("中期票据", "中期票据"),
    ("保理", "保理"), ("供应链", "供应链"), ("ABS", "资产支持证券"), ("可转债", "可转债"),
]


def query(stock: str, key: str):
    form = {
        "pageNum": "1", "pageSize": "30", "column": "szse", "tabName": "fulltext",
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


def main() -> int:
    out = {}
    for name, code in COMPANIES:
        plain = code.split(".")[0]
        orgid = ORGIDS.get(plain)
        if not orgid:
            print(f"NO_ORGID {name} {code}")
            continue
        stock = f"{plain},{orgid}"
        out[name] = {}
        print(f"\n== {name} ==")
        for label, key in KEYWORDS:
            data = query(stock, key)
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
            out[name][label] = {"count": count, "items": items}
            print(f"  {label}: {count}")
            if items:
                print("    -", items[0]["title"])
            time.sleep(0.2)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入：{OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
