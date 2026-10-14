#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腿1 客户检索 - 线索看板生成器（仅用 Python 3 标准库，零外部依赖）

功能：读取 staging CSV（线索卡数据），产出自包含 HTML 看板
      （评分档位分布 + 区域分布 + 需求信号分布，内联 SVG 柱状图），
      可直接发给甲方或手机打开。
对标：Kalk/Odoo 的 lead scoring + 实时 pipeline 看板。

用法：
    python 线索看板.py [staging_csv] [输出html]
    默认：读取本目录 staging示例_脱敏10家.csv，输出 线索看板_YYYYMMDD.html

依赖：仅 csv / datetime / collections / html（标准库）
"""

import csv
import sys
import os
import html
from collections import Counter
from datetime import date

DEFAULT_CSV = "staging示例_脱敏10家.csv"
OUT_DEFAULT = "线索看板_{}.html".format(date.today().strftime("%Y%m%d"))
TIERS = ["P0", "P1", "P2", "P3"]


def load(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            r["序号"] = (r.get("序号") or "").strip() or str(i)
            rows.append(r)
    return rows


def bar_chart(title, counter, order=None):
    items = order if order else [k for k, _ in counter.most_common()]
    items = [k for k in items if k]
    maxv = max([counter.get(k, 0) for k in items], default=1) or 1
    parts = ['<div class="chart-title">{}</div>'.format(html.escape(title))]
    for k in items:
        v = counter.get(k, 0)
        w = int(round(100.0 * v / maxv)) if maxv else 0
        parts.append(
            '<div class="row"><span class="lab">{}</span>'
            '<span class="track"><span class="fill" style="width:{}%"></span></span>'
            '<span class="val">{}</span></div>'.format(html.escape(str(k)), w, v)
        )
    return '<div class="chart">' + "".join(parts) + "</div>"


def build(rows):
    tiers = Counter((r.get("评分档位") or "").strip() for r in rows)
    regions = Counter((r.get("地区") or "").strip() for r in rows)
    signals = Counter()
    for r in rows:
        s = (r.get("需求信号") or "").strip()
        if s:
            signals[s] += 1
    L = []
    L.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
             '<title>成长型 Agent 平台 · 客户线索看板</title>')
    L.append('<style>')
    L.append(
        ''':root{--bg:#f5f7fa;--card:#fff;--primary:#2f6fed;--text:#1f2933;--muted:#6b7785;--line:#e6ebf2;}
    *{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);}
    .hero{background:linear-gradient(135deg,#2f6fed,#1f4fc4);color:#fff;padding:22px 18px;text-align:center;} .hero h1{margin:0;font-size:20px;} .hero p{margin:6px 0 0;font-size:13px;opacity:.95;}
    .wrap{max-width:760px;margin:0 auto;padding:18px;} section{background:var(--card);border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.05);}
    .kpi{display:flex;gap:12px;} .kpi div{flex:1;background:var(--card);border-radius:12px;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.05);} .kpi .n{font-size:24px;font-weight:800;color:var(--primary);} .kpi .l{font-size:12px;color:var(--muted);margin-top:4px;}
    .chart-title{font-weight:700;color:var(--primary);margin:0 0 10px;font-size:15px;} .row{display:flex;align-items:center;margin:6px 0;font-size:13px;} .row .lab{width:64px;color:var(--text);flex:none;} .row .track{flex:1;background:var(--line);border-radius:6px;height:16px;margin:0 8px;overflow:hidden;} .row .fill{display:block;height:100%;background:var(--primary);border-radius:6px;} .row .val{width:28px;text-align:right;color:var(--muted);flex:none;}
    .note{font-size:12px;color:var(--muted);margin-top:10px;} .flag{background:#fff8ef;border:1px solid #ffe2b8;color:#8a6d1a;border-radius:8px;padding:10px 12px;font-size:12px;margin-top:12px;}
    '''
    )
    L.append('</style></head><body>')
    L.append('<div class="hero"><h1>成长型 Agent 平台 · 客户线索看板</h1>'
             '<p>{} · 共 {} 条线索</p></div>'.format(date.today().isoformat(), len(rows)))
    L.append('<div class="wrap">')
    L.append(
        '<div class="kpi"><div><div class="n">{}</div><div class="l">线索总数</div></div>'
        '<div><div class="n">{}</div><div class="l">P0 强信号</div></div>'
        '<div><div class="n">{}</div><div class="l">覆盖区域</div></div></div>'.format(
            len(rows), tiers.get("P0", 0), len([k for k in regions if k])
        )
    )
    L.append('<section>' + bar_chart("评分档位分布（P0–P3）", tiers, order=TIERS) + '</section>')
    L.append('<section>' + bar_chart("区域分布（Top）", regions) + '</section>')
    if signals:
        L.append('<section>' + bar_chart("需求信号分布", signals) + '</section>')
    L.append('<div class="flag">本看板由成长型 Agent 平台 · 腿1 自动生成（标准库零依赖）。'
             '红线②：乙方核心资产（主表/评分引擎/采集管线）不随包交付；'
             '本看板仅含甲方自有或公开脱敏数据。</div>')
    L.append('<p class="note">成长型 Agent 平台 · 腿1 看板 · 模板</p>')
    L.append('</div></body></html>')
    return "\n".join(L)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    out = sys.argv[2] if len(sys.argv) > 2 else OUT_DEFAULT
    if not os.path.exists(src):
        print("[错误] 找不到数据文件：{}".format(src))
        sys.exit(1)
    rows = load(src)
    with open(out, "w", encoding="utf-8") as f:
        f.write(build(rows))
    print("[完成] 已生成看板：{}（{} 条线索）".format(out, len(rows)))


if __name__ == "__main__":
    main()
