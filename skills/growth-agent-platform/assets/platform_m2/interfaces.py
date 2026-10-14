#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 · 接口契约层（准备接口，非运行依赖）

定位：把「为单个客户做的 Agent」升级为「正式架构公司的成长型 Agent」的**接口准备**。
本文件为零依赖 Python（仅 abc / dataclasses / datetime），可直接被未来平台继承。

设计纪律（守返照补强红线）：
  - 先抽接口、不引框架、零依赖保留、红线②守牢（数据主权 per-tenant）。
  - 当前客户交付包保持不动；本文件是乙方侧"准备"，待 M1/M2 落地时把现有腿适配进来。

分层接口（详见返照补强报告第 3 节）：
  IClientProfile      客户配置层（示例客户 = profile_001）
  ICapabilityPlugin   能力插件层（腿1/2/3 = 插件）
  IEventBus           数据/事件层（tenant_id，跨客户看板聚合）
  IMemoryStore        知识/记忆层（progressive disclosure）
  IRedlineGuard       合规红线层（per-tenant 主权/不出门/防跳单）
  IHumanInLoop        人机协同层（转人工/审批/留资）
  IOrchestrator       编排层（调度/重试/超时/可观测）
  IA2AAdapter         Agent 互联适配层（未来 MCP/A2A/AIP）

里程碑映射：M0 现状 → M1 配置化 → M2 插件化 → M3 平台化(多租户) → M4 Agent 网络。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# ===================== 数据契约 =====================
@dataclass
class ClientProfile:
    """客户配置层数据契约：每个客户 = 一个 profile（示例客户 = profile_001）。
    解决「单客户域硬编码」第一卡点——新增客户 = 复制 profile + 换话术库/地域。"""
    tenant_id: str                     # 租户标识（红线② per-tenant 隔离锚点）
    company: str                       # 公司名
    industry: str                      # 行业（如 工业漆/UV胶/工业耗材）
    region: str                        # 主战场（如 示例市/示例省）
    script_lib_path: str               # 话术库路径（Agent Skills 式，可换）
    staging_path: str = ""             # 本租户线索 staging CSV（M2 多租户按租户取数；空=默认脱敏样例）
    staging_schema: List[str] = field(default_factory=lambda: ["评分档位", "地区", "需求信号"])
    redline: Dict[str, Any] = field(default_factory=lambda: {
        "data_sovereignty": True,      # 客户数据主权归客户
        "core_assets_out": False,       # 乙方主表/引擎/管线不出门
        "anti_jump": True,             # 防跳单
    })
    commercial: Dict[str, Any] = field(default_factory=lambda: {
        "setup_fee": [3000, 5000], "monthly": [1500, 2500], "share_pct": [0.05, 0.10],
    })
    dashboard_metrics: List[str] = field(default_factory=lambda: [
        "新增线索", "自动回复", "转人工", "留资", "成交线索", "预估分成",
    ])


@dataclass
class AgentEvent:
    """数据/事件层标准事件：带 tenant_id，使看板可跨客户聚合（解决运营日志宽表无 tenant_id）。"""
    tenant_id: str
    ts: datetime
    leg: str                           # 腿标识（leg1/leg2/leg3）
    metric: str                        # 指标名
    value: float
    meta: Dict[str, Any] = field(default_factory=dict)


# ===================== 接口定义 =====================
class IClientProfile(ABC):
    @abstractmethod
    def load(self, tenant_id: str) -> ClientProfile:
        """按 tenant_id 载入客户配置（未来从加密配置仓/多租户仓读取）。"""


class ICapabilityPlugin(ABC):
    """能力插件接口：腿1/腿2/腿3 实现统一接口。
    新增能力 = 新增一个实现此接口的插件目录（对应行业「Skill 可插拔」）。"""
    name: str = ""

    @abstractmethod
    def init(self, profile: ClientProfile) -> None:
        """绑定客户配置（话术库/地域/红线）。"""

    @abstractmethod
    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """执行本腿能力，返回结构化结果（如线索卡 / 自动回复 / 短信结果）。"""

    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """回报本腿当日指标（喂给 IEventBus → 看板）。"""

    @abstractmethod
    def render_dashboard(self) -> str:
        """产出本腿在看板工作台的图示片段（HTML/SVG 字符串）。"""


