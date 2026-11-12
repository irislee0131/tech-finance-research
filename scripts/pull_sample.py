#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样本拉取：验证 Tushare 财务字段口径（比亚迪 2023/2024）。

用法：
    python scripts/pull_sample.py

输出：
    20_数据库/sample_byd_financials.json
"""

from __future__ import annotations

import http.client
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / "_secrets" / "tushare_token.txt"
OUT_FILE = ROOT / "20_数据库" / "sample_byd_financials.json"
ENDPOINT = "https://api.tushare.pro"
TS_CODE = "002594.SZ"
PERIODS = ["20231231", "20241231"]

INCOME_FIELDS = ["ts_code", "end_date", "total_revenue", "revenue", "oper_cost", "rd_exp", "int_exp", "fin_exp", "n_income"]
BS_FIELDS = ["ts_code", "end_date", "st_borr", "lt_borr", "bond_payable", "nca_within_1y", "accounts_receiv", "notes_receiv", "inventories", "total_assets"]


def post(token: str, api_name: str, params: dict, fields: str, timeout: int = 20):
    url = urlparse(ENDPOINT)
    conn = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=timeout)
    payload = json.dumps(
        {"api_name": api_name, "token": token, "params": params, "fields": fields}
    ).encode("utf-8")
    try:
        conn.request(
            "POST",
            url.path or "/",
            body=payload,
            headers={"Content-Type": "application/json", "Connection": "close"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()
    return data


def main() -> int:
    token = TOKEN_FILE.read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
    out = {"generated_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S%z"), "ts_code": TS_CODE, "records": []}

    for period in PERIODS:
        income = post(token, "income", {"ts_code": TS_CODE, "period": period}, ",".join(INCOME_FIELDS))
        time.sleep(0.4)
        bs = post(token, "balancesheet", {"ts_code": TS_CODE, "period": period}, ",".join(BS_FIELDS))
        time.sleep(0.4)

        def to_dict(resp):
            if resp.get("code") != 0:
                return {"error": resp.get("msg"), "code": resp.get("code")}
            data = resp.get("data") or {}
            fields = data.get("fields") or []
            items = data.get("items") or []
            if not items:
                return {"error": "no rows", "fields": fields}
            return dict(zip(fields, items[0]))

        out["records"].append(
            {"period": period, "income": to_dict(income), "balancesheet": to_dict(bs)}
        )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n已写入：{OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
