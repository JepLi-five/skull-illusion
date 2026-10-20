import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

// 数据层只读本地 SQLite（主表绝不回写）
const DB = path.resolve(process.cwd(), '../data/skull.db');

// 每次请求读最新库（避免 build 期预渲染时路径不一致）
export const dynamic = 'force-dynamic';

function Tag({ p }) {
  const cls = { P0: 'p0', P1: 'p1', P2: 'p2', P3: 'p3' }[p] || 'p3';
  return <span className={`tag ${cls}`}>{p || '-'}</span>;
}

export default function Page({ searchParams }) {
  const tier = (searchParams?.tier || '').trim();
  const q = (searchParams?.q || '').trim();

  const db = new DatabaseSync(DB);
  const total = db.prepare('SELECT COUNT(*) AS c FROM clients').get().c;
  const tiers = db.prepare('SELECT priority, COUNT(*) AS n FROM clients GROUP BY priority').all();
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

  const tierCount = {};
  for (const t of tiers) tierCount[t.priority] = t.n;

  const link = (t) => `/?tier=${t}${q ? `&q=${encodeURIComponent(q)}` : ''}`;

  return (
    <main className="wrap">
      <h1>骷髅幻戏 · 客户看板</h1>
      <div className="sub">
        私有平台 · 数据全留本机 · 共 {total} 家客户（主表只读副本，评分来自 priority_engine 移植）
      </div>

      <div className="grid">
        <div className="card">
          <div className="k">客户总数</div>
          <div className="v">{total}</div>
        </div>
        {['P0', 'P1', 'P2', 'P3'].map((t) => (
          <div className="card" key={t}>
            <div className="k">{t} 档</div>
            <div className="v">{tierCount[t] || 0}</div>
          </div>
        ))}
      </div>

      <div className="bar">
        <a href="/" className={!tier ? 'on' : ''}>
          全部
        </a>
        {['P0', 'P1', 'P2', 'P3'].map((t) => (
          <a key={t} href={link(t)} className={tier === t ? 'on' : ''}>
            {t}
          </a>
        ))}
        <form method="get" style={{ display: 'flex', gap: 6 }}>
          {tier ? <input type="hidden" name="tier" value={tier} /> : null}
          <input name="q" defaultValue={q} placeholder="按企业名搜索" />
          <button type="submit">搜索</button>
        </form>
      </div>

      {provinces.length ? (
        <div className="bar">
          <span style={{ color: '#5b6470', fontSize: 13 }}>省份 Top：</span>
          {provinces.map((p) => (
            <span key={p.province} style={{ fontSize: 13 }}>
              {p.province} {p.n}
            </span>
          ))}
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>企业名称</th>
              <th>省份</th>
              <th>行业</th>
              <th>电话</th>
              <th>档位</th>
              <th>评分</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.name}</td>
                <td>{r.province || '-'}</td>
                <td>{r.industry || '-'}</td>
                <td>{r.phone || '-'}</td>
                <td>
                  <Tag p={r.priority} />
                </td>
                <td>{r.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="sub" style={{ marginTop: 10 }}>
        最多显示 200 条（按评分降序）。主表只读，不回写。
      </div>
    </main>
  );
}
