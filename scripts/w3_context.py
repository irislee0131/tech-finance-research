#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印关键证据的上下文，供人工核读。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    (ROOT / "14_原始公告" / "宁德时代" / "2026-03-10_annual_2025.txt", "招银国际融资"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-03-10_annual_2025.txt", "招银金租"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-03-10_annual_2025.txt", "兴业银行股份有限公司"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-07-25_07_2026年半年度募集资金存放与使用专项报告.txt", "中信银行股份有限公司宁德分行"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-07-25_07_2026年半年度募集资金存放与使用专项报告.txt", "兴业银行股份有限公司宁德蕉城支行"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-02-10_01_2026年科技创新公司债券_第一期_募集说明书.txt", "招商银行股份有限公司东莞南城支行"),
    (ROOT / "14_原始公告" / "宁德时代" / "2026-02-10_01_2026年科技创新公司债券_第一期_募集说明书.txt", "中信证券股份有限公司"),
    (ROOT / "14_原始公告" / "中国中车" / "2026-03-28_annual_2025.txt", "中信银行股份有限公司"),
]

for path, brand in TARGETS:
    text = path.read_text(encoding="utf-8", errors="replace")
    norm = re.sub(r"\s+", "", text)
    print(f"\n===== {path.name} | {brand} =====")
    count = 0
    start = 0
    while count < 3:
        pos = norm.find(brand, start)
        if pos < 0:
            break
        print(norm[max(0, pos - 160):pos + 260])
        print("---")
        start = pos + len(brand)
        count += 1
    if count == 0:
        print("NOT FOUND")
