#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PyPI 下载 pypdf wheel 并解压到本地 vendor 目录（短连接 + 重试）。"""

from __future__ import annotations

import http.client
import json
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "20_数据库" / "vendor"
VENDOR.mkdir(parents=True, exist_ok=True)


def fetch(url: str, attempts: int = 6) -> bytes:
    last = None
    parsed = urlparse(url)
    for attempt in range(attempts):
        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=60)
        try:
            path = parsed.path + (("?" + parsed.query) if parsed.query else "")
            conn.request(
                "GET",
                path,
                headers={
                    "User-Agent": "dsh-research",
                    "Accept": "*/*",
                    "Connection": "close",
                },
            )
            resp = conn.getresponse()
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")
            return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


try:
    data = json.loads(fetch("https://pypi.org/pypi/pypdf/json").decode("utf-8"))
except Exception as exc:  # noqa: BLE001
    print("PYPI_ERROR:", type(exc).__name__, exc)
    sys.exit(1)

version = data["info"]["version"]
wheels = [u for u in data.get("urls", []) if u["filename"].endswith(".whl")]
if not wheels:
    print("NO_WHEEL", version)
    sys.exit(1)
wheel = wheels[0]
target = VENDOR / wheel["filename"]
print("version:", version)
print("wheel:", wheel["filename"])
print("size:", wheel.get("size"))

try:
    target.write_bytes(fetch(wheel["url"]))
except Exception as exc:  # noqa: BLE001
    print("DOWNLOAD_ERROR:", type(exc).__name__, exc)
    sys.exit(1)

try:
    with zipfile.ZipFile(target) as zf:
        zf.extractall(VENDOR)
except Exception as exc:  # noqa: BLE001
    print("EXTRACT_ERROR:", type(exc).__name__, exc)
    sys.exit(1)

print("extracted_to:", VENDOR)
print("pypdf_present:", (VENDOR / "pypdf").is_dir())
