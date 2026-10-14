#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 · M4 真实 A2A 传输演示入口（替换 LocalA2ABus）。

串联：
  M2 热插拔    —— 复用 run_m2m4 的 _run_tenant，跑通两租户（示例 + 演示）插件；
  M4 真实 A2A  —— 四 Agent（获客/转化/交付/沉淀）以真实 localhost HTTP(A2A) 协作；
  M3 聚合      —— 重建多租户看板（含本次 platform_ops 事件）。

四 Agent 业务代码未改动；仅把协作总线从进程内 LocalA2ABus 换成真实 A2ATransport。
红线②：客户 U 盘包只读引用，核心资产不出门。
"""

import os
import sys
import json
import csv
from datetime import date, datetime


def _count_csv(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)

HERE = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.normpath(HERE)  # 契约层 interfaces.py 已内置 platform_m2 根目录
sys.path.insert(0, INTERFACE_DIR)
sys.path.insert(0, HERE)

from run_m2m4 import PROFILES, _reset_events, _run_tenant, CLIENT_PKG  # noqa: E402
from interfaces import ClientProfile  # noqa: E402
from core.event_bus import MultiTenantEventBus  # noqa: E402
from core.transport import A2ATransport, run_agent_server  # noqa: E402
from core.ledger import TenantLedger  # noqa: E402
from core.antijump import AntiJumpGate  # noqa: E402
from agents.acquisition import AcquisitionAgent  # noqa: E402
from agents.conversion import ConversionAgent  # noqa: E402
from agents.delivery import DeliveryAgent  # noqa: E402
from agents.deposit import DepositAgent  # noqa: E402
from multi_tenant_dashboard import build_dashboard  # noqa: E402

EVENTS_DIR = os.path.join(HERE, "events")
LEDGER_DIR = os.path.join(HERE, "ledger")
REGISTRY = os.path.join(HERE, "tenants", "registry.json")
HOST = "127.0.0.1"
PORTS = {
    "agent_acquisition": 8701,
    "agent_conversion": 8702,
    "agent_delivery": 8703,
    "agent_deposit": 8704,
}


def load_profiles() -> dict:
    """配置化：内置两租户种子 + registry.json 中已接入的新租户，合并为 PROFILES。
    新客户接入 = 写一条 registry.json 记录（见 onboard_client.py），无需改代码。"""
    profs = dict(PROFILES)
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
        for tid, c in reg.items():
            if tid in profs:
                continue
            profs[tid] = ClientProfile(
                tenant_id=tid, company=c["company"], industry=c["industry"], region=c["region"],
                script_lib_path=os.path.join(CLIENT_PKG, c.get("script_lib_path", "腿2_企微自动回复/话术库.json")),
                staging_path=os.path.join(HERE, c["staging_path"]),
                commercial={"setup_fee": [3000, 5000], "monthly": [1500, 2500],
                            "share_pct": [c.get("share_pct", 0.08), c.get("share_pct", 0.08)]},
            )
    return profs


def main():
    print("=== 成长型 Agent 平台 · M2/M3/M4/M5 全链路（配置化多租户）===")
    os.makedirs(EVENTS_DIR, exist_ok=True)
    _reset_events()  # 清空旧 events，整轮重跑

    PROFILES = load_profiles()  # 含 registry.json 接入的新租户

    # —— M2 热插拔：各租户插件运行（产出 cliente 事件）——
    print("\n[M2] 插件热插拔 + 多租户运行：")
    fragments = {}
    for tid in sorted(PROFILES):
        print("  租户", tid, "—", PROFILES[tid].company)
        frags, _ = _run_tenant(tid, PROFILES)
        fragments[tid] = frags

    # —— M4 真实 A2A：启动四 Agent 的 HTTP 服务（共驻线程，真实 socket 往返）——
    print("\n[M4] 四 Agent 真实 A2A(HTTP) 服务宿主：")
    transport = A2ATransport()
    ops_bus = MultiTenantEventBus("platform_ops", EVENTS_DIR)
    servers = []
    for cls, port in [(AcquisitionAgent, PORTS["agent_acquisition"]),
                      (ConversionAgent, PORTS["agent_conversion"]),
                      (DeliveryAgent, PORTS["agent_delivery"]),
                      (DepositAgent, PORTS["agent_deposit"])]:
        a = cls(transport, ops_bus)
        s = run_agent_server(a, transport, HOST, port)
        servers.append(s)
        print("  · 宿主 %s @ http://%s:%d/  (skills: %s)"
              % (a.name, HOST, port, ",".join(a.card.skills)))

    # —— 真实 discover：HTTP GET 对端 AgentCard ——
    print("\n[A2A discover] 拉取对端能力卡片：")
    card = transport.discover("http://%s:%d/.well-known/agent.json"
                              % (HOST, PORTS["agent_acquisition"]))
    print("  acquisition 卡片: name=%s protocol=%s skills=%s"
          % (card.get("name"), card.get("protocol"),
             [s.get("id") for s in card.get("skills", [])]))

    # —— 真实 delegate：仅触发首节点，链路经 HTTP 自传播 ——
    print("\n[A2A delegate] 触发获客 Agent（链路经真实 HTTP 传播）：")
    resp = transport.delegate("agent_acquisition",
                              {"skill": "acquire", "from": "orchestrator"})
    print("  最终回包:", resp)

    print("\n[A2A 协作日志]（真实 HTTP 往返）：")
    for m in transport.conversation_log():
        print("  · %s → %s（%s，%s）" % (m["from"], m["to"], m["skill"], m["transport"]))

    # —— M5 明账账本 + 防跳单闸门（红线③ 从话术落进代码）——
    print("\n[M5] 明账账本 + 防跳单闸门（脱敏演示）：")
    # 清空旧账本，保证可重复演示
    if os.path.isdir(LEDGER_DIR):
        for fn in os.listdir(LEDGER_DIR):
            if fn.startswith("ledger_") and fn.endswith(".csv"):
                os.remove(os.path.join(LEDGER_DIR, fn))
    # 演示场景（脱敏，非真实客户数据）：按各租户脱敏样例行数动态生成，
    # 含「合法成交(agent)」与「跳单嫌疑(direct)」两种情形，覆盖所有已接入租户。
    ledgers, antijump_alerts = {}, {}
    for tid, prof in sorted(PROFILES.items()):
        if tid == "platform_ops":
            continue
        n = _count_csv(prof.staging_path) if os.path.exists(prof.staging_path) else 0
        short = prof.company[:4]
        leads = ["%s-客户%d" % (short, i) for i in range(min(max(n, 1), 3))]
        share_pct = prof.commercial["share_pct"][0]
        deals = [("%s-客户0" % short, "agent", 50000.0)]
        if len(leads) >= 2:
            deals.append(("%s-客户1" % short, "direct", 30000.0))  # 触发跳单嫌疑
        led = TenantLedger(tid, LEDGER_DIR)
        gate = AntiJumpGate(tid, led)
        fc = date(2026, 1, 10)
        for c in leads:
            led.add("2026-01-10", "线索成本", 30.0, "CPL 线索成本(%s)" % c, c)
            gate.record_contact(c, fc)  # 留痕：Agent 首次触达
        for cust, ch, amt in deals:
            led.add("2026-03-15", "成交金额", amt, "成交(%s,渠道=%s)" % (cust, ch), cust)
            led.add("2026-03-15", "预估分成", amt * share_pct,
                    "分成 %.0f%%" % (share_pct * 100), cust)
            gate.check_deal("deal-" + cust, cust, date(2026, 3, 15), ch)  # 校验跳单
        ledgers[tid] = led.summary()
        antijump_alerts[tid] = gate.report()
        print("  租户 %s：线索%d / 成交%d / 预估分成¥%.0f / 净收益¥%.0f / 防跳单告警%d"
              % (tid, ledgers[tid]["leads"], ledgers[tid]["deals"],
                 ledgers[tid]["share"], ledgers[tid]["net"], ledgers[tid]["alerts"]))
        for a in antijump_alerts[tid]:
            print("    ⚠ 跳单嫌疑：%s（首次触达 %s，成交 %s 归因 %s 渠道）"
                  % (a["customer"], a["first_contact"], a["deal_date"], "非Agent"))

    # —— M3 重建多租户聚合看板（含 M5 明账/防跳单）——
    print("\n[M3] 重建多租户聚合看板（含 M5 明账/防跳单）：")
    html_doc = build_dashboard(EVENTS_DIR, PROFILES, fragments, ledgers, antijump_alerts)
    out = os.path.join(HERE, "多租户看板_M3_%s.html" % datetime.now().strftime("%Y%m%d"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print("  看板:", out)

    # 关闭服务
    for s in servers:
        s.shutdown()
        s.server_close()
    print("\n[完成] M2 热插拔 / M3 聚合 / M4 真实 A2A / M5 明账+防跳单 全链路落地；"
          "LocalA2ABus 仍保留为进程内参考实现。红线②未触碰客户包。")


if __name__ == "__main__":
    main()
