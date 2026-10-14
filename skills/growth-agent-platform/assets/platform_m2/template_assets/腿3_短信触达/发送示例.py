#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腿3 短信触达 - 合规通道发送示例骨架（仅用 Python 3 标准库，零外部依赖）

合规要点（见 退订频控清单.md）：
  - 短信签名须以甲方企业名报备（如【甲方公司】）
  - 模板须通过通道方审核
  - 每条须含退订指令（回复 T 退订）
  - 频控：同一号码营销类 ≤ 1 次/周；同模板 ≤ 1 次/24h；夜间不推营销
  - 严禁 AI 外呼（协议 1.3 红线④）

本文件为骨架，演示合规短信结构；access_key / appkey / 网关由甲方自行填入（建议环境变量）。
依赖：仅 json / urllib（标准库）
"""

import json
import urllib.request
import urllib.error
import os

SMS_GATEWAY = os.getenv("SMS_GATEWAY", "{{甲方短信通道网关地址}}")
ACCESS_KEY = os.getenv("SMS_ACCESS_KEY", "{{甲方access_key}}")
ACCESS_APPKEY = os.getenv("SMS_ACCESS_APPKEY", "{{甲方access_appkey}}")
SIGN = "【甲方公司】"  # 须以甲方企业名报备


def build_content(template, **kw):
    """渲染模板并强制补退订提示（合规）。
    签名幂等：模板已含签名则不再重复前置，避免双签名【甲方公司】【甲方公司】。"""
    content = template.format(**kw)
    if "退订" not in content:
        content += " 回复T退订"
    if not content.startswith(SIGN):
        content = SIGN + content
    return content


def send(phone, content):
    """调用合规短信通道发送（示例为 JSON POST，具体按通道文档调整）。"""
    data = {
        "phone": phone,
        "content": content,
        "sign": SIGN,
        "access_key": ACCESS_KEY,
        "access_appkey": ACCESS_APPKEY,
    }
    req = urllib.request.Request(
        SMS_GATEWAY, data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"errcode": e.code, "errmsg": e.reason}


if __name__ == "__main__":
    # 示例：向某号码发送一条合规营销短信（仅演示，未真正发送）
    tpl = "【甲方公司】{name}您好，我司XX工业耗材适配多种工况，可寄样测试。详询{phone}。回复T退订"
    msg = build_content(tpl, name="某总", phone="0311-XXXXXXX")
    print("待发送内容：", msg)
    print("（填入真实通道参数后，取消注释 send(phone, msg) 调用即可发送）")
