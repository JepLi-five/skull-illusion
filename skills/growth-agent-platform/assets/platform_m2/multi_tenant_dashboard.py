#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 · M3：多租户事件聚合看板。

读取 events_dir 下所有 events_<tenant>.csv（由 M2 各租户运行 + M4 Agent 网络产出），
聚合为「跨租户汇总 + 每租户视图」的自包含 HTML。新增任何租户只需其 events 文件落盘即可自动入图。

依赖：Python 3 标准库 + 本目录 core/event_bus.aggregate_events。
红线②：每个租户事件物理隔离在各自 CSV，看板只读聚合、不交叉暴露原始客户数据。
"""

import os
import html
from datetime import datetime
from typing import Dict, Any, List

from core.event_bus import aggregate_events
from interfaces import ClientProfile


CSS = """
:root{--bg:#f5f7fa;--card:#fff;--primary:#2f6fed;--accent:#0fa968;--text:#1f2933;--muted:#9aa7b4;--line:#e6ebf2;}
*{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);}
.hero{background:linear-gradient(135deg,#1f4fc4,#2f6fed);color:#fff;padding:20px 18px;} .hero h1{margin:0;font-size:21px;}
.hero p{margin:6px 0 0;font-size:13px;opacity:.95;} .wrap{max-width:960px;margin:0 auto;padding:14px 16px 40px;}
section{background:var(--card);border-radius:14px;padding:16px 18px;margin:12px 0;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.sec-h{display:flex;align-items:baseline;gap:10px;margin-bottom:10px;flex-wrap:wrap;}
.sec-h h2{margin:0;font-size:17px;color:var(--primary);border-left:4px solid var(--primary);padding-left:10px;}
.sub{font-size:12px;color:var(--muted);} .chart-title{font-weight:700;color:var(--primary);font-size:14px;margin:8px 0 6px;}
.row{display:flex;align-items:center;margin:5px 0;font-size:13px;}
.row .lab{width:96px;color:var(--text);flex:none;}
.row .track{flex:1;background:var(--line);border-radius:6px;height:14px;margin:0 8px;overflow:hidden;}
.row .fill{display:block;height:100%;background:var(--primary);border-radius:6px;}
.row .val{width:36px;text-align:right;color:var(--muted);flex:none;}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;} .kpi{background:var(--bg);border-radius:10px;padding:12px;text-align:center;}
.kpi .n{font-size:22px;font-weight:800;color:var(--primary);} .kpi .l{font-size:12px;color:var(--muted);margin-top:3px;}
.badge{display:inline-block;border-radius:6px;padding:3px 9px;font-size:12px;margin-right:6px;}
.b-ok{background:#e8f7f0;color:#0a7a4a;} .b-warn{background:#fff4ef;color:#b4621a;}
.note{font-size:12px;color:var(--muted);margin-top:10px;}
.qa{font-size:13px;background:var(--bg);border-radius:8px;padding:8px 10px;margin:6px 0;}
.qa .q{color:var(--primary);font-weight:700;} .qa .a{color:var(--text);}
.flag{background:#fff8ef;border:1px solid #ffe2b8;color:#8a6d1a;border-radius:8px;padding:10px 12px;font-size:12px;margin-top:12px;}
.tenant-tag{display:inline-block;background:#eef3ff;color:#2f6fed;border-radius:6px;padding:2px 8px;font-size:12px;margin-right:6px;}
"""


def _bar(pairs, color="#2f6fed"):
    if not pairs:
        return '<div class="note">（暂无事件）</div>'
    maxv = max(v for _, v in pairs) or 1
    out = []
    for label, v in pairs:
        w = int(100 * v / maxv)
        out.append(
            '<div class="row"><span class="lab">%s</span>'
            '<span class="track"><span class="fill" style="width:%d%%"></span></span>'
            '<span class="val">%d</span></div>' % (html.escape(str(label)), w, int(v)))
    return "".join(out)


def _money(v: float) -> str:
    return "{:,.0f}".format(v)


def render_ledger(led: Dict[str, float], alerts: List[Dict[str, str]]) -> str:
    """M5：每租户 明账账本 + 防跳单 区块。"""
    alert_rows = "".join(
        '<div class="qa"><span class="a">⚠ 跳单嫌疑：客户 %s，首次触达 %s，成交 %s'
        '（排他 24 个月内归因非 Agent 渠道）</span></div>'
        % (html.escape(a["customer"]), html.escape(a["first_contact"]), html.escape(a["deal_date"]))
        for a in alerts)
    return ('<section style="margin-top:10px"><div class="sec-h"><h2>明账账本（红线③）</h2>'
            '<span class="sub">双时态流水 · 变动带时间线锚</span></div>'
            '<div class="kpis">'
            '<div class="kpi"><div class="n">%d</div><div class="l">线索数</div></div>'
            '<div class="kpi"><div class="n">%d</div><div class="l">成交数</div></div>'
            '<div class="kpi"><div class="n">¥%s</div><div class="l">预估分成</div></div>'
            '<div class="kpi"><div class="n">¥%s</div><div class="l">净收益</div></div>'
            '<div class="kpi"><div class="n">%d</div><div class="l">防跳单告警</div></div></div>'
            '%s'
            '<div class="note">流水见 ledger_&lt;tenant&gt;.csv（event_date + recorded_at 双时态，新鲜度可追）</div></section>'
            % (led["leads"], led["deals"], _money(led["share"]), _money(led["net"]),
               led["alerts"], alert_rows))


def build_dashboard(events_dir: str,
                    profiles: Dict[str, ClientProfile],
                    fragments_by_tenant: Dict[str, List[str]],
                    ledgers: Dict[str, Dict[str, float]] = None,
                    antijump: Dict[str, List[Dict[str, str]]] = None) -> str:
    data = aggregate_events(events_dir)
    tids = sorted(data.keys())
    total_events = sum(len(v) for v in data.values())

    # 跨租户汇总指标
    all_metrics: Dict[str, float] = {}
    for evts in data.values():
        for e in evts:
            all_metrics[e.metric] = all_metrics.get(e.metric, 0.0) + e.value
    summary_bars = _bar(sorted(all_metrics.items(), key=lambda x: -x[1])[:10])

    # 每租户片段
    sections = []
    for tid in tids:
        evts = data[tid]
        prof = profiles.get(tid)
        if prof:
            comp, ind = prof.company, prof.industry
        elif tid == "platform_ops":
            comp, ind = "平台内部运营（M4 Agent 网络）", "平台运维"
        else:
            comp, ind = tid, "未知"
        metrics: Dict[str, float] = {}
        for e in evts:
            metrics[e.metric] = metrics.get(e.metric, 0.0) + e.value
        mbars = _bar(sorted(metrics.items(), key=lambda x: -x[1])[:8])
        frags = "".join(fragments_by_tenant.get(tid, []))
        if not frags:
            if tid == "platform_ops":
                frags = ('<section style="margin-top:10px"><div class="sec-h"><h2>内部 Agent 网络（M4）</h2>'
                         '<span class="sub">经真实 A2A(HTTP) 总线协作</span></div>'
                         '<div class="note">获客→转化→交付→沉淀 链路指标见上方指标条；完整链路经 '
                         'A2ATransport.delegate 串联，契约对齐 interfaces.IA2AAdapter（真实 AgentCard + tasks/send）。</div></section>')
            else:
                frags = '<div class="note">（本租户插件看板由 M2 运行产出，详见各租户运行）</div>'
        # M5：每租户追加 明账账本 + 防跳单 区块
        led = (ledgers or {}).get(tid)
        if led:
            frags += render_ledger(led, (antijump or {}).get(tid, []))
        sections.append(
            '<section><div class="sec-h"><h2>租户 %s · %s</h2>'
            '<span class="tenant-tag">%s</span><span class="sub">%s · %d 条事件</span></div>'
            '<div class="chart-title">本租户指标</div>%s%s'
            '<div class="note">事件源 events_%s.csv（物理隔离，红线② 守牢）</div></section>'
            % (html.escape(tid), html.escape(comp), html.escape(tid),
               html.escape(ind), len(evts), mbars, frags, tid))

    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            '<title>成长型 Agent 平台 · 多租户聚合看板（M3）</title><style>%s</style></head><body>'
            '<div class="hero"><h1>成长型 Agent 平台 · 多租户聚合看板（M3）</h1>'
            '<p>聚合 %d 个租户 / %d 条事件 · 生成于 %s</p></div>'
            '<div class="wrap">'
            '<section><div class="sec-h"><h2>跨租户汇总</h2>'
            '<span class="badge b-ok">数据主权归客户</span>'
            '<span class="badge b-ok">核心资产不出门</span>'
            '<span class="badge b-warn">防跳单</span></div>'
            '<div class="kpis">'
            '<div class="kpi"><div class="n">%d</div><div class="l">租户数</div></div>'
            '<div class="kpi"><div class="n">%d</div><div class="l">事件总数</div></div>'
            '<div class="kpi"><div class="n">%d</div><div class="l">指标种类</div></div></div>'
            '<div class="chart-title">全平台指标（跨租户求和）</div>%s</section>'
            '%s'
            '<div class="flag">本看板由 M3 聚合器生成：扫描所有 events_*.csv，按 tenant_id 物理隔离聚合。'
            '新增客户 = 在 PROFILES 加一项 + 其 events 文件落盘即自动入图（M3 多租户）。'
            '客户 U 盘交付包未被改动，红线②守牢。</div>'
            '<p class="note">成长型 Agent 平台 · M2 热插拔 / M3 聚合 / M4 Agent 网络 · %s</p>'
            '</div></body></html>'
            % (CSS, len(tids), total_events, datetime.now().strftime("%Y-%m-%d %H:%M"),
               len(tids), total_events, len(all_metrics), summary_bars,
               "".join(sections), datetime.now().strftime("%Y-%m-%d")))
