#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 M4 · 真实 A2A 传输层（零依赖，仅 Python 标准库）。

把 M4 的「获客/转化/交付/沉淀」四 Agent 协作，从进程内 LocalA2ABus 升级为
**真实 A2A（Agent2Agent）传输**：每个 Agent 以独立 localhost HTTP 服务暴露真实 AgentCard
（/.well-known/agent.json）与 tasks/send 端点；bus.discover 真实 HTTP GET 对端卡片，
bus.delegate 真实 HTTP POST 委托任务。协议形状对齐 Google A2A（AgentCard / tasks/send / Task·Message）。

设计要点：
  - 仅 Python 3 标准库（http.server / json / urllib / threading），零外部 SDK、零 pip、可离线。
  - 四 Agent 业务代码（agents/acquisition|conversion|delivery|deposit.py）**不变**；
    仅新增本传输层 + 服务宿主，Agent 经既有 bus.register / bus.delegate 接口接入。
  - 演示中四 Agent 以线程共驻同一进程（真实 socket 往返），换远端主机只需把 AgentCard URL 指向远程——
    传输契约与跨进程/跨机完全一致（神：接口不变，骨：local→远程一行切换）。
  - MCP 映射：MCP 是「工具总线」（Agent 暴露 tools 给模型/其他 Agent 调），A2A 是「Agent 网络」
    （Agent 互发现+委托任务）。本传输实现 A2A 协作层；四 Agent 的 skills 即天然可映射为 MCP tools，
    彼层用相同 JSON-RPC 信封即可接 MCP（下一步可选，不在本替换范围）。
"""

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any, List

from interfaces import IA2AAdapter
from core.a2a import AgentCard


class A2ATransport(IA2AAdapter):
    """真实 A2A 传输总线：discover(HTTP GET 卡片) + delegate(HTTP POST 任务)。"""

    def __init__(self):
        self.endpoints: Dict[str, str] = {}          # agent_name -> base url (http://host:port)
        self._cards: Dict[str, Dict[str, Any]] = {}
        self._log: List[Dict[str, Any]] = []         # A2A 协作日志（可观测）

    # —— 端点登记（宿主启动时调用）——
    def register_endpoint(self, name: str, url: str) -> None:
        self.endpoints[name] = url.rstrip("/")

    # —— 兼容 BaseAgent.__init__ 的 card 注册（不强制端点）——
    def register(self, card: AgentCard) -> None:
        self._cards[card.name] = card.to_card()

    # —— IA2AAdapter：discover（真实 HTTP GET 对端 AgentCard）——
    def discover(self, agent_card_url: str) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(agent_card_url, timeout=5) as r:
                card = json.loads(r.read().decode("utf-8"))
            name = card.get("name")
            if name:
                self._cards[name] = card
            return card
        except Exception as e:
            return {"error": str(e)}

    # —— IA2AAdapter：delegate（真实 HTTP POST 任务，A2A tasks/send 信封）——
    def delegate(self, target: str, task: Dict[str, Any]) -> Dict[str, Any]:
        url = self.endpoints.get(target)
        if not url:
            return {"ok": False, "error": "未知 agent 端点: %s" % target}
        self._log.append({"from": task.get("from", "?"), "to": target,
                          "skill": task.get("skill", ""), "transport": "A2A/HTTP"})
        envelope = {
            "id": "task-%d" % id(task),
            "message": {"role": "user",
                        "parts": [{"type": "application/json", "data": task}]},
        }
        payload = json.dumps(envelope).encode("utf-8")
        req = urllib.request.Request(
            url + "/tasks/send", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                reply = json.loads(r.read().decode("utf-8"))
            # 拆 A2A Task/Message 信封，回传 Agent 原始结果字典（与 LocalA2ABus 同接口）
            arts = reply.get("artifacts") or [{}]
            parts = (arts[0] or {}).get("parts") or [{}]
            return parts[0].get("data", reply)
        except Exception as e:
            return {"ok": False, "error": "A2A 委托失败: %s" % e}

    def conversation_log(self) -> List[Dict[str, Any]]:
        return self._log


def run_agent_server(agent, transport: A2ATransport, host: str, port: int):
    """以 A2A HTTP 服务宿主一个 Agent（守护线程，真实 socket）。"""
    card_url = "http://%s:%d/.well-known/agent.json" % (host, port)
    agent.card.url = card_url
    transport.register_endpoint(agent.name, "http://%s:%d" % (host, port))

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/.well-known/agent.json":
                self._send(200, agent.card.to_card())          # 真实 A2A AgentCard
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/tasks/send":
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    env = json.loads(raw.decode("utf-8"))
                    task = env["message"]["parts"][0]["data"]
                    task_id = env.get("id", "task")
                except Exception:
                    task, task_id = {}, "task"
                # 真实 A2A 任务体 -> 调用 agent 既有 _dispatch（业务代码不变）
                result = agent._dispatch(task)
                reply = {
                    "id": task_id,
                    "status": "completed",
                    "artifacts": [{"parts": [{"type": "application/json", "data": result}]}],
                }
                self._send(200, reply)
            else:
                self._send(404, {"error": "not found"})

        def log_message(self, *args):  # 静默访问日志
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
