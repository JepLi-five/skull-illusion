#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M4 核心：A2A / MCP 风格 Agent 协作总线。

内部 获客/转化/交付/沉淀 四个 Agent 经此总线以「消息委托」方式协作，
对应未来 MCP（工具总线）+ A2A（智能体网络）架构，契约直接对齐 interfaces.IA2AAdapter：
  - discover(agent_card_url) → 发现对端 Agent 的能力卡片；
  - delegate(target, task)    → 把任务委托给目标 Agent 的某技能。

当前为进程内本地实现（零依赖），但语义与「智能体互相发现 + 委托任务」一致，
升级时只需把 LocalA2ABus 换成真实 MCP/A2A transport，四个 Agent 的代码不动（神：接口不变）。
"""

from typing import Dict, Any, Callable, List

from interfaces import IA2AAdapter


class AgentCard:
    """Agent 能力卡片（对齐 A2A AgentCard / MCP server 描述）。"""

    def __init__(self, name: str, role: str, skills: List[str]):
        self.name = name
        self.role = role
        self.skills = skills
        self.url: str = ""            # A2A 传输层填充：AgentCard 发布地址
        self.handlers: Dict[str, Callable] = {}

    def add_handler(self, skill: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.handlers[skill] = fn
        return self

    def to_card(self) -> Dict[str, Any]:
        # 真实 A2A AgentCard 形状（对齐 Google A2A：name/url/protocol/skills[]）
        return {
            "name": self.name,
            "role": self.role,
            "url": self.url,
            "protocol": "A2A/0.1",
            "capabilities": {"streaming": False},
            "skills": [{"id": s, "name": s} for s in self.skills],
        }


class LocalA2ABus(IA2AAdapter):
    """进程内 A2A/MCP 总线：register 注册 AgentCard；delegate 按技能路由委托。"""

    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._log: List[Dict[str, Any]] = []  # A2A 协作日志（可观测）

    def register(self, card: AgentCard) -> None:
        self._agents[card.name] = card

    # —— IA2AAdapter 契约 ——
    def discover(self, agent_card_url: str) -> Dict[str, Any]:
        card = self._agents.get(agent_card_url)
        return card.to_card() if card else {}

    def delegate(self, target: str, task: Dict[str, Any]) -> Dict[str, Any]:
        card = self._agents.get(target)
        if not card:
            return {"ok": False, "error": "agent 不存在: %s" % target}
        skill = task.get("skill", "")
        fn = card.handlers.get(skill)
        if not fn:
            return {"ok": False, "error": "%s 无技能 %s" % (target, skill)}
        self._log.append({"from": task.get("from", "?"), "to": target,
                          "skill": skill, "payload_keys": list(task.keys())})
        return fn(task)

    def conversation_log(self) -> List[Dict[str, Any]]:
        return self._log
