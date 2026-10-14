#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M5 核心：防跳单闸门（红线③ 之「防跳单」）。

逻辑（对齐《AI_Agent定制代运营与线索共享合作协议》防跳单条款）：
  1. 留痕 —— 记录 Agent 首次触达每个客户的日期（footprint）。
  2. 校验 —— 成交时检查该客户是否在排他期内、且被归因到非 Agent 渠道。
  3. 告警 —— 排他期（协议 24 个月）内、归因"direct/other/self"即判跳单嫌疑，
            写入账本并产出可上报告警（965 留痕 + 排他 24 个月 + 违约金的依据）。

零依赖；仅做判定与留痕，不替代法律条款——给甲方一张"系统帮你盯跳单"的透明证据网。
"""

from datetime import date
from typing import Dict, List, Optional


class AntiJumpGate:
    EXCLUSIVITY_MONTHS = 24  # 协议排他期（月）

    def __init__(self, tenant_id: str, ledger):
        self.tenant_id = tenant_id
        self.ledger = ledger
        self.contacts: Dict[str, date] = {}     # customer_ref -> 首次触达日
        self.alerts: List[Dict[str, str]] = []

    def record_contact(self, customer_ref: str, first_contact: date) -> None:
        """留痕：记录 Agent 首次触达（同一客户只记最早一次）。"""
        if customer_ref not in self.contacts:
            self.contacts[customer_ref] = first_contact

    def check_deal(self, deal_ref: str, customer_ref: str,
                   deal_date: date, channel: str) -> Optional[Dict[str, str]]:
        """校验成交：非 Agent 渠道 + 排他期内首次触达 = 跳单嫌疑。"""
        fc = self.contacts.get(customer_ref)
        if fc and channel in ("direct", "other", "self"):
            months = (deal_date.year - fc.year) * 12 + (deal_date.month - fc.month)
            if months <= self.EXCLUSIVITY_MONTHS:
                alert = {
                    "deal": deal_ref, "customer": customer_ref,
                    "first_contact": fc.isoformat(), "deal_date": deal_date.isoformat(),
                    "type": "跳单嫌疑",
                }
                self.alerts.append(alert)
                self.ledger.add(deal_date.isoformat()[:10], "防跳单告警", 0.0,
                               "跳单嫌疑: %s 排他期内成交却归因非Agent渠道(%s)" % (customer_ref, channel),
                               deal_ref)
                return alert
        return None

    def report(self) -> List[Dict[str, str]]:
        return self.alerts
