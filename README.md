# 骷髅幻戏 · skull-illusion

**一人公司的去中心化私有平台** —— 主权归你、零订阅、自托管、数据不出本机。

它解决的问题很朴素：一个人的公司，客户、线索、回款、知识这些命脉，不该躺在 Excel 和脑子里，也不该寄存在别人的云上。

---

## 它是什么

| 形态 | 说明 |
|---|---|
| **私有版 WorkBuddy** | 本地 agent 工作台，跑你的自动化 / 技能 / MCP |
| **「千问工作」助手** | 产品名（非必用 Qwen 模型），与上一项共用同一引擎底座 |
| **中枢** | 你自己那台常开的 PC；手机经 Tailscale 作随身入口 |
| **引擎** | Goose（AAIF / Linux 基金会，Apache 2.0，Rust，本地优先、原生 MCP、零订阅） |
| **大脑** | LLM 可插拔：DeepSeek API（重活）+ 本地小模型（轻活 / 离线兜底） |

> "去中心化"指**主权与数据在你机器上**，不是断网。重推理上云、轻任务本地，是刻意的取舍。

---

## 架构

```
     手机（随身入口）
        │  Tailscale（P2P，仅你的设备）
        ▼
   你的常开 PC（中枢）
   ┌──────────────────────────────────┐
   │  引擎底座 Goose（或薄 harness）   │
   │  ├─ 四部门流水线：获客→转化→交付→沉淀 │
   │  ├─ MCP 客户端（接任意 MCP）      │
   │  └─ LLM 适配层（DeepSeek / 本地）  │
   ├──────────────────────────────────┤
   │  本地数据层：SQLite（客户/知识/线索/流水线）│
   ├──────────────────────────────────┤
   │  web：内部看板(3000) + 外部门户(3001)   │
   └──────────────────────────────────┘
```

**客户主表（Excel）只读** —— 只作派生来源，增强副本落 SQLite，绝不回写。

---

## 目录结构

```
skull-illusion/
├── engine/                 # 引擎层
│   ├── score.py            # 评分引擎（权重/阈值可调，可审计）
│   ├── ingest.py           # 主表只读导入 → 打分 → 落库
│   ├── pipeline.py         # 四部门流转状态机（SLA/逾期/复盘）
│   └── mcp_proof.mjs        # 最小端到端证明：harness + MCP + LLM
├── web/
│   ├── dash-server.mjs     # 内部看板（零依赖，口令保护）
│   ├── portal-server.mjs   # 外部门户（展示+引流，不碰钱）
│   └── app/                # Next.js 脚手架（可选 UI 路线）
├── config/                 # 配置样例（真实密钥不入库）
├── data/                   # SQLite schema + 初始化（*.db 不入库）
└── docs/                   # Tailscale 通道、MCP 注册表
```

---

## 快速开始

```bash
# 1) 初始化数据层
python data/init_db.py

# 2) 导入客户主表（只读；路径走环境变量，不写死）
MASTER_XLSX=/path/to/主表_当前.xlsx python engine/ingest.py

# 3) 起内部看板（默认只听 127.0.0.1）
cd web && node dash-server.mjs          # http://127.0.0.1:3000
#    手机经 Tailscale 访问：
#    BIND=<你的TailscaleIP> DASH_TOKEN=<强口令> node dash-server.mjs

# 4) 起外部门户（展示+引流）
node portal-server.mjs                   # http://127.0.0.1:3001

# 5) 线索流转与复盘
python engine/pipeline.py add --name "某某机械厂" --signals "强需求,已接触"
python engine/pipeline.py advance 1 convert
python engine/pipeline.py score          # 给未打分线索补分（含门户提交）
python engine/pipeline.py digest         # 复盘摘要
```

依赖极少：看板与门户**只用 Node 内置模块**（`http` + `node:sqlite`），不装任何 npm 包；数据层只用 Python 标准库 + `openpyxl`。

---

## 安全（默认即安全）

- 看板 / 门户**默认只监听 `127.0.0.1`**，公网与局域网均不可达；需要手机访问时显式 `BIND=<IP>`。
- 看板支持 `DASH_TOKEN` 口令闸门，不符直接 401；页面内链接与表单自动透传 token。
- 密钥一律走环境变量（`DEEPSEEK_API_KEY`），**不落库、不入库**。
- 数据库、`.env`、`node_modules` 均在 `.gitignore` 内，**客户数据永不进仓库**。

---

## 业务合规

- 客户主表**只读不回写**；对外展示脱敏。
- 外部门户**仅展示与咨询，不在线交易、不在线收款**；成交走微信 / 电话。
- 线索数据只存本地，不上传云端。

---

## 路线

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 骨架 + 数据层 + LLM + MCP 端到端验证 | ✅ |
| P0 | 获客流水线：主表只读导入 + 评分入库 | ✅ |
| P1 | 内部看板（零依赖、口令、手机自适应） | ✅ |
| P2 | 四部门流转状态机（SLA / 逾期 / 复盘） | ✅ |
| P3 | 外部门户（案例 / 科普 / CTA / 线索表单） | ✅ |
| P4 | 手机 Tailscale 实机 + 备份 | 进行中 |
| P5 | 开源橱窗 | 进行中 |

---

## 许可

MIT —— 见 `LICENSE`。引擎底座 Goose 为 Apache 2.0（AAIF / Linux 基金会）。
