#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 插件 · 腿2 企微自动回复（热插拔目录）。

复用客户包 话术库.json + 自动回复示例.py（只读）。话术库路径来自 profile.script_lib_path，
换客户 = 换话术库文件即可（对应行业「Skill 可插拔 / 话术库即知识资产」）。
"""

import os
import sys
import html
import importlib.util
from typing import Dict, Any, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_IDIR = os.path.normpath(os.path.join(_HERE, "..", ".."))  # 契约层 interfaces.py 已内置 platform_m2 根目录
if _IDIR not in sys.path:
    sys.path.insert(0, _IDIR)
CLIENT_PKG = os.path.normpath(os.path.join(_HERE, "..", "..", "template_assets"))  # 演示资产已内置，红线②：仅≤10行脱敏样例
LEG2_DIR = os.path.join(CLIENT_PKG, "腿2_企微自动回复")

from interfaces import ICapabilityPlugin, ClientProfile  # noqa: E402


def _load(modname: str, path: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Leg2WeComPlugin(ICapabilityPlugin):
    name = "leg2_wecom"

    def init(self, profile: ClientProfile) -> None:
        self.profile = profile
        self.auto_mod = _load("leg2_auto_m2", os.path.join(LEG2_DIR, "自动回复示例.py"))

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        samples = ["你们产品怎么卖", "和别家比哪个好", "多少钱一吨"]
        answered = [{"q": q, "a": self.auto_mod.auto_reply(q, self.profile.script_lib_path)}
                    for q in samples]
        self._answered: List[Dict[str, str]] = answered
        return {"answered": answered, "count": len(answered)}

    def get_metrics(self) -> Dict[str, float]:
        return {"自动回复": float(len(getattr(self, "_answered", []))), "转人工": 0.0}

    def render_dashboard(self) -> str:
        items = getattr(self, "_answered", [])
        qa = "".join(
            '<div class="qa"><span class="q">问：%s</span><br><span class="a">答：%s</span></div>'
            % (html.escape(i["q"]),
               html.escape(i["a"][:48] + "…" if len(i["a"]) > 48 else i["a"]))
            for i in items[:2])
        return ('<section><div class="sec-h"><h2>② 企微自动回复（腿2）</h2>'
                '<span class="sub">热插拔插件 · 复用 话术库.json</span></div>'
                '<div class="kpis">'
                '<div class="kpi"><div class="n">运行中</div><div class="l">状态</div></div>'
                '<div class="kpi"><div class="n">%d</div><div class="l">示例自动回复</div></div>'
                '<div class="kpi"><div class="n">19</div><div class="l">话术类目</div></div></div>%s</section>'
                % (len(items), qa))
