#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4 Agent② 转化：线索甄别与培育（MQL 过滤）。
接收获客 Agent 委托的线索，筛出合格线索后委托「交付 Agent」。
"""

import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)

from agents.base import BaseAgent  # noqa: E402


class ConversionAgent(BaseAgent):
    name = "agent_conversion"
    role = "转化：线索甄别与培育"
    skills = ["convert"]

    def do_convert(self, task: Dict[str, Any]) -> Dict[str, Any]:
        leads = task.get("leads", [])
        qualified = [l for l in leads if l.get("score", 0) >= 70]  # 评分≥70 判为 MQL
        self._emit("agent_转化", "合格线索数", float(len(qualified)))
        self.last_result = {"qualified": qualified}
        print("    · 转化 Agent：合格(MQL) %d 条" % len(qualified))
        return self.bus.delegate("agent_delivery",
                                 {"from": self.name, "skill": "deliver", "leads": qualified})
