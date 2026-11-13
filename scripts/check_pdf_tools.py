#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查可用的 PDF 解析库。"""

mods = ["pypdf", "PyPDF2", "pdfminer", "fitz", "pdfplumber"]
for name in mods:
    try:
        __import__(name)
        print(name, "OK")
    except Exception as exc:  # noqa: BLE001
        print(name, "NO", type(exc).__name__)
