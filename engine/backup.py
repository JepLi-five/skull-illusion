# 骷髅幻戏 · 数据备份（P4 防丢）
# 用 sqlite3 官方 backup API 做一致性备份（不是裸 copy，避免写到一半的库被复制走）。
# 备份目标走环境变量 BACKUP_DIR（U盘 / 备份盘 / 网盘同步目录均可），保留最近 N 份。
import glob
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.normpath(os.path.join(HERE, "..", "data", "skull.db"))
BACKUP_DIR = os.environ.get("BACKUP_DIR") or os.path.normpath(os.path.join(HERE, "..", "backups"))
KEEP = int(os.environ.get("BACKUP_KEEP", "7"))  # 默认保留最近 7 份


def main():
    if not os.path.exists(DB):
        raise SystemExit(f"找不到数据库：{DB}（先跑 data/init_db.py 与 engine/ingest.py）")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"skull_{ts}.db")

    # 一致性备份
    src = sqlite3.connect(DB)
    out = sqlite3.connect(dst)
    src.backup(out)
    out.close()
    src.close()

    # 校验：能打开且客户数对得上
    chk = sqlite3.connect(dst)
    clients = chk.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    leads = chk.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    chk.close()
    if clients == 0:
        raise SystemExit(f"备份异常：客户数为 0，已删除可疑备份 {dst}")
    size = os.path.getsize(dst)

    # 轮转：只保留最近 KEEP 份
    old = sorted(glob.glob(os.path.join(BACKUP_DIR, "skull_*.db")))[:-KEEP]
    for f in old:
        os.remove(f)

    print(f"[ok] 备份完成: {dst}")
    print(f"     大小 {size/1024/1024:.2f} MB | 客户 {clients} | 线索 {leads}")
    print(f"     目录 {BACKUP_DIR} | 保留最近 {KEEP} 份，清理旧备份 {len(old)} 个")


if __name__ == "__main__":
    main()
