#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M2 核心：多租户事件总线（写入 events_<tenant>.csv）
+ 跨租户聚合能力（M3 聚合看板的直接数据来源）。

设计纪律：
  - 仅 Python 3 标准库，零依赖。
  - AgentEvent 内嵌 tenant_id，使看板可跨客户聚合（解决 M0 运营日志无 tenant_id）。
  - 每个租户独立 CSV 文件，物理隔离，契合红线②「客户数据主权归客户」。
"""

import csv
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

from interfaces import AgentEvent, IEventBus


class MultiTenantEventBus(IEventBus):
    """每名租户一个 events_<tenant>.csv；支持按目录聚合所有租户事件（M3）。"""

    def __init__(self, tenant_id: str, out_dir: str):
        self.tenant_id = tenant_id
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.events: List[AgentEvent] = []
        self.csv_path = os.path.join(out_dir, "events_%s.csv" % tenant_id)
        self._lock = threading.Lock()  # M4 真实 A2A：Agent 在 HTTP 线程内并发写，需加锁

    def publish(self, evt: AgentEvent) -> None:
        self.events.append(evt)
        with self._lock:
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow([evt.tenant_id, evt.ts.isoformat(), evt.leg, evt.metric, evt.value])

    def query(self, tenant_id: str, leg: Optional[str] = None) -> List[AgentEvent]:
        return [e for e in self.events if e.tenant_id == tenant_id and (leg is None or e.leg == leg)]

    def reset(self) -> None:
        """清空本租户 CSV（演示可重复跑，避免事件无限累加）。"""
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        self.events = []


def aggregate_events(out_dir: str) -> Dict[str, List[AgentEvent]]:
    """扫描 out_dir 下所有 events_*.csv，返回 {tenant_id: [AgentEvent]}。
    这是 M3 多租户看板聚合的入口——新增任何租户只需其 events_<id>.csv 落盘即可被聚合。"""
    result: Dict[str, List[AgentEvent]] = {}
    if not os.path.isdir(out_dir):
        return result
    for fn in sorted(os.listdir(out_dir)):
        if not (fn.startswith("events_") and fn.endswith(".csv")):
            continue
        tid = fn[len("events_"):-len(".csv")]
        path = os.path.join(out_dir, fn)
        rows: List[AgentEvent] = []
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.reader(f):
                if len(r) < 5:
                    continue
                try:
                    ts = datetime.fromisoformat(r[1])
                    val = float(r[4])
                except (ValueError, IndexError):
                    continue
                rows.append(AgentEvent(tenant_id=r[0], ts=ts, leg=r[2], metric=r[3], value=val))
        result[tid] = rows
    return result
