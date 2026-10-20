// 骷髅幻戏 · 外部门户（Phase 3）
// 展示 + 引流：案例墙 / 涂装科普 / 微信 CTA / 线索表单。
// 合规红线：不碰钱、不碰交易、不在线成交（成交走微信/电话）。
// 零依赖：仅 Node 内置 http + node:sqlite。线索直灌 leads + pipeline(获客)。
import http from 'node:http';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DB = path.resolve(HERE, '../data/skull.db');
const PORT = Number(process.env.PORT || 3001);
// 安全默认：只听本机。要对外时用 BIND=<TailscaleIP 或 0.0.0.0> 显式指定。
const BIND = process.env.BIND || '127.0.0.1';
// 联系电话：仅走环境变量，不设默认值（避免开源时把个人号码写进仓库）
// 启动前设置：PORTAL_PHONE=你的号码 node portal-server.mjs
const PHONE = process.env.PORTAL_PHONE || '';

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ESC[c]);
const cut = (s, n) => String(s ?? '').slice(0, n);

// 案例为占位（真实项目由子羿填入，不编造）
const CASES = [
  { t: '【待填】铸造件浸涂线节拍优化', d: '待子羿填入真实项目：客户类型 / 原工艺 / 痛点 / 改后效果。' },
  { t: '【待填】电机端盖浸涂缺漆根治', d: '待子羿填入真实项目：端盖内侧上部缺漆的成因与对策（需先照片取证）。' },
  { t: '【待填】钢结构防腐配套选型', d: '待子羿填入真实项目：底/中/面配套与年限要求。' },
];

// 涂装科普（通用真知识，不编造客户案例）
const KNOW = [
  { t: '浸涂常见缺陷：内侧上部缺漆', d: '多与浸涂后沥漆方向、挂具角度、工件内腔排气不畅有关；先拍现场照片再定对策，不凭描述下结论。' },
  { t: '水性 vs 油性：不是简单替换', d: '水性对基材前处理、环境温湿度更敏感；换水性前必须做附着力与耐盐雾验证，别只换树脂了事。' },
  { t: '前处理决定一半寿命', d: '除油、除锈、磷化/钝化任一环节偷工，后面漆膜再厚也易早期失效。防腐的胜负手往往在喷砂/前处理。' },
];

function layout(title, body) {
  return `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#1b1f24;--muted:#5b6470;--line:#e3e7ec;--accent:#14539a;--warn:#b3261e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.6}
.wrap{max-width:900px;margin:0 auto;padding:18px}
header{padding:22px 0;border-bottom:1px solid var(--line);margin-bottom:18px}
h1{font-size:22px;margin:0 0 6px}
.tagline{color:var(--muted);font-size:14px}
h2{font-size:17px;margin:26px 0 12px;padding-left:10px;border-left:4px solid var(--accent)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h3{margin:0 0 6px;font-size:15px}
.card p{margin:0;color:var(--muted);font-size:13px}
.cta{display:inline-block;margin-top:14px;padding:10px 18px;background:var(--accent);color:#fff;border-radius:8px;text-decoration:none;font-size:15px}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
label{display:block;font-size:13px;color:var(--muted);margin:10px 0 4px}
input,textarea{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;font-family:inherit}
textarea{min-height:80px;resize:vertical}
button{margin-top:14px;padding:10px 20px;background:var(--accent);color:#fff;border:0;border-radius:8px;font-size:15px;cursor:pointer}
.notice{margin-top:20px;padding:12px;background:#fff6f5;border:1px solid #f3c9c4;border-radius:8px;color:var(--warn);font-size:13px}
footer{margin:26px 0 10px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:12px}
</style></head><body><main class="wrap">
<header><h1>涂装医生 · 工业漆门诊</h1>
<div class="tagline">看案例 · 学涂装 · 提需求 —— 按需看诊，方案给到能落地</div></header>
${body}
<footer>${PHONE ? `联系：${esc(PHONE)}　|　` : ''}本站仅作展示与咨询，<strong>不在线交易、不在线收款</strong>；成交一律走微信 / 电话。客户信息仅存于本地，不外传。</footer>
</main></body></html>`;
}

