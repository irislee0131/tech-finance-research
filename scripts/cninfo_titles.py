#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽查候选企业公告标题，确认公告类型是否可用于银行关系反推。"""

from __future__ import annotations

import http.client
import json
import urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"


def query(stock: str, key: str):
    conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=25)
    form = {
        "pageNum": "1", "pageSize": "10", "column": "szse", "tabName": "fulltext",
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
        "Connection": "close",
    }
    try:
        conn.request("POST", "/new/hisAnnouncement/query", body=body, headers=headers)
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()


from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORGIDS = json.loads((ROOT / "20_数据库" / "cninfo_orgids.json").read_text(encoding="utf-8"))

for label, code, key in [
    ("中国中车-担保", "601766.SH", "担保"),
    ("京东方-募集说明书", "000725.SZ", "募集说明书"),
    ("宁德时代-债券", "300750.SZ", "债券"),
]:
    plain = code.split(".")[0]
    stock = f"{plain},{ORGIDS[plain]}"
    data = query(stock, key)
    print(f"\n== {label} == total={data.get('totalAnnouncement')}")
    for a in (data.get("announcements") or [])[:5]:
        print("  ", a.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""), "|", a.get("adjunctUrl"))
