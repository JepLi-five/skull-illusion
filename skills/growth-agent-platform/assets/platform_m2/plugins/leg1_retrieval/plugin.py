#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 插件 · 腿1 客户检索（热插拔目录）。

本文件即「一条腿 = 一个独立插件目录」的体现：复制本目录、改 run() 即可新增/替换能力，
发现器会自动加载（见 core/discoverer.py），无需改主程序。
复用客户包 线索看板.py（只读），数据取自 profile.staging_path（M2 多租户按租户取数）。
"""

import os
import sys
import html
import importlib.util
from typing import Dict, Any, List

_HERE = os.path.dirname(os.path.abspath(__file__))
# 契约层 interfaces.py 已内置 platform_m2 根目录（_IDIR 即 platform_m2）
_IDIR = os.path.normpath(os.path.join(_HERE, "..", ".."))  # 契约层 interfaces.py 已内置 platform_m2 根目录
if _IDIR not in sys.path:
    sys.path.insert(0, _IDIR)
# 客户包（只读引用，从不改写）
CLIENT_PKG = os.path.normpath(os.path.join(_HERE, "..", "..", "template_assets"))  # 演示资产已内置，红线②：仅≤10行脱敏样例
LEG1_DIR = os.path.join(CLIENT_PKG, "腿1_线索检索")

from interfaces import ICapabilityPlugin, ClientProfile  # noqa: E402


def _load(modname: str, path: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Leg1RetrievalPlugin(ICapabilityPlugin):
    name = "leg1_retrieval"

    def init(self, profile: ClientProfile) -> None:
        self.profile = profile
        # M2：按租户取数，空则回退默认脱敏样例
        self.staging = profile.staging_path or os.path.join(LEG1_DIR, "staging示例_脱敏10家.csv")

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        kanban = _load("leg1_kanban_m2", os.path.join(LEG1_DIR, "线索看板.py"))
        rows = kanban.load(self.staging)
        self._rows: List[Dict[str, Any]] = rows
        tiers, regions = {}, {}
        for r in rows:
            t = (r.get("评分档位") or "").strip()
            if t:
                tiers[t] = tiers.get(t, 0) + 1
            rg = (r.get("地区") or "").strip()
            if rg:
                regions[rg] = regions.get(rg, 0) + 1
        return {"leads": len(rows), "tiers": tiers, "regions": regions}

    def get_metrics(self) -> Dict[str, float]:
        rows = getattr(self, "_rows", [])
        return {"新增线索": float(len(rows)),
                "留资": float(sum(1 for r in rows if (r.get("需求信号") or "").strip()))}

    def render_dashboard(self) -> str:
        rows = getattr(self, "_rows", [])
        regions = {}
        for r in rows:
            rg = (r.get("地区") or "").strip()
            if rg:
                regions[rg] = regions.get(rg, 0) + 1
        top = sorted(regions.items(), key=lambda x: -x[1])[:6]
        maxv = max([v for _, v in top], default=1) or 1
        bars = "".join(
            '<div class="row"><span class="lab">%s</span>'
            '<span class="track"><span class="fill" style="width:%d%%"></span></span>'
            '<span class="val">%d</span></div>' % (html.escape(str(k)), int(100 * v / maxv), v)
            for k, v in top)
        return ('<section><div class="sec-h"><h2>① 客户检索（腿1）</h2>'
                '<span class="sub">热插拔插件 · 复用 线索看板.py</span></div>'
                '<div class="kpis">'
                '<div class="kpi"><div class="n">%d</div><div class="l">线索总数</div></div>'
                '<div class="kpi"><div class="n">%d</div><div class="l">P0 强信号</div></div>'
                '<div class="kpi"><div class="n">%d</div><div class="l">覆盖区域</div></div></div>'
                '<div class="chart-title">区域分布 Top</div>%s'
                '<div class="note">数据来自租户脱敏 staging：%s</div></section>'
                % (len(rows), sum(1 for r in rows if (r.get("评分档位") or "") == "P0"),
                   len(regions), bars, os.path.basename(self.staging)))
