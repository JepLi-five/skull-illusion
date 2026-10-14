#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4 Agent 基类：每个内部 Agent = 一个技能处理器 + 一张 AgentCard，注册到 A2A 总线。
提供 _emit 把自身指标写入事件总线（供 M3 跨租户聚合），从而把「Agent 网络」也纳入统一看板。
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)
sys.path.insert(0, _PLATFORM_M2)  # 契约层 interfaces.py 已内置 platform_m2 根目录（_PLATFORM_M2 即 platform_m2）

from interfaces import AgentEvent  # noqa: E402
from core.a2a import AgentCard, LocalA2ABus  # noqa: E402


class BaseAgent:
    """内部 Agent 基类：注册自身能力卡片，按 skill 派发到 do_<skill> 方法。"""

    name = ""
    role = ""
    skills: list = []

    def __init__(self, bus: LocalA2ABus, ops_bus=None):
        self.bus = bus
        self.ops_bus = ops_bus          # 事件总线（tenant=platform_ops），用于把指标喂给 M3 看板
        self.card = AgentCard(self.name, self.role, list(self.skills))
        for sk in self.skills:
            self.card.add_handler(sk, self._dispatch)
        self.bus.register(self.card)
        self.last_result: Dict[str, Any] = {}

    def _dispatch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        skill = task.get("skill", "")
        method = getattr(self, "do_%s" % skill, None)
        if method is None:
            return {"ok": False, "error": "未实现技能 %s" % skill}
        return method(task)

    def _emit(self, leg: str, metric: str, value: float) -> None:
        if self.ops_bus is not None:
            self.ops_bus.publish(AgentEvent(
                tenant_id=self.ops_bus.tenant_id, ts=datetime.now(),
                leg=leg, metric=metric, value=value))

    def run_local(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return self._dispatch(task)
