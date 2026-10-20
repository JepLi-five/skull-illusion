# 骷髅幻戏 · 四部门流转状态机（P2）
# 获客 → 转化 → 交付 → 沉淀，每条线索带档位/评分/到期日，自动判逾期。
# 纯 Python 标准库（sqlite3），复用 score.py 的评分引擎。零依赖。
import os
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from score import score_signals  # noqa: E402

HERE = os.path.dirname(__file__)
DB = os.path.normpath(os.path.join(HERE, "..", "data", "skull.db"))

# 四部门阶段
STAGES = ["acquire", "convert", "deliver", "deposit"]
STAGE_CN = {"acquire": "获客", "convert": "转化", "deliver": "交付", "deposit": "沉淀"}

# 各阶段默认 SLA（天）—— 到期未推进即逾期提醒（子羿可调）
SLA_DAYS = {"acquire": 3, "convert": 7, "deliver": 30, "deposit": 90}


def _conn():
    return sqlite3.connect(DB)


def ensure_schema():
    """幂等补齐字段（已存在的库直接加列，不影响既有数据）。"""
    c = _conn()
    cur = c.cursor()
    cols = {r[1] for r in cur.execute("PRAGMA table_info(leads)")}
    if "priority" not in cols:
        cur.execute("ALTER TABLE leads ADD COLUMN priority TEXT")
    if "score" not in cols:
        cur.execute("ALTER TABLE leads ADD COLUMN score REAL")
    c.commit()
    c.close()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_lead(name, contact=None, intent=None, source="manual", signals=None, flags=None):
    """进一条线索：按 score.py 打分 -> 入 leads + 建获客阶段流水线节点。"""
    ensure_schema()
    signals = set(signals or [])
    flags = set(flags or [])
    score, tier, _contrib = score_signals(signals, flags)
    due = (datetime.now() + timedelta(days=SLA_DAYS["acquire"])).strftime("%Y-%m-%d %H:%M:%S")
    c = _conn()
    cur = c.cursor()
    cur.execute(
        "INSERT INTO leads (name, contact, intent, source, status, priority, score) "
        "VALUES (?,?,?,?,?,?,?)",
        (name, contact, intent, source, "new", tier, score),
    )
    lid = cur.lastrowid
    cur.execute(
        "INSERT INTO pipeline (lead_id, stage, owner, entered_at, due_at, notes) "
        "VALUES (?,?,?,?,?,?)",
        (lid, "acquire", "子羿", _now(), due, "新线索进入获客"),
    )
    c.commit()
    c.close()
    return {"lead_id": lid, "priority": tier, "score": score, "due_at": due}


def advance(lead_id, to_stage, notes=None, due_days=None):
    """推进阶段；自动按 SLA 设到期日。"""
    if to_stage not in STAGES:
        raise ValueError(f"未知阶段: {to_stage}（可选 {STAGES}）")
    ensure_schema()
    days = due_days if due_days is not None else SLA_DAYS[to_stage]
    due = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    c = _conn()
    cur = c.cursor()
    cur.execute(
        "INSERT INTO pipeline (lead_id, stage, owner, entered_at, due_at, notes) "
        "VALUES (?,?,?,?,?,?)",
        (lead_id, to_stage, "子羿", _now(), due, notes or f"推进到{STAGE_CN[to_stage]}"),
    )
    cur.execute("UPDATE leads SET status=? WHERE id=?", (to_stage, lead_id))
    c.commit()
    c.close()
    return {"lead_id": lead_id, "stage": to_stage, "due_at": due}


def overdue():
    """已逾期（due_at < now，且仍是当前阶段）。"""
    ensure_schema()
    c = _conn()
    rows = c.execute(
        """
        SELECT p.stage, l.id, l.name, l.priority, p.due_at, p.notes
        FROM pipeline p JOIN leads l ON l.id = p.lead_id
        WHERE p.due_at IS NOT NULL AND p.due_at < ?
          AND p.id = (SELECT MAX(p2.id) FROM pipeline p2 WHERE p2.lead_id = p.lead_id)
        ORDER BY p.due_at
        """,
        (_now(),),
    ).fetchall()
    c.close()
    return rows


def due_soon(days=3):
    """N 天内到期（提前提醒）。"""
    ensure_schema()
    until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    c = _conn()
    rows = c.execute(
        """
        SELECT p.stage, l.id, l.name, l.priority, p.due_at
        FROM pipeline p JOIN leads l ON l.id = p.lead_id
        WHERE p.due_at IS NOT NULL AND p.due_at BETWEEN ? AND ?
          AND p.id = (SELECT MAX(p2.id) FROM pipeline p2 WHERE p2.lead_id = p.lead_id)
        ORDER BY p.due_at
        """,
        (_now(), until),
    ).fetchall()
    c.close()
    return rows


