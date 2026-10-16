# 骷髅幻戏 · skull-illusion

> 一套「可装载的 AI 协作操作系统」种子——把"怎么用 AI 管一家一人公司"的方法论、技能模板、工具脚本开放出来。任何人 clone 后，都能在自己的工作台里显形一个会管获客 / 转化 / 交付 / 沉淀的数字伙伴。

## 它是什么
骷髅幻戏不是某个具体软件，是一颗**种子（模式）**：一套能反复长出的协作契约与技能骨架。它把单人公司最痛的三件事——获客、转化、交付——用可继承、可随身带、可自动执行的系统接管起来。

## 从哪开始（3 步跑通）
```bash
git clone https://github.com/JepLi-five/skull-illusion.git
cd skull-illusion/skills/growth-agent-platform/assets/platform_m2
python run_m4_transport.py        # 开箱跑通 M2–M5：A2A 协作 + 明账/防跳单 + 聚合看板
```
- 接自己的第一个客户：`python onboard_client.py --id profile_003 --company "某某新材料" ...`（参数见下方 SKILL.md）
- 公开前先自检一遍：`python ../../redline-scan/scan.py .`

## 能力展示
- 一人销售公司的「四部门管理法」（获客 / 转化 / 交付 / 沉淀）
- 通用技能模板（全部脱敏，不含任何客户与商业机密）
- **成长型 Agent 平台**：把「单客户 Agent」升级为「多租户量产接入」模板（配置化 / 插件热插拔 / 多租户看板 / Agent 联网协作 / 明账+防跳单，M1–M5 全链路，零依赖自包含；v1.1 起支持 `--tenant` 单租户交付看板（含交付话术与实测记录）；v1.1.2 起客户看板自带线索明细 + 县级区域聚合；v1.2 起支持一键导入任意格式名单（列名自动映射、零依赖读 Excel））→ [skills/growth-agent-platform](skills/growth-agent-platform/SKILL.md)
- 文本 / 报表处理类通用工具脚本
- 心智工坊：把经验结构化沉淀的模板

## 仓库结构
```
skull-illusion/
├── README.md · LICENSE · .gitignore
├── docs/                          方法论：四部门管理法 · 心智工坊模板
├── skills/
│   ├── growth-agent-platform/     ★ 主力：M1–M5 全链路多租户平台
│   │   └── assets/platform_m2/    （agents / core / plugins / 看板 / 接入手册）
│   └── redline-scan/              红线扫描器（公开前自检）
└── tools/                         通用脚本（CSV → Markdown 报表等）
```

## 红线（公开承诺）
本仓库**绝不包含**任何客户数据、密钥、订单账本、合同、内部架构。所有内容均经脱敏，可安全公开。
公开前自检：`python skills/redline-scan/scan.py .`

## 业务合作 / 交流
请走 **GitHub Discussions / Issues**（公开、可沉淀、不留私人联系方式）：
https://github.com/JepLi-five/skull-illusion/discussions

## License
MIT（代码） / CC-BY 4.0（文档）
