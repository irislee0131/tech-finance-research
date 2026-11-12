#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 orgId 测试巨潮公告查询。"""

from __future__ import annotations

import http.client
import json
import urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def query(stock: str, searchkey: str = "", page: int = 1):
    conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=25)
    form = {
        "pageNum": str(page), "pageSize": "30", "column": "szse", "tabName": "fulltext",
        "plate": "", "stock": stock, "searchkey": searchkey, "secDate": "", "tdate": "",
        "type": "", "category": "", "trade": "", "seDate": "2023-01-01~2026-11-12",
        "sortName": "", "sortType": "", "isHLtitle": "true",
    }
    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": UA,
        "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "close",
    }
    try:
        conn.request("POST", "/new/hisAnnouncement/query", body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8", errors="replace")
    finally:
        conn.close()


for label, stock, key in [
    ("宁德-债券", "300750,GD165627", "债券"),
    ("宁德-全部", "300750,GD165627", ""),
    ("中车-债券", "601766,9900005127", "债券"),
    ("比亚迪-债券", "002594,gshk0001211", "债券"),
]:
    status, raw = query(stock, key)
    print(f"\n== {label} == status={status} len={len(raw)}")
    try:
        data = json.loads(raw)
        print("total:", data.get("totalAnnouncement"))
        for a in (data.get("announcements") or [])[:3]:
            print("  ", a.get("announcementTitle"), a.get("adjunctUrl"))
    except Exception:
        print(raw[:300])
