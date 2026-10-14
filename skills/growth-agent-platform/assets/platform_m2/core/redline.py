#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M2 核心：合规红线守卫（per-tenant 主权 / 不出门 / 防跳单）。

与 M1 同款守卫，按「加固」方案保留：任何跨租户访问、触碰乙方核心资产（主表/引擎/管线）
的动作都在此被拦截。这是一人公司升级为架构公司时「平台独立复活 + 客户数据主权」的硬闸。
"""

from interfaces import IRedlineGuard, ClientProfile


class SimpleRedlineGuard(IRedlineGuard):
    def check(self, profile: ClientProfile, action: dict) -> tuple:
        # 红线②：禁止跨租户访问、禁止触碰乙方核心资产
        if action.get("cross_tenant"):
            return (False, "跨租户访问被红线②禁止")
        if action.get("touch_core_assets"):
            return (False, "乙方主表/引擎/管线不出门（红线②）")
        if not profile.redline.get("data_sovereignty"):
            return (False, "客户数据主权未确认")
        return (True, "通过")