def digest():
    """每日/每周复盘种子：各阶段在办数 + 逾期数 + P0 未动数。"""
    ensure_schema()
    c = _conn()
    out = {}
    for s in STAGES:
        # 当前阶段 = 该线索最新一条流水线记录
        n = c.execute(
            """
            SELECT COUNT(*) FROM pipeline p
            WHERE p.stage = ? AND p.id = (
                SELECT MAX(p2.id) FROM pipeline p2 WHERE p2.lead_id = p.lead_id
            )
            """,
            (s,),
        ).fetchone()[0]
        out[s] = n
    total_leads = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    p0_open = c.execute(
        """
        SELECT COUNT(*) FROM leads l
        WHERE l.priority = 'P0' AND l.status IN ('new','acquire')
        """
    ).fetchone()[0]
    c.close()
    return {"stages": out, "total_leads": total_leads, "p0_open": p0_open,
            "overdue": len(overdue())}


# 需求描述 -> 信号词映射（给外部门户线索补分用；评分仍单源在 score.py）
INTENT_SIGNALS = [
    ("切换", "强切换"), ("改水性", "水性"), ("水性", "水性"),
    ("油性", "油性信号"), ("油", "油性信号"),
    ("急需", "强需求"), ("急", "强需求"), ("马上", "强需求"),
    ("协会", "协会"), ("展会", "展会"),
]


def score_pending():
    """给未打分线索（如外部门户提交）抽信号并打分，保证评分逻辑只有 score.py 一处。"""
    ensure_schema()
    c = _conn()
    cur = c.cursor()
    rows = cur.execute(
        "SELECT id, intent FROM leads WHERE priority IS NULL OR priority = ''"
    ).fetchall()
    for lid, intent in rows:
        txt = str(intent or "")
        sigs = {sig for kw, sig in INTENT_SIGNALS if kw in txt}
        score, tier, _ = score_signals(sigs, set())
        cur.execute("UPDATE leads SET priority=?, score=? WHERE id=?", (tier, score, lid))
    c.commit()
    c.close()
    return len(rows)


def _cli():
    import argparse

    ap = argparse.ArgumentParser(description="四部门流转状态机")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="进一条线索")
    a.add_argument("--name", required=True)
    a.add_argument("--contact")
    a.add_argument("--intent")
    a.add_argument("--source", default="manual")
    a.add_argument("--signals", default="", help="逗号分隔，如 强需求,已接触")

    v = sub.add_parser("advance", help="推进阶段")
    v.add_argument("lead_id", type=int)
    v.add_argument("stage", choices=STAGES)
    v.add_argument("--notes")

    sub.add_parser("digest", help="复盘摘要")
    sub.add_parser("score", help="给未打分线索（含门户提交）补分")
    sub.add_parser("overdue", help="逾期清单")
    d = sub.add_parser("due", help="N天内到期")
    d.add_argument("--days", type=int, default=3)

    args = ap.parse_args()

    if args.cmd == "add":
        sigs = [s.strip() for s in args.signals.split(",") if s.strip()]
        r = add_lead(args.name, args.contact, args.intent, args.source, sigs)
        print(f"[ok] 线索 #{r['lead_id']} 档位={r['priority']} 分={r['score']} 获客到期={r['due_at']}")
    elif args.cmd == "advance":
        r = advance(args.lead_id, args.stage, args.notes)
        print(f"[ok] #{r['lead_id']} -> {r['stage']}({STAGE_CN[r['stage']]}) 到期={r['due_at']}")
    elif args.cmd == "digest":
        d = digest()
        print("【四部门流转 · 复盘摘要】")
        for s in STAGES:
            print(f"  {STAGE_CN[s]}({s}): {d['stages'][s]}")
        print(f"  线索总数: {d['total_leads']}   P0未动: {d['p0_open']}   逾期: {d['overdue']}")
    elif args.cmd == "score":
        n = score_pending()
        print(f"[ok] 已补分线索: {n} 条")
    elif args.cmd == "overdue":
        rows = overdue()
        print(f"【逾期清单】共 {len(rows)} 条")
        for r in rows:
            print(f"  [{STAGE_CN.get(r[0], r[0])}] #{r[1]} {r[2]} 档={r[3]} 到期={r[4]}")
    elif args.cmd == "due":
        rows = due_soon(args.days)
        print(f"【{args.days} 天内到期】共 {len(rows)} 条")
        for r in rows:
            print(f"  [{STAGE_CN.get(r[0], r[0])}] #{r[1]} {r[2]} 档={r[3]} 到期={r[4]}")


if __name__ == "__main__":
    _cli()
