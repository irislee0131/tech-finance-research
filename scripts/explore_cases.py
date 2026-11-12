#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选客户池数据探查（Tushare）。

读取 02_案例长名单.csv，对 8 家核心 + 4 家备选做公开数据可得性初筛：
    - 基本信息、行业、实际控制人
    - 2020–2025 年度利润表/资产负债表/财务指标
    - 最新市值、股权质押、前十大股东
    - 研发强度、有息负债率、营收 CAGR
输出：
    20_数据库/case_exploration.json
    20_数据库/case_exploration.csv
    20_数据库/case_raw/{code}.json
"""

from __future__ import annotations

import csv
import http.client
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / "_secrets" / "tushare_token.txt"
CASE_FILE = ROOT / "02_案例长名单.csv"
OUT_JSON = ROOT / "20_数据库" / "case_exploration.json"
OUT_CSV = ROOT / "20_数据库" / "case_exploration.csv"
RAW_DIR = ROOT / "20_数据库" / "case_raw"
ENDPOINT = "https://api.tushare.pro"

ANNUAL_ENDS = {"20201231", "20211231", "20221231", "20231231", "20241231", "20251231"}

INCOME_FIELDS = "ts_code,end_date,ann_date,report_type,revenue,oper_cost,rd_exp,n_income,total_revenue"
BS_FIELDS = "ts_code,end_date,ann_date,report_type,total_assets,st_borr,lt_borr,bond_payable,nca_within_1y,accounts_receiv,inventories"
FI_FIELDS = "ts_code,end_date,debt_to_assets,roe"
BASIC_FIELDS = "ts_code,name,industry,market,list_date,act_name,act_ent_type"
DAILY_FIELDS = "ts_code,trade_date,total_mv,pe_ttm,pb"
HOLDER_FIELDS = "ts_code,end_date,holder_name,hold_ratio"


def post(token: str, api_name: str, params: dict, fields: str = "", timeout: int = 25):
    url = urlparse(ENDPOINT)
    conn = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=timeout)
    payload = json.dumps(
        {"api_name": api_name, "token": token, "params": params, "fields": fields}
    ).encode("utf-8")
    try:
        conn.request(
            "POST",
            url.path or "/",
            body=payload,
            headers={"Content-Type": "application/json", "Connection": "close"},
        )
        resp = conn.getresponse()
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    finally:
        conn.close()


def rows_of(resp: dict) -> list[dict]:
    if resp.get("code") != 0:
        return []
    data = resp.get("data") or {}
    fields = data.get("fields") or []
    return [dict(zip(fields, item)) for item in (data.get("items") or [])]


def annual_rows(token: str, api_name: str, ts_code: str, fields: str) -> list[dict]:
    resp = post(
        token,
        api_name,
        {"ts_code": ts_code, "start_date": "20200101", "end_date": "20261231"},
        fields,
    )
    rows = rows_of(resp)
    keep = []
    for row in rows:
        end = str(row.get("end_date") or "")
        if end not in ANNUAL_ENDS:
            continue
        if row.get("report_type") not in (None, "", "1"):
            continue
        keep.append(row)
    # 同一报告期保留最新公告
    keep.sort(key=lambda r: str(r.get("ann_date") or ""), reverse=True)
    dedup: dict[str, dict] = {}
    for row in keep:
        dedup.setdefault(str(row["end_date"]), row)
    return [dedup[k] for k in sorted(dedup)]


def latest_by_date(rows: list[dict], date_key: str = "end_date") -> dict:
    if not rows:
        return {}
    return max(rows, key=lambda r: str(r.get(date_key) or ""))


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def yi(value):
    """元 -> 亿元"""
    v = num(value)
    return round(v / 1e8, 2) if v is not None else None


def ratio(value):
    v = num(value)
    return round(v, 4) if v is not None else None


def main() -> int:
    token = TOKEN_FILE.read_text(encoding="utf-8-sig").strip().strip('"').strip("'")
    tz = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S%z")

    with CASE_FILE.open(encoding="utf-8-sig", newline="") as f:
        candidates = list(csv.DictReader(f))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    for row in candidates:
        name = row["企业简称"]
        codes = [c.strip() for c in row["证券代码"].split(";") if c.strip()]
        a_code = next((c for c in codes if c.endswith(".SH") or c.endswith(".SZ")), None)
        hk_code = next((c for c in codes if c.endswith(".HK")), None)
        code = a_code or hk_code or ""
        print(f"[{row['推进顺序']}] {name} {code}")

        rec = {
            "序号": row["序号"],
            "推进顺序": row["推进顺序"],
            "企业": name,
            "代码": code,
            "行业": row["所属行业"],
            "所有制": row["所有制"],
            "上市地": row["上市地"],
            "优先级": row["优先级"],
            "备注": row.get("备注", ""),
            "data": {},
            "errors": [],
        }

        if a_code:
            # 基本信息
            basic = rows_of(post(token, "stock_basic", {"ts_code": a_code}, BASIC_FIELDS))
            rec["data"]["stock_basic"] = basic[0] if basic else {}
            time.sleep(0.3)

            company = rows_of(post(token, "stock_company", {"ts_code": a_code}, "ts_code,main_business,province,city,employees"))
            rec["data"]["stock_company"] = company[0] if company else {}
            time.sleep(0.3)

            income = annual_rows(token, "income", a_code, INCOME_FIELDS)
            rec["data"]["income"] = income
            time.sleep(0.3)

            bs = annual_rows(token, "balancesheet", a_code, BS_FIELDS)
            rec["data"]["balancesheet"] = bs
            time.sleep(0.3)

            fi = annual_rows(token, "fina_indicator", a_code, FI_FIELDS)
            rec["data"]["fina_indicator"] = fi
            time.sleep(0.3)

            daily = rows_of(
                post(
                    token,
                    "daily_basic",
                    {"ts_code": a_code, "start_date": "20260101", "end_date": "20261231"},
                    DAILY_FIELDS,
                )
            )
            rec["data"]["daily_basic"] = latest_by_date(daily, "trade_date")
            time.sleep(0.3)

            pledge = rows_of(post(token, "pledge_stat", {"ts_code": a_code}))
            rec["data"]["pledge_stat"] = latest_by_date(pledge)
            time.sleep(0.3)

            holders = rows_of(
                post(
                    token,
                    "top10_holders",
                    {"ts_code": a_code, "start_date": "20250101", "end_date": "20251231"},
                    HOLDER_FIELDS,
                )
            )
            latest_end = max((str(h.get("end_date") or "") for h in holders), default="")
            rec["data"]["top10_holders"] = [
                h for h in holders if str(h.get("end_date") or "") == latest_end
            ]
            time.sleep(0.3)
        else:
            rec["errors"].append("港股标的，A 股接口不适用；需 hk_* 接口或手工补财务")

        records.append(rec)

        raw_file = RAW_DIR / f"{code.replace('.', '_')}.json"
        raw_file.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    # 计算指标
    out_rows = []
    for rec in records:
        data = rec["data"]
        income = data.get("income") or []
        bs = data.get("balancesheet") or []
        fi = data.get("fina_indicator") or []
        basic = data.get("stock_basic") or {}
        daily = data.get("daily_basic") or {}
        pledge = data.get("pledge_stat") or {}

        inc_map = {str(r["end_date"]): r for r in income}
        bs_map = {str(r["end_date"]): r for r in bs}
        years = sorted(set(inc_map) | set(bs_map))
        latest_year = max(years) if years else None
        inc_l = inc_map.get(latest_year, {}) if latest_year else {}
        bs_l = bs_map.get(latest_year, {}) if latest_year else {}

        revenue = num(inc_l.get("revenue"))
        rd_exp = num(inc_l.get("rd_exp"))
        n_income = num(inc_l.get("n_income"))
        total_assets = num(bs_l.get("total_assets"))
        debt_parts = [
            num(bs_l.get("st_borr")),
            num(bs_l.get("lt_borr")),
            num(bs_l.get("bond_payable")),
            num(bs_l.get("nca_within_1y")),
        ]
        interest_debt = sum(v for v in debt_parts if v is not None) if any(v is not None for v in debt_parts) else None

        rd_intensity = (rd_exp / revenue) if (rd_exp is not None and revenue) else None
        debt_ratio = (interest_debt / total_assets) if (interest_debt is not None and total_assets) else None

        # 营收 CAGR：2021 -> 最新年
        rev_2021 = num(inc_map.get("20211231", {}).get("revenue"))
        rev_latest = revenue
        n_years = (int(latest_year[0:4]) - 2021) if latest_year else 0
        cagr = None
        if rev_2021 and rev_latest and n_years > 0:
            cagr = (rev_latest / rev_2021) ** (1 / n_years) - 1

        market_cap = num(daily.get("total_mv"))
        market_cap_yi = round(market_cap / 1e4, 2) if market_cap is not None else None
        pledge_ratio = num(pledge.get("pledge_ratio"))

        # 数据可得性初筛（0–6）
        score = 0
        if len(years) >= 5:
            score += 2
        elif len(years) == 4:
            score += 1
        if rd_exp is not None:
            score += 1
        if market_cap_yi is not None:
            score += 1
        if pledge_ratio is not None:
            score += 1
        if rec["代码"].endswith((".SH", ".SZ")):
            score += 1

        if rd_intensity is None:
            fit = "研发数据缺失"
        elif rd_intensity >= 0.05:
            fit = "达到 5% 门槛"
        elif rd_intensity >= 0.04:
            fit = "略低于 5%，需讨论"
        else:
            fit = "低于 5%，需讨论"

        out_rows.append(
            {
                "序号": rec["序号"],
                "推进顺序": rec["推进顺序"],
                "企业": rec["企业"],
                "代码": rec["代码"],
                "行业": rec["行业"],
                "所有制": rec["所有制"],
                "上市地": rec["上市地"],
                "优先级": rec["优先级"],
                "Tushare行业": basic.get("industry", ""),
                "实际控制人": basic.get("act_name", ""),
                "最新年度": latest_year or "",
                "年报年数": len(years),
                "营收(亿元)": yi(revenue),
                "净利润(亿元)": yi(n_income),
                "研发费用(亿元)": yi(rd_exp),
                "研发强度": ratio(rd_intensity),
                "总资产(亿元)": yi(total_assets),
                "有息负债(亿元)": yi(interest_debt),
                "有息负债率": ratio(debt_ratio),
                "市值(亿元)": market_cap_yi,
                "质押比例": ratio(pledge_ratio),
                "营收CAGR(2021-最新)": ratio(cagr),
                "初筛分(0-6)": score,
                "研发门槛": fit,
                "备注": rec["备注"],
                "错误": "; ".join(rec["errors"]),
            }
        )

    OUT_JSON.write_text(
        json.dumps({"generated_at": generated_at, "records": out_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = list(out_rows[0].keys())
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\n已写入：{OUT_CSV}")
    print(f"已写入：{OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
