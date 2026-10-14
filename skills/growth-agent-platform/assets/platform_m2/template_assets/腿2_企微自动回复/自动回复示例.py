#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腿2 企微自动回复 - 官方 API 接入示例骨架（仅用 Python 3 标准库，零外部依赖）

重要合规：
  - 仅使用企业微信官方 API，严禁个人微信外挂 / 绕过官方接口的群发工具（协议 1.3）。
  - 所有文本回复末尾强制追加显式 AI 标识（办法第七条，见 ai标识话术.md）。

前置条件（见 接入指引.md）：
  1. 甲方已完成企业微信认证（待定项 5）
  2. 创建自建应用，获取 corpid / appkey / agentid
  3. 配置可信 IP 白名单（服务器出口 IP）
  4. access_token 已做缓存（本文件内置 7200s 缓存）

本文件为骨架，仅演示调用结构；token / 密钥由甲方自行填入（建议用环境变量，勿写入本包）。
依赖：仅 json / time / urllib（标准库）
"""

import json
import time
import urllib.request
import urllib.error
import os

# ---- 甲方自行填入（建议用环境变量，勿硬编码进受控包）----
CORP_ID = os.getenv("QY_CORP_ID", "{{甲方企业微信corpid}}")
CORP_APPKEY = os.getenv("QY_CORP_APPKEY", "{{甲方自建应用appkey}}")
AGENT_ID = os.getenv("QY_AGENT_ID", "{{甲方agentid}}")

TOKEN_CACHE = {"token": None, "expire": 0}
AI_TAG = "【本回复由 AI 生成】"


def get_token():
    """获取并缓存 access_token（官方接口 cgi-bin/gettoken）"""
    if TOKEN_CACHE["token"] and time.time() < TOKEN_CACHE["expire"]:
        return TOKEN_CACHE["token"]
    url = ("https://qyapi.weixin.qq.com/cgi-bin/gettoken"
           "?corpid={}&appkey={}".format(CORP_ID, CORP_APPKEY))
    resp = _get(url)
    if "access_token" not in resp:
        raise RuntimeError("获取 access_token 失败：{}".format(resp))
    TOKEN_CACHE["token"] = resp["access_token"]
    TOKEN_CACHE["expire"] = time.time() + resp.get("expires_in", 7200) - 200
    return TOKEN_CACHE["token"]


def send_text(touser, content):
    """通过官方 API 发送文本消息（应用消息 / 客户联系）。
    注意：给外部客户发消息须走『客户联系』接口并遵守频控与免打扰。"""
    token = get_token()
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(token)
    # 合规：文本末尾追加显式 AI 标识（办法第七条）
    payload = {
        "touser": touser,
        "msgtype": "text",
        "agentid": int(AGENT_ID),
        "text": {"content": content if AI_TAG in content else content + "\n" + AI_TAG},
    }
    return _post(url, payload)


def auto_reply(user_msg, 话术库路径="话术库.json"):
    """根据 话术库.json 匹配关键词，返回标准应答；无匹配转人工。
    打分：命中关键词长度之和 + 命中条数（长度优先、条数次之），
    避免多类目同时命中时仅靠列表顺序取胜导致答非所问。"""
    with open(话术库路径, encoding="utf-8") as f:
        话术库 = json.load(f)["items"]
    best = None  # {"score": int, "reply": str}
    for item in 话术库:
        score = 0
        for kw in item.get("keywords", []):
            if kw and kw in user_msg:
                score += len(kw) + 1  # 长度 + 命中条数加权
        if score > 0 and (best is None or score > best["score"]):
            best = {"score": score, "reply": item["reply"]}
    return best["reply"] if best else "您好，您的问题已记录，工作人员将尽快与您联系。" + AI_TAG


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"errcode": e.code, "errmsg": e.reason}


if __name__ == "__main__":
    print("本文件为企微官方 API 接入骨架。请在 接入指引.md 完成后，")
    print("用环境变量 QY_CORP_ID / QY_CORP_APPKEY / QY_AGENT_ID 填入凭据，再运行。")
    # 示例（取消注释前先确保凭据就绪）：
    # print(auto_reply("你们产品怎么卖"))
    # print(send_text("ZhangSan", "您好，这是一条测试。"))
