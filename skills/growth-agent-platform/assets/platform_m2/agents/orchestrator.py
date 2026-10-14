#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M4：四 Agent 协作编排。
获客→转化→交付→沉淀 经 A2A 总线串联：仅触发第一个 Agent，链路靠 bus.delegate 自传播，
完整演示「智能体互相发现 + 委托任务」的 MCP/A2A 协作范式。

返回 A2A 协作日志（可观测），链路上的每一步指标也经 _emit 落到 platform_ops 事件总线，
从而被 M3 多租户看板一并聚合。
"""

import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLATFORM_M2 = os.path.normpath(os.path.join(_HERE, ".."))
if _PLATFORM_M2 not in sys.path:
    sys.path.insert(0, _PLATFORM_M2)

from core.a2a import LocalA2ABus  # noqa: E402
from agents.acquisition import AcquisitionAgent  # noqa: E402
from agents.conversion import ConversionAgent  # noqa: E402
from agents.delivery import DeliveryAgent  # noqa: E402
from agents.deposit import DepositAgent  # noqa: E402


def run_agent_pipeline(bus: LocalA2ABus, ops_bus=None) -> List[Dict[str, Any]]:
    # 注册四个 Agent（各自向总线注册 AgentCard）
    AcquisitionAgent(bus, ops_bus)
    ConversionAgent(bus, ops_bus)
    DeliveryAgent(bus, ops_bus)
    DepositAgent(bus, ops_bus)
    # 仅触发获客 Agent，下游由 A2A delegate 自传播（do_acquire 内部用 demo_leads 兜底）
    bus.delegate("agent_acquisition",
                 {"from": "orchestrator", "skill": "acquire"})
    return bus.conversation_log()
