#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选企业公告结构扫描（巨潮资讯，长连接版）。

对 8 家核心 + 4 家备选，统计 2023-01-01 至 2026-11-12 的公告数量。
输出：
    20_数据库/cninfo_scan.csv
    20_数据库/cninfo_scan.json
    20_数据库/cninfo_orgids.json（缓存）
"""

from __future__ import annotations

import csv
import http.client
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_FILE = ROOT / "02_案例长名单.csv"
OUT_DIR = ROOT / "20_数据库"
OUT_CSV = OUT_DIR / "cninfo_scan.csv"
OUT_JSON = OUT_DIR / "cninfo_scan.json"
ORGID_CACHE = OUT_DIR / "cninfo_orgids.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"

KEYWORDS = [
    ("总公告", ""),
    ("债券", "债券"),
    ("中期票据", "中期票据"),
    ("超短融", "超短期融资券"),
    ("公司债", "公司债"),
    ("可转债", "可转债"),
    ("担保", "担保"),
    ("授信", "授信"),
    ("银团", "银团"),
    ("并购贷款", "并购贷款"),
    ("募集说明书", "募集说明书"),
    ("委托理财", "委托理财"),
    ("ABS", "资产支持证券"),
    ("应收账款", "应收账款"),
    ("供应链", "供应链"),
]


def fetch_orgids() -> dict[str, str]:
    if ORGID_CACHE.exists():
        return json.loads(ORGID_CACHE.read_text(encoding="utf-8"))
    last_error = None
    for attempt in range(4):
        conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=30)
        try:
            conn.request(
                "GET",
                "/new/data/szse_stock.json",
                headers={"User-Agent": UA, "Connection": "close"},
            )
            resp = conn.getresponse()
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            mapping = {
                str(item.get("code")): str(item.get("orgId"))
                for item in (data.get("stockList") or [])
            }
            ORGID_CACHE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
            return mapping
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        finally:
            conn.close()
    raise RuntimeError(f"获取 orgId 失败：{last_error}")


class Cninfo:
    def __init__(self) -> None:
        self.conn: http.client.HTTPConnection | None = None
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": UA,
            "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
            "X-Requested-With": "XMLHttpRequest",
        }

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001
                pass
            self.conn = None

    def query(self, stock: str, searchkey: str, attempts: int = 3) -> int:
        form = {
            "pageNum": "1",
            "pageSize": "30",
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": stock,
            "searchkey": searchkey,
            "secDate": "",
            "tdate": "",
            "type": "",
            "category": "",
            "trade": "",
            "seDate": SE_DATE,
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        body = urllib.parse.urlencode(form).encode("utf-8")
        for attempt in range(attempts):
            try:
                if self.conn is None:
                    self.conn = http.client.HTTPConnection("www.cninfo.com.cn", 80, timeout=25)
                self.conn.request("POST", "/new/hisAnnouncement/query", body=body, headers=self.headers)
                resp = self.conn.getresponse()
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return int(data.get("totalAnnouncement") or 0)
            except Exception:  # noqa: BLE001
                self.close()
                time.sleep(1.0 * (attempt + 1))
        return -1


def main() -> int:
    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S%z")

    with CASE_FILE.open(encoding="utf-8-sig", newline="") as f:
        candidates = list(csv.DictReader(f))
    orgids = fetch_orgids()
    print(f"orgId 映射：{len(orgids)} 条")

    client = Cninfo()
    rows = []
    try:
        for row in candidates:
            name = row["企业简称"]
            codes = [c.strip() for c in row["证券代码"].split(";") if c.strip()]
            a_code = next((c for c in codes if c.endswith(".SH") or c.endswith(".SZ")), None)
            if not a_code:
                print(f"[SKIP] {name}：无 A 股代码")
                rows.append({"企业": name, "代码": row["证券代码"], "备注": "港股，公告体系不同"})
                continue

            plain = a_code.split(".")[0]
            orgid = orgids.get(plain)
            if not orgid:
                print(f"[SKIP] {name} {a_code}：未找到 orgId")
                rows.append({"企业": name, "代码": a_code, "备注": "未找到 orgId"})
                continue

            stock = f"{plain},{orgid}"
            record = {"企业": name, "代码": a_code, "公告起止": SE_DATE}
            for label, key in KEYWORDS:
                record[label] = client.query(stock, key)
                time.sleep(0.2)
            rows.append(record)
            print(
                f"[OK] {name:<6} 总={record.get('总公告')} 债券={record.get('债券')} "
                f"担保={record.get('担保')} 授信={record.get('授信')} "
                f"募集={record.get('募集说明书')} 银团={record.get('银团')}"
            )
    finally:
        client.close()

    OUT_JSON.write_text(
        json.dumps({"generated_at": generated_at, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = ["企业", "代码", "公告起止"] + [label for label, _ in KEYWORDS] + ["备注"]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"\n已写入：{OUT_CSV}")
    print(f"已写入：{OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
