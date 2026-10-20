#!/usr/bin/env python3
# 骷髅幻戏 · 初始化本地数据层（SQLite，零依赖，标准库）
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "schema.sql")
DB = os.path.join(HERE, "skull.db")


def main():
    if os.path.exists(DB):
        print(f"[skip] 已存在 {DB}，不覆盖。删除后再跑可重建。")
        return
    with sqlite3.connect(DB) as conn:
        with open(SCHEMA, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print(f"[ok] 已建 {DB}")
    print("     表:", ", ".join(tables))


if __name__ == "__main__":
    main()
