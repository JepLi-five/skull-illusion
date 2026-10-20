// 骷髅幻戏 · 客户看板服务（零依赖版）
// 只用 Node 内置模块：http + node:sqlite。不装任何 npm 包、不经原生二进制，
// 因此不受沙箱/网络限制；真机同样直接可跑，手机经 Tailscale 访问。
// 数据只读 ../data/skull.db；主表绝不回写。
import http from 'node:http';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DB = path.resolve(HERE, '../data/skull.db');
const PORT = Number(process.env.PORT || 3000);

// ── 安全默认 ──────────────────────────────────────────
// 默认只监听本机 127.0.0.1（公网/局域网都碰不到）。
// 需要手机经 Tailscale 访问时，显式指定 BIND=<你的Tailscale IP>，不要裸露 0.0.0.0。
const BIND = process.env.BIND || '127.0.0.1';
// 可选口令：设了 DASH_TOKEN 后必须带 ?token=xxx 才能访问。
const TOKEN = process.env.DASH_TOKEN || '';

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ESC[c]);

const TIERS = ['P0', 'P1', 'P2', 'P3'];

function page(searchParams) {
  const tier = (searchParams.get('tier') || '').trim();
  const q = (searchParams.get('q') || '').trim();
  const token = (searchParams.get('token') || '').trim();

  const db = new DatabaseSync(DB);
  const total = db.prepare('SELECT COUNT(*) AS c FROM clients').get().c;
  const tierRows = db
    .prepare('SELECT priority, COUNT(*) AS n FROM clients GROUP BY priority')
    .all();
  const provinces = db
    .prepare(
      "SELECT province, COUNT(*) AS n FROM clients WHERE province IS NOT NULL AND province <> '' GROUP BY province ORDER BY n DESC LIMIT 8"
    )
    .all();

  const where = [];
  const args = [];
  if (tier) {
    where.push('priority = ?');
    args.push(tier);
  }
  if (q) {
    where.push('name LIKE ?');
    args.push(`%${q}%`);
  }
  const sql =
    'SELECT name, province, industry, phone, priority, score FROM clients' +
    (where.length ? ' WHERE ' + where.join(' AND ') : '') +
    ' ORDER BY score DESC, id LIMIT 200';
  const rows = db.prepare(sql).all(...args);
  db.close();

  const count = {};
  for (const r of tierRows) count[r.priority] = r.n;

  // 口令需随链接/表单透传，否则点筛选会被踢出
  const tok = token ? `&token=${encodeURIComponent(token)}` : '';
  const home = token ? `/?token=${encodeURIComponent(token)}` : '/';
  const qs = (t) => `?tier=${t}${q ? `&q=${encodeURIComponent(q)}` : ''}${tok}`;

  const cards = [
    `<div class="card"><div class="k">客户总数</div><div class="v">${total}</div></div>`,
    ...TIERS.map(
      (t) =>
        `<div class="card"><div class="k">${t} 档</div><div class="v">${count[t] || 0}</div></div>`
    ),
  ].join('');

  const filters =
    `<a href="${home}" class="${!tier ? 'on' : ''}">全部</a>` +
    TIERS.map((t) => `<a href="${qs(t)}" class="${tier === t ? 'on' : ''}">${t}</a>`).join('');

  const prov = provinces.length
    ? provinces.map((p) => `${esc(p.province)} ${p.n}`).join(' · ')
    : '-';

  const body = rows
    .map(
      (r) => `<tr>
      <td>${esc(r.name)}</td>
      <td>${esc(r.province)}</td>
      <td>${esc(r.industry)}</td>
      <td>${esc(r.phone)}</td>
      <td><span class="tag ${(r.priority || 'P3').toLowerCase()}">${esc(r.priority)}</span></td>
      <td>${esc(r.score)}</td>
    </tr>`
    )
    .join('');

  return `<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>骷髅幻戏 · 客户看板</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#1b1f24;--muted:#5b6470;--line:#e3e7ec;--accent:#14539a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}
@media(max-width:700px){.grid{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .k{font-size:12px;color:var(--muted)}
.card .v{font-size:22px;font-weight:700;margin-top:4px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center}
.bar a{padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--text);text-decoration:none;font-size:13px}
.bar a.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.bar input{padding:6px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px}
.bar button{padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);font-size:13px;cursor:pointer}
.table-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{color:var(--muted);font-weight:600}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.p0{background:#fde2e2;color:#b3261e}.p1{background:#fff0d6;color:#8a5300}
.p2{background:#e2efff;color:#14539a}.p3{background:#eceef1;color:#5b6470}
</style></head>
<body><main class="wrap">
<h1>骷髅幻戏 · 客户看板</h1>
<div class="sub">私有平台 · 数据全留本机 · 共 ${total} 家客户（主表只读副本，评分来自 priority_engine 移植）</div>
<div class="grid">${cards}</div>
<div class="bar">${filters}
  <form method="get" style="display:flex;gap:6px">
    ${tier ? `<input type="hidden" name="tier" value="${esc(tier)}">` : ''}
    ${token ? `<input type="hidden" name="token" value="${esc(token)}">` : ''}
    <input name="q" value="${esc(q)}" placeholder="按企业名搜索">
    <button type="submit">搜索</button>
  </form>
</div>
<div class="bar"><span style="color:#5b6470;font-size:13px">省份 Top：</span><span style="font-size:13px">${prov}</span></div>
<div class="table-wrap"><table>
<thead><tr><th>企业名称</th><th>省份</th><th>行业</th><th>电话</th><th>档位</th><th>评分</th></tr></thead>
<tbody>${body}</tbody></table></div>
<div class="sub" style="margin-top:10px">最多显示 200 条（按评分降序）。主表只读，不回写。</div>
</main></body></html>`;
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  // 口令闸门：设了 DASH_TOKEN 就必须带正确 token
  if (TOKEN && (url.searchParams.get('token') || '') !== TOKEN) {
    res.writeHead(401, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('401 未授权：需要正确的 token（?token=...）');
    return;
  }
  try {
    const html = page(url.searchParams);
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('ERR: ' + e.message);
  }
});

server.listen(PORT, BIND, () => {
  const scope = BIND === '0.0.0.0' ? '⚠️ 监听所有网卡（不建议）' : `仅 ${BIND}`;
  console.log(`[看板] http://${BIND}:${PORT}  范围: ${scope}`);
  console.log(`[安全] 口令保护: ${TOKEN ? '已开启' : '未开启（如需手机访问请先设 DASH_TOKEN）'}`);
});
