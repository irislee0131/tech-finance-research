#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tushare 权限探测脚本（仅使用 Python 标准库，无需安装 tushare 包）。

用法：
    python scripts/tushare_probe.py

行为：
    1. 从 _secrets/tushare_token.txt 读取 Token；
    2. 逐个调用候选接口，记录返回码、字段、行数、耗时；
    3. 结果写入 20_数据库/tushare_capability.json，并在终端打印摘要。

说明：
    - Token 只发送给 Tushare 官方接口，不写入输出文件；
    - 返回 code=0 表示可用；非 0 时记录 msg，区分"无权限/参数不符/限频"；
    - 网络错误自动重试 3 次，使用短连接避免本地端口复用问题；
    - 探测用小样本（limit=1），不消耗大量积分。
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / "_secrets" / "tushare_token.txt"
OUT_DIR = ROOT / "20_数据库"
OUT_FILE = OUT_DIR / "tushare_capability.json"

ENDPOINTS = [
    "https://api.tushare.pro",
    "http://api.tushare.pro",
]

# 每个接口给一个最小合法参数，避免把"参数错误"误判为"无权限"
PROBES: list[tuple[str, dict]] = [
    ("stock_basic", {"list_status": "L", "limit": 1}),
    ("stock_company", {"ts_code": "002594.SZ"}),
    ("income", {"ts_code": "002594.SZ", "limit": 1}),
    ("balancesheet", {"ts_code": "002594.SZ", "limit": 1}),
    ("cashflow", {"ts_code": "002594.SZ", "limit": 1}),
    ("fina_indicator", {"ts_code": "002594.SZ", "limit": 1}),
    ("fina_mainbz", {"ts_code": "002594.SZ", "limit": 1}),
    ("forecast", {"ts_code": "002594.SZ", "limit": 1}),
    ("express", {"ts_code": "002594.SZ", "limit": 1}),
    ("top10_holders", {"ts_code": "002594.SZ", "limit": 1}),
    ("top10_floatholders", {"ts_code": "002594.SZ", "limit": 1}),
    ("stk_holdernumber", {"ts_code": "002594.SZ", "limit": 1}),
    ("pledge_stat", {"ts_code": "002594.SZ", "limit": 1}),
    ("stk_holdertrade", {"ts_code": "002594.SZ", "limit": 1}),
    ("dividend", {"ts_code": "002594.SZ", "limit": 1}),
    ("repurchase", {"ts_code": "002594.SZ", "limit": 1}),
    ("daily", {"ts_code": "002594.SZ", "limit": 1}),
    ("daily_basic", {"ts_code": "002594.SZ", "limit": 1}),
    ("block_trade", {"ts_code": "002594.SZ", "limit": 1}),
    ("cb_basic", {"limit": 1}),
    ("cb_issue", {"limit": 1}),
    ("sf_month", {"limit": 1}),
    ("cn_m", {"limit": 1}),
    ("cn_gdp", {"limit": 1}),
    ("cn_pmi", {"limit": 1}),
    ("shibor", {"limit": 1}),
    ("shibor_lpr", {"limit": 1}),
    ("index_basic", {"limit": 1}),
    ("fund_basic", {"limit": 1}),
    ("anns_d", {"ts_code": "002594.SZ", "limit": 1}),
    ("news", {"limit": 1}),
]


def _post(endpoint: str, token: str, api_name: str, params: dict, timeout: int = 20):
    url = urlparse(endpoint)
    if url.scheme == "https":
        conn = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=timeout)
    else:
        conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=timeout)

    payload = json.dumps(
        {"api_name": api_name, "token": token, "params": params, "fields": ""}
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "Connection": "close"}
    started = time.time()
    try:
        conn.request("POST", url.path or "/", body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", errors="replace")
    finally:
        conn.close()
    latency = round((time.time() - started) * 1000)
    return json.loads(raw), latency


def probe_one(token: str, api_name: str, params: dict, attempts: int = 3) -> dict:
    last_error = None
    for attempt in range(attempts):
        for endpoint in ENDPOINTS:
            try:
                data, latency = _post(endpoint, token, api_name, params)
                code = data.get("code")
                payload = data.get("data") or {}
                items = payload.get("items") or []
                fields = payload.get("fields") or []
                return {
                    "api_name": api_name,
                    "ok": code == 0,
                    "code": code,
                    "msg": data.get("msg"),
                    "rows": len(items),
                    "fields": fields,
                    "latency_ms": latency,
                    "endpoint": endpoint,
                }
            except (urllib.error.URLError, ConnectionError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            except json.JSONDecodeError as exc:
                last_error = f"JSONDecodeError: {exc}"
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
        if attempt < attempts - 1:
            time.sleep(1.0 * (attempt + 1))
    return {
        "api_name": api_name,
        "ok": False,
        "code": None,
        "msg": last_error,
        "rows": 0,
        "fields": [],
        "latency_ms": None,
        "endpoint": None,
    }


def main() -> int:
    if not TOKEN_FILE.exists():
        print(f"[ERROR] 未找到 Token 文件：{TOKEN_FILE}")
        print("请按 _secrets/README.md 的说明创建。")
        return 2

    token = TOKEN_FILE.read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
    if not token:
        print(f"[ERROR] Token 文件为空：{TOKEN_FILE}")
        return 2

    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S%z")

    results = []
    for api_name, params in PROBES:
        result = probe_one(token, api_name, params)
        results.append(result)
        flag = "OK " if result["ok"] else "ERR"
        print(
            f"[{flag}] {api_name:<20} code={result['code']} "
            f"rows={result['rows']} fields={len(result['fields'])} "
            f"msg={result['msg']}"
        )
        time.sleep(0.5)  # 温和限频

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": generated_at,
        "token_file": str(TOKEN_FILE.relative_to(ROOT)),
        "endpoint_used": next((r["endpoint"] for r in results if r["endpoint"]), None),
        "total": len(results),
        "ok_count": sum(1 for r in results if r["ok"]),
        "results": results,
    }
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n可用接口：{payload['ok_count']}/{payload['total']}")
    print(f"结果已写入：{OUT_FILE}")
    return 0 if payload["ok_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
