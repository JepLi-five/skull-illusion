#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M5 核心：明账账本（红线③ 之「明账」）。

每租户一本**双时态流水账**：每条记录同时带
  - event_date  业务发生日（变动时间线锚·业务侧）
  - recorded_at 落账时刻（变动时间线锚·系统侧）
对应「变动必带时间线锚」纪律——任何账目变动都可追新鲜度，不知何时=不知真假。

零依赖（csv / datetime）；红线②：账本只记本租户的明账流水，不碰乙方核心资产。
"""

import os
import csv
from datetime import datetime
from typing import Dict, List


class TenantLedger:
    COLS = ["tenant_id", "event_date", "recorded_at", "kind", "amount", "deal_ref", "note"]

    def __init__(self, tenant_id: str, ledger_dir: str):
        self.tenant_id = tenant_id
        self.path = os.path.join(ledger_dir, "ledger_%s.csv" % tenant_id)
        self.rows: List[List[str]] = []
        os.makedirs(ledger_dir, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8", newline="") as f:
                for r in csv.reader(f):
                    if r and r[0] == self.tenant_id:
                        self.rows.append(r)

    def add(self, event_date: str, kind: str, amount: float,
            note: str = "", deal_ref: str = "") -> List[str]:
        recorded = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        row = [self.tenant_id, event_date, recorded, kind, "%.2f" % float(amount), deal_ref, note]
        self.rows.append(row)
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(row)
        return row

    def summary(self) -> Dict[str, float]:
        leads = sum(1 for r in self.rows if r[3] == "线索成本")
        deals = sum(1 for r in self.rows if r[3] == "成交金额")
        deal_amt = sum(float(r[4]) for r in self.rows if r[3] == "成交金额")
        share = sum(float(r[4]) for r in self.rows if r[3] == "预估分成")
        cost = sum(float(r[4]) for r in self.rows if r[3] == "线索成本")
        alerts = sum(1 for r in self.rows if r[3] == "防跳单告警")
        return {"leads": leads, "deals": deals, "deal_amount": deal_amt,
                "share": share, "cost": cost, "net": share - cost, "alerts": alerts}
