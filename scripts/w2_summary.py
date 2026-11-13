#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总 W2 年报补读结果，按银行/关键词输出页码与上下文。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "20_数据库" / "w2_annual_evidence.csv"
OUT = ROOT / "20_数据库" / "w2_summary.json"

WANTED = {
    "招商银行": ["科技金融", "科技贷款", "子公司", "招银投资", "招商证券", "集团协同"],
    "中信银行": ["科技金融", "科技贷款", "子公司", "信银金投", "中信证券", "中信信托", "集团协同"],
    "兴业银行": ["科技金融", "科技贷款", "子公司", "兴银投资", "兴业证券", "集团协同"],
}

rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
summary = {}
for bank, keywords in WANTED.items():
    summary[bank] = {}
    print(f"\n######## {bank} ########")
    for kw in keywords:
        matches = [r for r in rows if r["银行"] == bank and r["关键词"] == kw and r["上下文"] != "未找到"]
        summary[bank][kw] = matches[:3]
        print(f"\n== {kw} ({len(matches)}) ==")
        for r in matches[:3]:
            print(f"  p.{r['PDF页码']}: {r['上下文'][:220]}")

OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已写入：{OUT}")
