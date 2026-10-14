#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M2 核心：插件热插拔发现器。

把「三条腿」拆为 plugins/<leg>/plugin.py 独立目录后，本发现器：
  1. 扫描 plugins/ 下所有子目录的 plugin.py；
  2. 用 importlib 动态加载模块；
  3. 自动识别实现了 ICapabilityPlugin 且非抽象类的插件并实例化。

效果 = 热插拔：新增能力 = 复制一个目录（加 plugin.py 实现接口），无需改主程序。
对应返照补强「行业 Skill 可插拔 / progressive disclosure」范式。
"""

import inspect
import os
import importlib.util
import sys

from interfaces import ICapabilityPlugin


def discover_plugins(plugins_root: str):
    """遍历 plugins_root 子目录，加载每个 plugin.py，收集已实例化的 ICapabilityPlugin。"""
    found = []
    if not os.path.isdir(plugins_root):
        return found
    for entry in sorted(os.listdir(plugins_root)):
        pdir = os.path.join(plugins_root, entry)
        if not os.path.isdir(pdir):
            continue
        pfile = os.path.join(pdir, "plugin.py")
        if not os.path.isfile(pfile):
            continue
        mod_name = "plugin_%s" % entry
        try:
            spec = importlib.util.spec_from_file_location(mod_name, pfile)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            print("    [warn] 插件加载失败 %s: %s" % (entry, e))
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if (issubclass(obj, ICapabilityPlugin)
                    and obj is not ICapabilityPlugin
                    and getattr(obj, "__abstractmethods__", None) == frozenset()):
                try:
                    inst = obj()
                    found.append(inst)
                    print("    [热插拔] 加载插件:", inst.name, "(目录 %s)" % entry)
                except Exception as e:
                    print("    [warn] 插件实例化失败 %s: %s" % (entry, e))
    return found
