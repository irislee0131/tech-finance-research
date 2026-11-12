#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建 GitHub 仓库（私有，auto_init），或复用已存在的同名仓库。"""

from __future__ import annotations

import http.client
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "github_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
OWNER = "irislee0131"
NAME = "tech-finance-research"
DESCRIPTION = "股份制银行综合经营服务科技龙头企业的模式研究——底稿、数据与报告"


def request(method: str, path: str, payload: dict | None = None, attempts: int = 5):
    last = None
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    for attempt in range(attempts):
        conn = http.client.HTTPSConnection("api.github.com", 443, timeout=30)
        try:
            headers = {
                "Authorization": f"Bearer {TOKEN}",
                "User-Agent": "dsh-research",
                "Accept": "application/vnd.github+json",
                "Connection": "close",
            }
            if body is not None:
                headers["Content-Type"] = "application/json; charset=utf-8"
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


status, raw = request(
    "POST",
    "/user/repos",
    {
        "name": NAME,
        "description": DESCRIPTION,
        "private": True,
        "auto_init": True,
        "has_issues": True,
        "has_wiki": False,
    },
)
print("create_status:", status)

if status not in (200, 201):
    print("create_response:", raw[:500])
    status2, raw2 = request("GET", f"/repos/{OWNER}/{NAME}")
    print("get_status:", status2)
    print("get_response:", raw2[:500])
    if status2 != 200:
        raise SystemExit(1)
    repo = json.loads(raw2)
else:
    repo = json.loads(raw)

print("url:", repo.get("html_url"))
print("default_branch:", repo.get("default_branch"))
print("private:", repo.get("private"))
