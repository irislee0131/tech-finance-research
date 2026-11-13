#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成可直接双击发送的 .eml 邮件文件。"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "90_过程记录" / "待决策事项_邮件稿.html"
OUT = ROOT / "90_过程记录" / "待决策事项_邮件稿.eml"
SUBJECT = "【研究项目】W2–W4 初稿完成，6 项待决策（2026-11-13）"

html = HTML.read_text(encoding="utf-8")
msg = EmailMessage()
msg["To"] = "20139221@qq.com"
msg["From"] = "20139221@qq.com"
msg["Subject"] = SUBJECT
msg.set_content("请使用支持 HTML 的邮件客户端查看。")
msg.add_alternative(html, subtype="html")
OUT.write_bytes(msg.as_bytes())
print("written:", OUT, "bytes:", OUT.stat().st_size)
