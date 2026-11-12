#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查候选企业是否发行可转债（cb_basic 全量拉取后按正股过滤）。"""

from __future__ import annotations

import http.client
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "tushare_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
ENDPOINT = "https://api.tushare.pro"
FIELDS = "ts_code,bond_short_name,stk_code,list_date,delist_date,issue_size"

CODES = {
    "002594.SZ": "比亚迪", "300750.SZ": "宁德时代", "688981.SH": "中芯国际",
    "600690.SH": "海尔智家", "601766.SH": "中国中车", "601012.SH": "隆基绿能",
    "300760.SZ": "迈瑞医疗", "000725.SZ": "京东方", "600031.SH": "三一重工",
    "000333.SZ": "美的集团", "002475.SZ": "立讯精密",
}


def post(api_name: str, params: dict):
    url = urlparse(ENDPOINT)
    conn = http.client.HTTPSConnection(url.hostname, 443, timeout=30)
    payload = json.dumps({"api_name": api_name, "token": TOKEN, "params": params, "fields": FIELDS}).encode("utf-8")
    try:
        conn.request("POST", "/", body=payload, headers={"Content-Type": "application/json", "Connection": "close"})
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()


r = post("cb_basic", {"limit": 5000})
data = r.get("data") or {}
fields = data.get("fields") or []
items = [dict(zip(fields, item)) for item in (data.get("items") or [])]
print(f"cb_basic code={r.get('code')} rows={len(items)}")

by_stock = defaultdict(list)
for item in items:
    by_stock[str(item.get("stk_code") or "")].append(item)

for code, name in CODES.items():
    bonds = by_stock.get(code, [])
    print(f"\n{name} {code}: {len(bonds)} 只")
    for b in sorted(bonds, key=lambda x: str(x.get("list_date") or "")):
        print(f"  {b.get('ts_code')} {b.get('bond_short_name')} 上市 {b.get('list_date')} 退市 {b.get('delist_date')} 规模 {b.get('issue_size')}")
