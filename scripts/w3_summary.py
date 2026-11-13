#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总 W3 关系：按企业—银行集团—法人去重，输出可读清单。"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "20_数据库" / "w3_relations.csv",
    ROOT / "20_数据库" / "jdf_relations.csv",
]
OUT = ROOT / "20_数据库" / "w3_summary.json"

EXCLUDE_GROUPS = {"非中信系（中信建投）", "非兴业系（兴业证券）", "招商局集团（招商证券）"}


def clean_entity(entity: str) -> str:
    entity = entity.strip()
    entity = re.sub(r"(户名|住所|账号|银行账号|法定代表人|联系人|邮政编码|电话|传真|名称|开户行).*$", "", entity)
    m = re.match(r"^(.*?(?:支行|分行|有限公司|股份有限公司))", entity)
    if m:
        return m.group(1)
    return entity[:30]


def main() -> int:
    buckets = defaultdict(lambda: {"docs": set(), "contexts": [], "levels": set()})
    excluded = defaultdict(lambda: {"docs": set(), "contexts": []})

    for path in FILES:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                company = row["企业"]
                group = row["银行集团"]
                entity = clean_entity(row["法人/品牌"])
                if group in EXCLUDE_GROUPS:
                    excluded[(company, group, entity)]["docs"].add(row["文档"])
                    if len(excluded[(company, group, entity)]["contexts"]) < 2:
                        excluded[(company, group, entity)]["contexts"].append(row["上下文"][:200])
                    continue
                key = (company, group, entity)
                buckets[key]["docs"].add(row["文档"])
                buckets[key]["levels"].add(row["证据等级"])
                if len(buckets[key]["contexts"]) < 2:
                    buckets[key]["contexts"].append(row["上下文"][:220])

    rows = []
    for (company, group, entity), payload in sorted(buckets.items()):
        rows.append(
            {
                "企业": company,
                "银行集团": group,
                "法人": entity,
                "文档数": len(payload["docs"]),
                "文档": sorted(payload["docs"]),
                "证据等级": sorted(payload["levels"]),
                "上下文": payload["contexts"],
            }
        )

    print("=== 计入的关系（去重） ===")
    for row in rows:
        print(f"\n{row['企业']} | {row['银行集团']} | {row['法人']} | 文档 {row['文档数']} | {','.join(row['证据等级'])}")
        for ctx in row["上下文"]:
            print("   ", ctx[:180])

    print("\n=== 排除的关系 ===")
    for (company, group, entity), payload in sorted(excluded.items()):
        print(f"{company} | {group} | {entity} | 文档 {len(payload['docs'])}")

    OUT.write_text(json.dumps({"included": rows, "excluded": [
        {"企业": k[0], "银行集团": k[1], "法人": k[2], "文档数": len(v["docs"])} for k, v in sorted(excluded.items())
    ]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入：{OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
