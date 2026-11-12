#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试港股接口是否可用（小米 1810.HK）。"""

from __future__ import annotations

import http.client
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "tushare_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
ENDPOINT = "https://api.tushare.pro"


def post(api_name: str, params: dict, fields: str = ""):
    url = urlparse(ENDPOINT)
    conn = http.client.HTTPSConnection(url.hostname, 443, timeout=25)
    payload = json.dumps({"api_name": api_name, "token": TOKEN, "params": params, "fields": fields}).encode("utf-8")
    try:
        conn.request("POST", "/", body=payload, headers={"Content-Type": "application/json", "Connection": "close"})
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()


for api, params in [
    ("hk_basic", {"ts_code": "1810.HK"}),
    ("hk_income", {"ts_code": "1810.HK", "start_date": "20200101", "end_date": "20261231"}),
    ("hk_balancesheet", {"ts_code": "1810.HK", "start_date": "20200101", "end_date": "20261231"}),
]:
    r = post(api, params)
    data = r.get("data") or {}
    print(f"\n== {api} == code={r.get('code')} msg={r.get('msg')}")
    print("fields:", data.get("fields"))
    items = data.get("items") or []
    print("rows:", len(items))
    if items:
        print("first:", dict(zip(data.get("fields") or [], items[0])))
