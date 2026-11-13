#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3：宁德时代、中国中车的债券/担保/授信公告标题扫描。"""

from __future__ import annotations

import http.client
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "20_数据库" / "w3_titles.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"

COMPANIES = [
    {"name": "宁德时代", "code": "300750.SZ", "orgid": "GD165627"},
    {"name": "中国中车", "code": "601766.SH", "orgid": "9900005127"},
]

KEYWORDS = [
    ("债券", "债券"),
    ("募集说明书", "募集说明书"),
    ("担保", "担保"),
    ("授信", "授信"),
    ("银团", "银团"),
    ("并购贷款", "并购贷款"),
    ("募集资金", "募集资金"),
    ("中期票据", "中期票据"),
    ("公司债", "公司债"),
    ("可转债", "可转债"),
    ("ABS", "资产支持证券"),
    ("保理", "保理"),
    ("供应链", "供应链"),
]


class Cninfo:
    def __init__(self) -> None:
        self.conn: http.client.HTTPConnection | None = None
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": UA,
            "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
            "X-Requested-With": "XMLHttpRequest",
        }

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001
                pass
            self.conn = None

    def query(self, stock: str, searchkey: str, page_size: int = 30, attempts: int = 3):
        form = {
            "pageNum": "1", "pageSize": str(page_size), "column": "szse", "tabName": "fulltext",
            "plate": "", "stock": stock, "searchkey": searchkey, "secDate": "", "tdate": "",
            "type": "", "category": "", "trade": "", "seDate": SE_DATE,
            "sortName": "", "sortType": "", "isHLtitle": "true",
        }
        body = urllib.parse.urlencode(form).encode("utf-8")
        for attempt in range(attempts):
            try:
                if self.conn is None:
                    self.conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=25)
                self.conn.request("POST", "/new/hisAnnouncement/query", body=body, headers=self.headers)
                resp = self.conn.getresponse()
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
            except Exception:  # noqa: BLE001
                self.close()
                time.sleep(1.0 * (attempt + 1))
        return {"totalAnnouncement": -1, "announcements": []}


def main() -> int:
    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S%z")
    client = Cninfo()
    out = {"generated_at": generated_at, "companies": {}}

    try:
        for company in COMPANIES:
            stock = f"{company['code'].split('.')[0]},{company['orgid']}"
            out["companies"][company["name"]] = {}
            print(f"\n== {company['name']} ==")
            for label, key in KEYWORDS:
                data = client.query(stock, key)
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
                out["companies"][company["name"]][label] = {"count": count, "items": items}
                print(f"  {label}: {count}")
                if items:
                    print(f"    - {items[0]['title']}")
                time.sleep(0.2)
    finally:
        client.close()

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入：{OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
