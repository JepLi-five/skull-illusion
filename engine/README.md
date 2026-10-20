# engine · harness 集成层

> 这里是"骷髅幻戏"与 Goose（harness 底座）的接缝。我们**不写底层 agent loop**，而是：
> 1. 用 Goose 跑通用 agent 能力（工具调用、MCP、上下文管理）；
> 2. 在它外面用我们自己的代码包"四部门逻辑 / 私有大脑 / 品牌壳"——这是差异化、主权所在。

## 当前接缝
- Goose 二进制：`../tools/goose/goose.exe`
- 配置样例：`../config/goose.toml.example` → `%APPDATA%\goose\config.toml`
- LLM 适配：DeepSeek（重活）/ 本地小模型（轻活），见 `../config/.env.example`
- MCP 插头：见 `../docs/mcp-registry.md`

## 调用方式（两种）
1. **CLI 直接调**：`goose run "..."` / `goose session` 交互，适合一次性任务、调试。
2. **API 嵌入**：Goose 提供 API 模式，未来由 `web/` 后端或调度器以 API 调起，做四部门自动流转。

## Phase 0 验收（[2026-10-20]）
- [x] 项目骨架 + Goose 配置（DeepSeek provider）就位
- [x] 数据层 `data/skull.db` 初始化（6 表）
- [x] LLM 腿通：DeepSeek 实测回「连通」
- [x] MCP 腿通：filesystem MCP 端到端跑通（见 `mcp_proof.mjs`，harness+MCP+LLM 三腿绿）
- [~] **Goose 二进制**：本沙箱网络限流（~18KB/s）致 40MB 包下载损坏，留待**真机**安装（命令见下）。架构已由最小 harness 证明等价。

## 真机安装 Goose（推荐，网络正常时）
```powershell
# Windows PowerShell
irm https://github.com/aaif-goose/goose/releases/latest/download/goose-x86_64-pc-windows-msvc.zip -OutFile goose.zip
Expand-Archive goose.zip -DestinationPath $env:LOCALAPPDATA\goose
# 把 goose.exe 加入 PATH 后：
goose --version
```
配置已就绪：`%APPDATA%\goose\config.toml`（DeepSeek provider，密钥走 `${DEEPSEEK_API_KEY}`）。
装好后端到端：`goose run "读取 README.md 前三行并总结"`（同 `mcp_proof.mjs` 验证的路径）。

## 获客流水线模块（P0 · 已落地 [2026-10-20]）
- `score.py`：移植自 `priority_engine.py`（2026-10-05 子羿拍板版）的透明评分引擎。权重/阈值/外省降级均可调，纯函数无 IO。
- `ingest.py`：**主表只读**导入 → 解析「综合优先级」→ 按 `score.py` 打分 → 落入 `data/skull.db` 的 `clients` 表。绝不回写主表（红线）。
- 实测：导入 **12,913** 条（与记忆口径吻合），档位 P0 392 / P1 293 / P2 1793 / P3 10435；省份已归一（河北/河北省→河北 等）。
- 用法：`python engine/ingest.py`（venv 内）。新线索/抓取来的客户可用 `score.score_from_string()` 同口径打分后入 `leads`/`clients`。
- 扩展：外部门户线索表单 → `leads` 表 → 评分 → 进 `pipeline`（获客→转化→交付→沉淀）即 Phase 2。
