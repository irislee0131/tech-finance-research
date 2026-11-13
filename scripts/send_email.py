#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送“待决策事项”邮件（QQ 邮箱 SMTP）。

前提：
    _secrets/email_smtp.json 存在，字段：
    {
      "host": "smtp.qq.com",
      "port": 465,
      "user": "20139221@qq.com",
      "auth_code": "QQ邮箱授权码",
      "to": "20139221@qq.com",
      "subject": "【研究项目】W2–W4 初稿完成，6 项待决策（2026-11-13）"
    }

用法：
    python scripts/send_email.py
    python scripts/send_email.py --dry-run
"""

from __future__ import annotations

import json
import smtplib
import ssl
import sys
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "_secrets" / "email_smtp.json"
HTML = ROOT / "90_过程记录" / "待决策事项_邮件稿.html"


def main() -> int:
    if not CONFIG.exists():
        print(f"缺少配置文件：{CONFIG}")
        print("请按 _secrets/README.md 的说明，放入 QQ 邮箱授权码后重试。")
        return 2
    if not HTML.exists():
        print(f"缺少邮件正文：{HTML}")
        return 2

    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    html = HTML.read_text(encoding="utf-8")
    subject = cfg.get("subject", "【研究项目】W2–W4 初稿完成，6 项待决策")
    sender = cfg["user"]
    recipient = cfg.get("to", sender)

    print("host:", cfg.get("host", "smtp.qq.com"))
    print("port:", cfg.get("port", 465))
    print("from:", sender)
    print("to:", recipient)
    print("subject:", subject)
    print("html_bytes:", len(html.encode("utf-8")))

    if "--dry-run" in sys.argv:
        print("dry-run: 未发送")
        return 0

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg.get("host", "smtp.qq.com"), int(cfg.get("port", 465)), context=context, timeout=30) as server:
        server.login(sender, cfg["auth_code"])
        server.sendmail(sender, [recipient], msg.as_string())

    print("SENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
