# MCP 注册表 · 接什么、怎么接

> Goose 原生支持 MCP（stdio / HTTP+SSE）。本平台把 MCP 当"外部能力插头"。
> 接 MCP = 让私有 WorkBuddy 能查企业、查地图、存网盘……不写底层轮子。

## 已有哪些 MCP（你环境里就有的）
| MCP | 用途 | 状态 |
|---|---|---|
| 天眼查 tyc-mcp | 查企业工商/股权（选厂合规排查） | 需鉴权 |
| 腾讯地图 tencent-map | 地理编码/路线/周边 | 已连 |
| 百度网盘 baidu-netdisk | 文件备份/分发 | 已连 |

## Phase 0 端到端验证：filesystem MCP
先用 Goose 自带/官方 filesystem MCP 跑通"agent 读本地文件"这一最小闭环，
证明 harness + MCP + LLM 三者打通，再接业务 MCP。

```bash
# 进入项目根
cd skull-illusion
# 用 Goose 跑一个依赖 filesystem 工具的简单任务（需先配好 DeepSeek provider）
DEEPSEEK_API_KEY=sk-xxx tools/goose/goose.exe run "读取 README.md 前三行并总结"
```

若 Goose 报错说没有 filesystem 工具，先加 MCP：
```bash
tools/goose/goose.exe mcp add --name filesystem --command npx --args "-y @modelcontextprotocol/server-filesystem ."
```

## 业务 MCP 接入顺序（建议）
1. filesystem（验证用，Phase 0）
2. tencent-map（获客地理聚类）
3. tyc-mcp（选厂合规排查，需先解决鉴权）
4. baidu-netdisk（每日备份到网盘/U盘镜像）

## 红线
- 天眼查/地图返回的数据落本地 SQLite，不外传第三方云。
- 接业务 MCP 前先确认其数据用途符合"去中心化私有"原则。