class IEventBus(ABC):
    """数据/事件层：统一事件总线（tenant_id 已内嵌 AgentEvent）。
    M3 平台化时替换为多租户持久化实现；M0/M1 可先用本地 CSV/内存。"""
    @abstractmethod
    def publish(self, evt: AgentEvent) -> None: ...

    @abstractmethod
    def query(self, tenant_id: str, leg: Optional[str] = None) -> List[AgentEvent]: ...


class IMemoryStore(ABC):
    """知识/记忆层：话术库/客户知识/盲区雷达，按 progressive disclosure 组织（metadata→body→linked）。"""
    @abstractmethod
    def recall(self, key: str) -> Optional[str]: ...

    @abstractmethod
    def store(self, key: str, value: str, level: int = 1) -> None: ...


class IRedlineGuard(ABC):
    """合规红线层：per-tenant 主权/不出门/防跳单 可插拔校验（对应多租户 ABAC 的朴素版）。"""
    @abstractmethod
    def check(self, profile: ClientProfile, action: Dict[str, Any]) -> tuple[bool, str]:
        """返回 (是否放行, 原因)。任何跨租户/出域动作必须经此闸门。"""


class IHumanInLoop(ABC):
    """人机协同层：转人工 / 审批 / 留资（对应 Anthropic human-in-the-loop guardrail + 75/25）。"""
    @abstractmethod
    def escalate(self, reason: str, payload: Dict[str, Any]) -> str:
        """触发转人工/审批，返回工单号。"""


class IOrchestrator(ABC):
    """编排层：调度插件 / SLA / 重试 / 超时 / 可观测（对应 Anthropic orchestrator + LangGraph 状态机语义）。"""
    @abstractmethod
    def schedule(self, plugins: List[ICapabilityPlugin], ctx: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def observe(self, run_id: str) -> Dict[str, Any]:
        """返回可观测日志（make reasoning explicit / observability）。"""


class IA2AAdapter(ABC):
    """Agent 互联适配层（M4 预留）：未来获客/转化/交付/沉淀 Agent 用 MCP/A2A/AIP 协作。
    当前不实现——仅声明契约，避免超前工程（神：减法优先）。"""
    @abstractmethod
    def discover(self, agent_card_url: str) -> Dict[str, Any]: ...

    @abstractmethod
    def delegate(self, target: str, task: Dict[str, Any]) -> Dict[str, Any]: ...


# ===================== 适配示例（如何把现有腿接进接口） =====================
class Leg1RetrievalPlugin(ICapabilityPlugin):
    """腿1 客户检索 的接口适配骨架（示例，展示"加固"方案如何零改动现有体验）。
    实际 run() 复用现有 周报脚本/线索看板 逻辑；此处只定义契约形状。"""
    name = "leg1_retrieval"

    def init(self, profile: ClientProfile) -> None:
        self.profile = profile
        self.script_lib = profile.script_lib_path

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        # TODO(M2): 调用现有 周报脚本.py / 线索看板.py 逻辑
        return {"status": "ok", "leads": [], "note": "复用腿1 现有实现"}

    def get_metrics(self) -> Dict[str, float]:
        return {"新增线索": 0.0, "留资": 0.0}

    def render_dashboard(self) -> str:
        return "<!-- 腿1 看板片段：线索档位环形 + 区域柱状（复用线索看板.py 输出）-->"


def build_default_profiles() -> Dict[str, ClientProfile]:
    """示例客户配置：profile_001。新增客户在此加一项即可。"""
    sentong = ClientProfile(
        tenant_id="profile_001", company="甲方公司（示例）", industry="工业耗材",
        region="示例市/示例省", script_lib_path="腿2_企微自动回复/话术库.json",
    )
    return {"profile_001": sentong}


if __name__ == "__main__":
    # 自测：接口可实例化、契约可载入（不引框架、零依赖）
    profiles = build_default_profiles()
    p = profiles["profile_001"]
    leg1 = Leg1RetrievalPlugin()
    leg1.init(p)
    print("[OK] 成长型架构接口草图自测通过：")
    print("     客户:", p.company, "| 行业:", p.industry, "| 租户:", p.tenant_id)
    print("     腿1 指标:", leg1.get_metrics())
    print("     红线② 主权归客户:", p.redline["data_sovereignty"], "| 核心资产不出门:", not p.redline["core_assets_out"])
