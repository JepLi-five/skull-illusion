#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 · M2 / M3 / M4 一体化落地入口（零依赖）。

里程碑落地：
  M2 热插拔  —— 三条腿拆为 plugins/<leg>/plugin.py 独立目录，discover_plugins 自动加载；
               新增客户 = PROFILES 加一项 + 其 events 落盘。
  M3 聚合    —— 各租户 + M4 Agent 网络事件写入 events_<tenant>.csv，multi_tenant_dashboard 聚合成跨租户看板。
  M4 协作    —— 内部 获客/转化/交付/沉淀 四 Agent 经 LocalA2ABus(A2A/MCP) 串联，链路指标也进 M3 看板。

红线②全程守牢：客户交付包只读引用，从不改写；
核心资产（主表/评分引擎/采集管线）不出现于本目录。
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

HERE = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.normpath(HERE)  # 契约层 interfaces.py 已内置 platform_m2 根目录
CLIENT_PKG = os.path.normpath(os.path.join(HERE, "template_assets"))  # 演示资产已内置
sys.path.insert(0, INTERFACE_DIR)
sys.path.insert(0, HERE)

from interfaces import ClientProfile, AgentEvent  # noqa: E402
from core.event_bus import MultiTenantEventBus  # noqa: E402
from core.discoverer import discover_plugins  # noqa: E402
from core.redline import SimpleRedlineGuard  # noqa: E402
from core.a2a import LocalA2ABus  # noqa: E402
from agents.orchestrator import run_agent_pipeline  # noqa: E402
from multi_tenant_dashboard import build_dashboard  # noqa: E402

PLUGINS_ROOT = os.path.join(HERE, "plugins")
EVENTS_DIR = os.path.join(HERE, "events")
TENANTS_DIR = os.path.join(HERE, "tenants")
LEG1 = os.path.join(CLIENT_PKG, "腿1_线索检索")
LEG2 = os.path.join(CLIENT_PKG, "腿2_企微自动回复")

# M2 配置化：内置示例租户 = profile_001；演示租户 = profile_002（独立脱敏 staging，绝不用乙方主表）
PROFILES: Dict[str, ClientProfile] = {
    "profile_001": ClientProfile(
        tenant_id="profile_001", company="甲方公司A（示例）", industry="工业耗材",
        region="示例市/示例省",
        script_lib_path=os.path.join(LEG2, "话术库.json"),
        staging_path=os.path.join(LEG1, "staging示例_脱敏10家.csv"),
    ),
    "profile_002": ClientProfile(
        tenant_id="profile_002", company="演示租户·示例公司B（样例）", industry="工业耗材",
        region="示例市A/示例市B",
        script_lib_path=os.path.join(LEG2, "话术库.json"),
        staging_path=os.path.join(TENANTS_DIR, "profile_002", "staging_脱敏样例.csv"),
    ),
}


def _reset_events():
    if os.path.isdir(EVENTS_DIR):
        for fn in os.listdir(EVENTS_DIR):
            if fn.startswith("events_") and fn.endswith(".csv"):
                os.remove(os.path.join(EVENTS_DIR, fn))


def _run_tenant(tenant_id: str, profiles: dict = None):
    profiles = profiles if profiles is not None else PROFILES
    profile = profiles[tenant_id]
    bus = MultiTenantEventBus(tenant_id, EVENTS_DIR)
    guard = SimpleRedlineGuard()
    ok, why = guard.check(profile, {"cross_tenant": False, "touch_core_assets": False})
    if not ok:
        print("    [红线拦截]", why)
        return [], bus
    # M2 热插拔：从 plugins/ 自动发现并加载三腿
    plugins = discover_plugins(PLUGINS_ROOT)
    fragments: List[str] = []
    for p in plugins:
        p.init(profile)
        p.run({})
        for metric, val in p.get_metrics().items():
            bus.publish(AgentEvent(tenant_id=tenant_id, ts=datetime.now(),
                                   leg=p.name, metric=metric, value=val))
        fragments.append(p.render_dashboard())
    print("    → 租户 %s：插件 %d · 事件 %d" % (tenant_id, len(plugins), len(bus.events)))
    return fragments, bus


def main():
    print("=== 成长型 Agent 平台 · M2/M3/M4 一体化落地 ===")
    os.makedirs(EVENTS_DIR, exist_ok=True)
    _reset_events()

    print("\n[M2] 插件热插拔加载 + 多租户运行：")
    fragments: Dict[str, List[str]] = {}
    for tid in ["profile_001", "profile_002"]:
        print("  租户", tid, "—", PROFILES[tid].company)
        frags, _ = _run_tenant(tid)
        fragments[tid] = frags

    print("\n[M4] 内部四 Agent（获客/转化/交付/沉淀）经 A2A/MCP 总线协作：")
    a2a_bus = LocalA2ABus()
    ops_bus = MultiTenantEventBus("platform_ops", EVENTS_DIR)  # M4 指标纳入 M3 聚合
    conv_log = run_agent_pipeline(a2a_bus, ops_bus)
    print("  A2A 协作日志 — 消息数:", len(conv_log))
    for m in conv_log:
        print("    · %s → %s（%s）" % (m["from"], m["to"], m["skill"]))

    print("\n[M3] 多租户事件聚合看板生成：")
    html_doc = build_dashboard(EVENTS_DIR, PROFILES, fragments)
    out = os.path.join(HERE, "多租户看板_M3_%s.html" % datetime.now().strftime("%Y%m%d"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print("  看板:", out)
    print("\n[完成] M2 热插拔 / M3 聚合 / M4 协作 全部落地。红线②守牢（客户包只读，核心资产不出门）。")


if __name__ == "__main__":
    main()
