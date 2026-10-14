#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长型 Agent 平台 · 新客户一键接入（M5 收口：把平台固化成可分发模板）。

一条命令把「一个人公司接新客户」从改代码变成写一条配置：
  python onboard_client.py --id profile_003 --company "某某新材料" --industry 工业漆 \
      --region 示例市 --staging /path/to/脱敏样例.csv --share 0.08 --cpl 30

它做四件事（全部零依赖、红线②守牢）：
  1. 红线校验 —— staging 必须是 ≤10 行的脱敏样例（禁止导入 1.2 万主表/评分引擎/采集管线）。
  2. 自包含拷贝 —— 把样例拷进 tenants/<id>/，平台不再依赖客户原始文件路径。
  3. 写入注册表 —— tenants/registry.json 追加一条租户配置（配置化，不改主程序）。
  4. 初始化账本 —— ledger/<id>.csv 建好，M5 明账/防跳单即生效。

之后跑 `python run_m4_transport.py` 即把新客户并入多租户看板（含明账/防跳单）。
"""

import argparse
import csv
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "tenants", "registry.json")
TENANTS_DIR = os.path.join(HERE, "tenants")
LEDGER_DIR = os.path.join(HERE, "ledger")
MAX_DECOY_ROWS = 10  # 红线②：平台内只保留 ≤10 家脱敏样例，主表永不出门


def count_rows(path: str) -> int:
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # 去掉表头


def main():
    ap = argparse.ArgumentParser(description="成长型 Agent 平台 · 新客户一键接入")
    ap.add_argument("--id", required=True, help="租户ID，如 profile_003")
    ap.add_argument("--company", required=True, help="公司名")
    ap.add_argument("--industry", required=True, help="行业，如 工业漆/UV胶/工业耗材")
    ap.add_argument("--region", required=True, help="主战场，如 示例市/示例市B")
    ap.add_argument("--staging", required=True, help="脱敏样例 CSV 路径（≤10 行）")
    ap.add_argument("--script-lib", default="腿2_企微自动回复/话术库.json",
                    help="话术库相对客户包的路径（默认复用内置话术库做演示）")
    ap.add_argument("--share", type=float, default=0.08, help="分成比例，如 0.08 表 8%%")
    ap.add_argument("--cpl", type=float, default=30.0, help="单线索成本（元）")
    args = ap.parse_args()

    # 1) 红线校验
    if not os.path.isfile(args.staging):
        print("[红线拦截] staging 文件不存在：", args.staging); sys.exit(1)
    n = count_rows(args.staging)
    if n > MAX_DECOY_ROWS:
        print("[红线拦截] staging 行数 %d > %d（红线②：平台仅留脱敏样例，主表/引擎/管线不出门）"
              % (n, MAX_DECOY_ROWS)); sys.exit(1)
    print("[红线②校验] staging 行数 %d ≤ %d，脱敏样例合规" % (n, MAX_DECOY_ROWS))

    # 2) 自包含拷贝
    dest_dir = os.path.join(TENANTS_DIR, args.id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_staging = os.path.join(dest_dir, "staging_脱敏样例.csv")
    shutil.copy(args.staging, dest_staging)
    print("[自包含] 样例已拷入：", dest_staging)

    # 3) 写入注册表
    reg = {}
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
    if args.id in reg:
        print("[提示] %s 已存在于注册表，将覆盖其配置" % args.id)
    reg[args.id] = {
        "company": args.company, "industry": args.industry, "region": args.region,
        "staging_path": os.path.relpath(dest_staging, HERE),
        "script_lib_path": args.script_lib,
        "share_pct": args.share, "cpl": args.cpl,
    }
    os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print("[注册表] 已写入 tenants/registry.json：", args.id)

    # 4) 初始化账本
    os.makedirs(LEDGER_DIR, exist_ok=True)
    ledger_path = os.path.join(LEDGER_DIR, "ledger_%s.csv" % args.id)
    if not os.path.exists(ledger_path):
        open(ledger_path, "w", encoding="utf-8").close()  # 建空文件，首笔账由运行产生
    print("[账本] 已初始化：", ledger_path)

    print("\n[完成] 新客户 %s（%s · %s）接入就绪。" % (args.id, args.company, args.industry))
    print("下一步：python run_m4_transport.py  →  新客户自动并入多租户看板（含 M5 明账/防跳单）")


if __name__ == "__main__":
    main()
