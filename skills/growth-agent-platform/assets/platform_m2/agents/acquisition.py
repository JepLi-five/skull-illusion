#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4 Agent① 获客：线索发现与采集。
演示数据取自脱敏样例（不碰乙方 1.2 万家主表），产出线索后经 A2A 总线委托「转化 Agent」。
"""

import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)

from agents.base import BaseAgent  # noqa: E402


class AcquisitionAgent(BaseAgent):
    name = "agent_acquisition"
    role = "获客：线索发现与采集"
    skills = ["acquire"]

    def demo_leads(self) -> List[Dict[str, Any]]:
        # 脱敏演示线索（非乙方主表，非任何客户真实数据）
        return [
            {"name": "示例市A某制造A", "region": "示例市A", "signal": "询产品规格参数", "score": 88},
            {"name": "示例市B某装备B", "region": "示例市B", "signal": "多型号比价", "score": 72},
            {"name": "示例市C某精密C", "region": "示例市C", "signal": "试样申请", "score": 65},
            {"name": "示例市D某结构件D", "region": "示例市D", "signal": "招标咨询", "score": 80},
            {"name": "示例市E某配件E", "region": "示例市E", "signal": "微信咨询", "score": 55},
        ]

    def do_acquire(self, task: Dict[str, Any]) -> Dict[str, Any]:
        leads = task.get("leads") or self.demo_leads()
        self._emit("agent_获客", "线索数", float(len(leads)))
        self.last_result = {"leads": leads}
        print("    · 获客 Agent：采集线索 %d 条" % len(leads))
        # 经 A2A 总线委托下游「转化 Agent」
        return self.bus.delegate("agent_conversion",
                                 {"from": self.name, "skill": "convert", "leads": leads})
