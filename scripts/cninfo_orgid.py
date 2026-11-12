#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""获取巨潮 orgId 并测试公告查询。"""

from __future__ import annotations

import http.client
import json
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


for url in [
    "http://www.cninfo.com.cn/new/data/szse_stock.json",
    "http://www.cninfo.com.cn/new/data/sse_stock.json",
]:
    try:
        data = get_json(url)
        items = data.get("stockList") or data.get("stockList") or []
        print(url, "items", len(items))
        for item in items[:1]:
            print("sample", item)
        for item in items:
            if str(item.get("code")) in {"300750", "601766", "002594"}:
                print("FOUND", item)
    except Exception as exc:
        print(url, "ERROR", type(exc).__name__, exc)
