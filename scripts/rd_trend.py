#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按年度计算候选企业研发强度（研发费用/营业收入），用于判断 5% 门槛的稳健性。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "20_数据库" / "case_raw"

rows = []
for path in sorted(RAW.glob("*.json")):
    rec = json.loads(path.read_text(encoding="utf-8"))
    name = rec.get("企业")
    income = rec.get("data", {}).get("income") or []
    by_year = {}
    for item in income:
        end = str(item.get("end_date") or "")
        if not end.endswith("1231"):
            continue
        rev = item.get("revenue")
        rd = item.get("rd_exp")
        if rev and rd is not None:
            by_year[end[:4]] = float(rd) / float(rev)
    rows.append((name, by_year))

years = ["2021", "2022", "2023", "2024", "2025"]
print("企业".ljust(8), "  ".join(years), "  2023-25均值")
for name, by_year in rows:
    vals = [by_year.get(y) for y in years]
    recent = [v for v in vals[-3:] if v is not None]
    avg = sum(recent) / len(recent) if recent else None
    cells = [f"{v*100:5.2f}%" if v is not None else "  n/a " for v in vals]
    avg_s = f"{avg*100:5.2f}%" if avg is not None else "  n/a "
    print(str(name).ljust(10), " ".join(cells), "  ", avg_s)
