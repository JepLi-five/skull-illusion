#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4 Agent④ 沉淀：知识资产与客户沉淀。
接收交付 Agent 委托的线索，归档到平台内部记忆（本地 JSON），完结整条 A2A 链路。
"""

import os
import sys
import json
from datetime import datetime
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)

from agents.base import BaseAgent  # noqa: E402


class DepositAgent(BaseAgent):
    name = "agent_deposit"
    role = "沉淀：知识资产与客户沉淀"
    skills = ["deposit"]

    def do_deposit(self, task: Dict[str, Any]) -> Dict[str, Any]:
        leads = task.get("leads", [])
        # 沉淀：写入平台内部记忆（演示写本地 JSON，非客户数据、非乙方主表）
        out = os.path.join(_PLATFORM_M2, "deposit_memory.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"ts": datetime.now().isoformat(), "leads": leads},
                      f, ensure_ascii=False, indent=2)
        self._emit("agent_沉淀", "沉淀客户数", float(len(leads)))
        self.last_result = {"deposited": leads}
        print("    · 沉淀 Agent：归档 %d 条至内部记忆" % len(leads))
        return {"ok": True, "deposited": len(leads),
                "pipeline": "获客→转化→交付→沉淀 已闭环"}
