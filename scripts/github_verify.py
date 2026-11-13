#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 GitHub 仓库上传结果（不打印 Token）。"""

from __future__ import annotations

import http.client
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "github_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
OWNER = "irislee0131"
REPO = "tech-finance-research"


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
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}: {raw[:300]}")
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


repo = get(f"/repos/{OWNER}/{REPO}")
print("repo:", repo["html_url"])
print("private:", repo["private"])
print("default_branch:", repo["default_branch"])
print("pushed_at:", repo["pushed_at"])

tree = get(f"/repos/{OWNER}/{REPO}/git/trees/{repo['default_branch']}?recursive=1")
paths = [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]
print("files:", len(paths))
print("has_secrets:", any(p.startswith("_secrets/") for p in paths))
print("has_readme:", "README.md" in paths)
for key in [
    "00_研究框架_v2.3.md",
    "05_研究规范_v0.2.md",
    "06_写作规范_v0.2.md",
    "08_报告大纲_v1.md",
    "20_数据库/w3_pilot_relations.csv",
    "30_编码/试点/宁德时代_服务关系.md",
    "30_编码/试点/中国中车_服务关系.md",
    "30_编码/试点/京东方_服务关系.md",
    "30_编码/试点/立讯精密_服务关系.md",
    "90_过程记录/W3_试点报告.md",
    "90_过程记录/W4_第二试点测试.md",
    "90_过程记录/W2_年报补读.md",
    "20_数据库/w2_cmb_summary.csv",
]:
    print(f"{key}:", key in paths)
print("pdf_count:", sum(1 for p in paths if p.lower().endswith(".pdf")))
print("vendor_count:", sum(1 for p in paths if p.startswith("20_数据库/vendor/")))
print("size_kb:", repo.get("size"))
print("top_level:", sorted({p.split('/')[0] for p in paths}))