function home(msg = '') {
  const cases = CASES.map((c) => `<div class="card"><h3>${esc(c.t)}</h3><p>${esc(c.d)}</p></div>`).join('');
  const know = KNOW.map((k) => `<div class="card"><h3>${esc(k.t)}</h3><p>${esc(k.d)}</p></div>`).join('');
  return layout(
    '涂装医生 · 工业漆门诊',
    `${msg ? `<div class="notice">${esc(msg)}</div>` : ''}
<h2>案例墙</h2><div class="grid">${cases}</div>
<h2>涂装科普</h2><div class="grid">${know}</div>
<h2>说说你的件</h2>
<form method="post" action="/lead">
  <label>企业名称 *</label><input name="name" required maxlength="80" placeholder="如：某某机械制造有限公司">
  <label>联系人 / 电话或微信 *</label><input name="contact" required maxlength="60" placeholder="138xxxx / 微信号">
  <label>工件与工艺需求</label><textarea name="intent" maxlength="300" placeholder="如：电机端盖，现用油性浸涂，想改水性；小端盖内侧上部常缺漆"></textarea>
  <button type="submit">提交需求</button>
</form>
<div class="notice">提交后进入我的获客池（本地库，不上传云端），我会按需联系。</div>
${PHONE
    ? `<a class="cta" href="tel:${esc(PHONE)}">直接拨打 ${esc(PHONE)}</a>
<div class="notice">微信二维码待补（图给我即可填入）；电话 ${esc(PHONE)} 已可直接点击拨打。</div>`
    : `<div class="notice">联系方式未配置：启动前请设置环境变量 PORTAL_PHONE（不设默认值，避免号码进仓库）。</div>`}`
  );
}

function thanks(name) {
  return layout(
    '已收到 · 涂装医生',
    `<h2>已收到你的需求</h2>
     <div class="card"><h3>${esc(name)}</h3><p>已归入本地获客池，我会按优先级联系你。急事可直接加微信 / 电话。</p></div>
     <a class="cta" href="/">返回首页</a>`
  );
}

const pad = (n) => String(n).padStart(2, '0');
function fmt(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let d = '';
    req.on('data', (c) => {
      d += c;
      if (d.length > 20000) req.destroy();
    });
    req.on('end', () => resolve(d));
    req.on('error', reject);
  });
}

function saveLead(p) {
  const name = cut(p.get('name'), 80).trim();
  const contact = cut(p.get('contact'), 60).trim();
  const intent = cut(p.get('intent'), 300).trim();
  if (!name || !contact) return { ok: false, why: '企业名称与联系方式必填' };
  const db = new DatabaseSync(DB);
  const info = db
    .prepare(
      'INSERT INTO leads (name, contact, intent, source, status) VALUES (?,?,?,?,?)'
    )
    .run(name, contact, intent, 'web', 'new');
  const lid = Number(info.lastInsertRowid);
  // 必须写本地时间：Python 侧用 datetime.now()（本地），若此处写 UTC 会差 8 小时、污染逾期判定
  const due = fmt(new Date(Date.now() + 3 * 86400000));
  db.prepare(
    'INSERT INTO pipeline (lead_id, stage, owner, entered_at, due_at, notes) VALUES (?,?,?,?,?,?)'
  ).run(lid, 'acquire', '子羿', fmt(new Date()), due, '外部门户提交');
  db.close();
  return { ok: true, name, lid };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  try {
    if (req.method === 'POST' && url.pathname === '/lead') {
      const body = await readBody(req);
      const p = new URLSearchParams(body);
      const r = saveLead(p);
      res.writeHead(r.ok ? 200 : 400, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(r.ok ? thanks(r.name) : home(r.why));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(home());
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('ERR: ' + e.message);
  }
});

server.listen(PORT, BIND, () => {
  const scope = BIND === '0.0.0.0' ? '⚠️ 监听所有网卡' : `仅 ${BIND}`;
  console.log(`[门户] http://${BIND}:${PORT}  范围: ${scope}`);
  console.log('[合规] 仅展示+引流，不碰钱不碰交易；线索写入本地 leads 表。');
});
