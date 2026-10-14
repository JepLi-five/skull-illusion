#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 插件 · 腿3 短信触达（热插拔目录）。

复用客户包 短信模板.json + 发送示例.py（只读）。build_content 签名幂等、合规（签名/退订）。
"""

import os
import sys
import html
import json
import importlib.util
from typing import Dict, Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_IDIR = os.path.normpath(os.path.join(_HERE, "..", ".."))  # 契约层 interfaces.py 已内置 platform_m2 根目录
if _IDIR not in sys.path:
    sys.path.insert(0, _IDIR)
CLIENT_PKG = os.path.normpath(os.path.join(_HERE, "..", "..", "template_assets"))  # 演示资产已内置，红线②：仅≤10行脱敏样例
LEG3_DIR = os.path.join(CLIENT_PKG, "腿3_短信触达")

from interfaces import ICapabilityPlugin, ClientProfile  # noqa: E402


def _load(modname: str, path: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Leg3SmsPlugin(ICapabilityPlugin):
    name = "leg3_sms"

    def init(self, profile: ClientProfile) -> None:
        self.profile = profile
        with open(os.path.join(LEG3_DIR, "短信模板.json"), encoding="utf-8") as f:
            self.tpls = json.load(f)["templates"]
        self.sms_mod = _load("leg3_send_m2", os.path.join(LEG3_DIR, "发送示例.py"))

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        content = self.sms_mod.build_content(self.tpls[0]["content"], name="某总", phone="0311-XXXXXXX")
        self._content = content
        return {"content": content}

    def get_metrics(self) -> Dict[str, float]:
        return {"短信触达": 1.0, "退订": 0.0}

    def render_dashboard(self) -> str:
        content = getattr(self, "_content", "")
        return ('<section><div class="sec-h"><h2>③ 短信触达（腿3）</h2>'
                '<span class="sub">热插拔插件 · 复用 短信模板.json</span></div>'
                '<div class="kpis">'
                '<div class="kpi"><div class="n">运行中</div><div class="l">状态</div></div>'
                '<div class="kpi"><div class="n">%d</div><div class="l">模板数</div></div>'
                '<div class="kpi"><div class="n">合规</div><div class="l">签名/退订</div></div></div>'
                '<div class="qa"><span class="a">示例：%s</span></div></section>'
                % (len(self.tpls), html.escape(content)))
