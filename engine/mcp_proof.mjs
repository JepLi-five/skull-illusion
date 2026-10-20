// 骷髅幻戏 · 最小端到端证明（harness + MCP + LLM）
// 本脚本充当"薄 harness"：连接 filesystem MCP 取目录 → 交 DeepSeek 解读。
// 证明三腿打通，架构与 Goose 调 MCP 完全一致；Goose 为真机生产 harness。
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "node:path";

const ROOT = path.resolve(".."); // skull-illusion 根
// 密钥一律走环境变量，不读本机凭证文件、不硬编码路径（对外安全）
const KEY = process.env.DEEPSEEK_API_KEY;
if (!KEY) {
  console.error("请先设置环境变量 DEEPSEEK_API_KEY 再运行本脚本。");
  process.exit(1);
}

async function main() {
  // 1) MCP 腿：起 filesystem server（经 npx，npm 源）
  const transport = new StdioClientTransport({
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-filesystem", ROOT],
  });
  const client = new Client({ name: "skull-proof", version: "0.0.1" });
  await client.connect(transport);
  const tools = await client.listTools();
  console.log("[MCP] 已连 filesystem，工具:", tools.tools.map((t) => t.name).join(", "));

  // 2) 调 list_directory 取项目根
  const res = await client.callTool({ name: "list_directory", arguments: { path: ROOT } });
  const listing = res.content.map((c) => c.text).join("\n").slice(0, 600);
  console.log("[MCP] 项目根目录(节选):\n" + listing);

  // 3) LLM 腿：DeepSeek 基于 MCP 结果解读
  const r = await fetch("https://api.deepseek.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "deepseek-chat",
      messages: [
        {
          role: "user",
          content: `这是我的项目根目录文件清单：\n${listing}\n请用一句话说明这个项目的用途。`,
        },
      ],
      max_tokens: 80,
    }),
  });
  const j = await r.json();
  console.log("[LLM] DeepSeek 解读:", j.choices?.[0]?.message?.content);

  await client.close();
  console.log("DONE");
}

main().catch((e) => {
  console.error("ERR", e);
  process.exit(1);
});
