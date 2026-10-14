#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4 Agent③ 交付：方案触达与成交推进。
接收转化 Agent 委托的合格线索，模拟触达（短信/方案）后委托「沉淀 Agent」。
"""

import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)

from agents.base import BaseAgent  # noqa: E402


class DeliveryAgent(BaseAgent):
    name = "agent_delivery"
    role = "交付：方案触达与成交推进"
    skills = ["deliver"]

    def do_deliver(self, task: Dict[str, Any]) -> Dict[str, Any]:
        leads = task.get("leads", [])
        delivered = list(leads)  # 演示：合格线索全部进入交付触达
        self._emit("agent_交付", "交付触达数", float(len(delivered)))
        self.last_result = {"delivered": delivered}
        print("    · 交付 Agent：触达 %d 条（含短信/方案）" % len(delivered))
        return self.bus.delegate("agent_deposit",
                                 {"from": self.name, "skill": "deposit", "leads": delivered})
