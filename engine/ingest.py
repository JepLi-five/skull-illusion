# 骷髅幻戏 · 获客流水线（P0）— 主表只读导入 + 评分灌库
# 读取权威主表（统一总表，只读），解析「综合优先级」字符串、按 score.py 打分，
# 结果落入本地 data/skull.db 的 clients 表。绝不回写主表。
import os
import sys
import sqlite3

import openpyxl

sys.path.insert(0, os.path.dirname(__file__))
from score import parse_priority, score_signals

# 主表路径走环境变量（不写死本机路径：便于开源、换机、保密目录结构）
MASTER = os.environ.get("MASTER_XLSX")
SHEET = "统一总表"
DB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "skull.db"))

# 省份归一（记忆红线：河北/河北省 异写需归一）
PROV_NORM = {
    "河北省": "河北", "河南省": "河南", "山东省": "山东", "山西省": "山西",
    "北京市": "北京", "天津市": "天津",
}


def norm_prov(p):
    if p is None:
        return None
    p = str(p).strip()
    return PROV_NORM.get(p, p)


def main():
    if not MASTER:
        raise SystemExit(
            "请先设置环境变量 MASTER_XLSX 指向只读的客户主表 xlsx，例如：\n"
            "  MASTER_XLSX=/path/to/主表_当前.xlsx python ingest.py"
        )
    wb = openpyxl.load_workbook(MASTER, read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    idx = {h: i for i, h in enumerate(header) if h is not None}
    ci = idx["综合优先级"]
    ni = idx["企业名称"]
    pi = idx.get("省份")
    ii = idx.get("行业类别")
    phi = idx.get("联系电话")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE source='master'")  # 每次全量刷新只读副本

    n = 0
    skip = 0
    for r in rows:
        name = r[ni]
        if name is None or str(name).strip() == "":
            skip += 1
            continue
        orig_tier, toks, flags = parse_priority(r[ci])
        score, _engine_tier, _contrib = score_signals(toks, flags)
        # 权威档位用主表标签；score 用引擎可审计分
        priority = orig_tier if orig_tier != "?" else _engine_tier
        cur.execute(
            "INSERT INTO clients (name, province, industry, phone, priority, score, source) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                str(name).strip(),
                norm_prov(r[pi]),
                str(r[ii]) if r[ii] is not None else None,
                str(r[phi]) if r[phi] is not None else None,
                priority,
                score,
                "master",
            ),
        )
        n += 1
    conn.commit()

    print(f"[ok] 主表只读导入 clients：新增 {n} 条，跳过无名 {skip} 条")
    print("     档位分布：")
    for t in ("P0", "P1", "P2", "P3"):
        cnt = cur.execute("SELECT COUNT(*) FROM clients WHERE priority=?", (t,)).fetchone()[0]
        print(f"       {t}: {cnt}")
    total = cur.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    print(f"     clients 总条数: {total}")
    conn.close()


if __name__ == "__main__":
    main()
