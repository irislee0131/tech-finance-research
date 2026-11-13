#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub Git Data API 上传项目文件（无需本地 git）。

排除：_secrets/、__pycache__/、.git/、*.pyc、*.db、*.sqlite、~$*。
"""

from __future__ import annotations

import base64
import http.client
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (ROOT / "_secrets" / "github_token.txt").read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
OWNER = "irislee0131"
REPO = "tech-finance-research"
BRANCH = "main"
MESSAGE = "W2-W4 first drafts: status memo and pending decisions email"

EXCLUDE_DIRS = {"_secrets", "__pycache__", ".git", "vendor", "w2_annual_text"}
EXCLUDE_SUFFIXES = {".pyc", ".db", ".db-journal", ".sqlite", ".log", ".pdf"}
EXCLUDE_NAMES = {"Thumbs.db", "desktop.ini"}


def api(method: str, path: str, payload: dict | None = None, attempts: int = 5):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    last = None
    for attempt in range(attempts):
        conn = http.client.HTTPSConnection("api.github.com", 443, timeout=60)
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
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}: {raw[:400]}")
            return json.loads(raw) if raw else {}
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(last)


def collect_files():
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        if path.name in EXCLUDE_NAMES or path.name.startswith("~$"):
            continue
        files.append((path.relative_to(ROOT).as_posix(), path))
    return files


def main() -> int:
    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    head_sha = ref["object"]["sha"]
    commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head_sha}")
    base_tree = commit["tree"]["sha"]
    print("head:", head_sha)
    print("base_tree:", base_tree)

    files = collect_files()
    print("files:", len(files))

    tree_entries = []
    for index, (rel, path) in enumerate(files, 1):
        content = base64.b64encode(path.read_bytes()).decode("ascii")
        blob = api(
            "POST",
            f"/repos/{OWNER}/{REPO}/git/blobs",
            {"content": content, "encoding": "base64"},
        )
        tree_entries.append(
            {"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]}
        )
        if index % 10 == 0:
            print(f"uploaded blobs: {index}/{len(files)}")
        time.sleep(0.15)

    tree = api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        {"base_tree": base_tree, "tree": tree_entries},
    )
    print("tree:", tree["sha"])

    new_commit = api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {"message": MESSAGE, "tree": tree["sha"], "parents": [head_sha]},
    )
    print("commit:", new_commit["sha"])

    api(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
        {"sha": new_commit["sha"], "force": False},
    )
    print("ref updated:", f"https://github.com/{OWNER}/{REPO}/commit/{new_commit['sha']}")
    print("repo:", f"https://github.com/{OWNER}/{REPO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
