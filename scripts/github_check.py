#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 GitHub Token（短连接 + 重试；只打印账号信息，不打印 Token）。"""

from __future__ import annotations

import http.client
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "github_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")


def get(path: str, attempts: int = 5):
    last = None
    for attempt in range(attempts):
        conn = http.client.HTTPSConnection("api.github.com", 443, timeout=30)
        try:
            conn.request(
                "GET",
                path,
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "User-Agent": "dsh-research",
                    "Accept": "application/vnd.github+json",
                    "Connection": "close",
                },
            )
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.getheaders()), raw
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


try:
    status, headers, raw = get("/user")
    user = json.loads(raw)
    print("status:", status)
    print("login:", user.get("login"))
    print("name:", user.get("name"))
    print("public_repos:", user.get("public_repos"))
    print("scopes:", headers.get("X-OAuth-Scopes"))
except Exception as exc:  # noqa: BLE001
    print("ERROR:", type(exc).__name__, exc)
