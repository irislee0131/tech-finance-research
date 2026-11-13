#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W2：三家股份行公告结构扫描（巨潮资讯）。

统计 2023-01-01 至 2026-11-12 的公告数量，并抓取关键关键词的标题。
输出：
    20_数据库/bank_scan.csv
    20_数据库/bank_scan.json
    20_数据库/bank_titles.json
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
OUT_DIR = ROOT / "20_数据库"
OUT_CSV = OUT_DIR / "bank_scan.csv"
OUT_JSON = OUT_DIR / "bank_scan.json"
OUT_TITLES = OUT_DIR / "bank_titles.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SE_DATE = "2023-01-01~2026-11-12"

COMMON = [
    ("总公告", ""),
    ("年报", "年报"),
    ("半年报", "半年报"),
    ("金融资产投资", "金融资产投资"),
    ("债转股", "债转股"),
    ("科技金融", "科技金融"),
    ("科创", "科创"),
    ("科技型企业", "科技型企业"),
    ("子公司", "子公司"),
    ("协同", "协同"),
    ("集团", "集团"),
    ("投贷联动", "投贷联动"),
    ("并购贷款", "并购贷款"),
    ("承销", "承销"),
    ("投行", "投行"),
]

BANKS = [
    {
        "name": "招商银行",
        "code": "600036.SH",
        "orgid": "gssh0600036",
        "specific": [("投商行", "投商行"), ("财富管理", "财富管理"), ("招银国际", "招银国际"), ("招银投资", "招银投资"), ("招银租赁", "招银租赁"), ("招银理财", "招银理财")],
    },
    {
        "name": "中信银行",
        "code": "601998.SH",
        "orgid": "9900002721",
        "specific": [("联合舰队", "联合舰队"), ("中信金控", "中信金控"), ("信银投资", "信银投资"), ("信银金投", "信银金投"), ("中信证券", "中信证券"), ("中信信托", "中信信托")],
    },
    {
        "name": "兴业银行",
        "code": "601166.SH",
        "orgid": "9900002081",
        "specific": [("商行+投行", "商行+投行"), ("兴业研究", "兴业研究"), ("兴银投资", "兴银投资"), ("兴业信托", "兴业信托"), ("兴业金租", "兴业金租"), ("绿色金融", "绿色金融")],
    },
]

TITLE_KEYS = {"年报", "金融资产投资", "科技金融", "协同", "投商行", "联合舰队", "商行+投行"}


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

    def query(self, stock: str, searchkey: str, page_size: int = 30, attempts: int = 3):
        form = {
            "pageNum": "1",
            "pageSize": str(page_size),
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
                return json.loads(raw)
            except Exception:  # noqa: BLE001
                self.close()
                time.sleep(1.0 * (attempt + 1))
        return {"totalAnnouncement": -1, "announcements": []}


def main() -> int:
    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S%z")
    client = Cninfo()
    rows = []
    titles: dict[str, list] = {}

    try:
        for bank in BANKS:
            stock = f"{bank['code'].split('.')[0]},{bank['orgid']}"
            record = {"银行": bank["name"], "代码": bank["code"], "公告起止": SE_DATE}
            print(f"\n== {bank['name']} ==")
            for label, key in COMMON + bank["specific"]:
                data = client.query(stock, key)
                count = int(data.get("totalAnnouncement") or 0)
                record[label] = count
                if label in TITLE_KEYS:
                    items = []
                    for item in (data.get("announcements") or [])[:8]:
                        title = str(item.get("announcementTitle") or "").replace("<em>", "").replace("</em>", "")
                        items.append(
                            {
                                "title": title,
                                "date": item.get("announcementTime"),
                                "url": f"http://static.cninfo.com.cn/{item.get('adjunctUrl')}",
                            }
                        )
                    titles[f"{bank['name']}::{label}"] = items
                print(f"  {label}: {count}")
                time.sleep(0.2)
            rows.append(record)
    finally:
        client.close()

    OUT_JSON.write_text(
        json.dumps({"generated_at": generated_at, "rows": rows, "titles": titles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_TITLES.write_text(json.dumps(titles, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = ["银行", "代码", "公告起止"] + [label for label, _ in COMMON] + [
        label for bank in BANKS for label, _ in bank["specific"] if label not in {x[0] for x in COMMON}
    ]
    # 不同银行的特有关键词不同，CSV 按并集写，缺省空
    all_specific = []
    for bank in BANKS:
        for label, _ in bank["specific"]:
            if label not in all_specific:
                all_specific.append(label)
    fieldnames = ["银行", "代码", "公告起止"] + [label for label, _ in COMMON] + all_specific
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"\n已写入：{OUT_CSV}")
    print(f"已写入：{OUT_JSON}")
    print(f"已写入：{OUT_TITLES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
