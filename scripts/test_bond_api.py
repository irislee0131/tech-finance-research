#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测 Tushare 是否存在可用的公司债接口。"""

from __future__ import annotations

import http.client
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "tushare_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
ENDPOINT = "https://api.tushare.pro"

NAMES = ["bond_basic", "bond_issue", "bond_info", "bond_daily", "bond_maturity", "bond_blk", "bond_share"]


def post(api_name: str):
    url = urlparse(ENDPOINT)
    conn = http.client.HTTPSConnection(url.hostname, 443, timeout=20)
    payload = json.dumps({"api_name": api_name, "token": TOKEN, "params": {"limit": 1}, "fields": ""}).encode("utf-8")
    try:
        conn.request("POST", "/", body=payload, headers={"Content-Type": "application/json", "Connection": "close"})
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()


for name in NAMES:
    r = post(name)
    data = r.get("data") or {}
    print(f"{name:<14} code={r.get('code')} msg={r.get('msg')} fields={data.get('fields')}")
