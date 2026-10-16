#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户版看板生成器（单租户视角 · 可直接给客户看）

与 multi_tenant_dashboard（乙方内部多租户聚合）严格区分：
  ✅ 本看板只读取「指定租户」自己的 events / ledger / staging；
  ❌ 绝不读取其他租户事件（profile_00x 互不相见）与平台运营数据（platform_ops）——避免跨租户外泄。

用法：
    python 客户版看板.py --tenant profile_003 [--out 客户版看板.html]

输出：自包含 HTML（内联 CSS / 内联 SVG，零 CDN、零后端），可微信发送或手机打开。
依赖：仅 Python 3 标准库。
"""

import os
import re
import csv
import html
import json
import argparse
from datetime import date
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(HERE, "events")
LEDGER_DIR = os.path.join(HERE, "ledger")
REGISTRY = os.path.join(HERE, "tenants", "registry.json")

# 腿 -> 展示名
LEG_NAMES = {
    "leg1_retrieval": "① 线索检索",
    "leg2_wecom": "② 企微自动回复",
    "leg3_sms": "③ 短信触达",
}


def load_profile(tid):
    """租户配置（公司名/行业/区域/staging 路径）。"""
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
        if tid in reg:
            c = reg[tid]
            return {
                "company": c.get("company", tid),
                "industry": c.get("industry", ""),
                "region": c.get("region", ""),
                "staging": os.path.join(HERE, c.get("staging_path", "")),
                "share": c.get("share_pct", 0.08),
            }
    return {"company": tid, "industry": "", "region": "", "staging": "", "share": 0.08}


def load_events(tid):
    """只读本租户事件（严格按 tenant_id 过滤，杜绝跨租户）。"""
    path = os.path.join(EVENTS_DIR, "events_%s.csv" % tid)
    if not os.path.exists(path):
        return {}
    agg = defaultdict(float)
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 5 or row[0] != tid:
                continue  # 双保险：非本租户行直接丢弃
            leg, metric, val = row[2], row[3], row[4]
            try:
                agg[(leg, metric)] += float(val)
            except ValueError:
                pass
    return agg


def region_key(s):
    """把地区字段聚合成「县级」单位，让区域分布图有意义。

    两种常见写法一并处理：
      · 「示例县·某镇某村」→ 先按分隔符取前段 → 再取最具体行政单位 → 「示例县」
      · 「示例市A区」      → 贪婪取到最后一个行政字 → 「示例市A区」（不能吞成「示例市」）
    兜底：无行政后缀时保留原值；整段被吞（>12 字）时退回第一个行政单位。
    """
    s = (s or "").strip()
    if not s:
        return s
    for sep in ("·", "、", "/"):
        if sep in s:
            s = s.split(sep)[0].strip()
            break
    m = re.match(r"^(.*[市县区旗])", s)
    if m:
        r = m.group(1)
        if len(r) > 12:  # 防御：吞掉整句时退回首个行政单位
            m2 = re.match(r"^(.*?[市县区旗])", s)
            r = m2.group(1) if m2 else r
        return r
    m3 = re.match(r"^(.*?[镇乡])", s)
    return (m3.group(1) if m3 else s) or s


def load_staging(path):
    if not path or not os.path.exists(path):
        return [], Counter(), Counter()
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    tiers = Counter((r.get("评分档位") or "").strip() for r in rows)
    regions = Counter(region_key(r.get("地区")) for r in rows)
    return rows, tiers, regions


def load_ledger(tid):
    """只读本租户账本，出 M5 明账汇总 + 明细（双时态）。"""
    path = os.path.join(LEDGER_DIR, "ledger_%s.csv" % tid)
    if not os.path.exists(path):
        return {"leads": 0, "deals": 0, "share": 0.0, "cost": 0.0, "net": 0.0,
                "alerts": 0, "rows": []}
    leads = deals = alerts = 0
    share = cost = 0.0
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if len(r) < 5 or r[0] != tid:
                continue
            kind, amount, customer, note = r[3], r[4], (r[5] if len(r) > 5 else ""), (r[6] if len(r) > 6 else "")
            try:
                amt = float(amount)
            except ValueError:
                amt = 0.0
            rows.append({"date": r[1], "recorded": r[2], "kind": kind,
                         "amount": amt, "customer": customer, "note": note})
            if kind == "线索成本":
                leads += 1
                cost += amt
            elif kind == "成交金额":
                deals += 1
            elif kind == "预估分成":
                share += amt
            elif kind == "防跳单告警":
                alerts += 1
    return {"leads": leads, "deals": deals, "share": share, "cost": cost,
            "net": share - cost, "alerts": alerts, "rows": rows}


def bars(counter, order=None, color="#2f6fed"):
    items = order if order else [k for k, _ in counter.most_common()]
    items = [k for k in items if k]
    maxv = max([counter.get(k, 0) for k in items], default=1) or 1
    out = []
    for k in items:
        v = counter.get(k, 0)
        w = int(round(100.0 * v / maxv)) if maxv else 0
        out.append('<div class="row"><span class="lab">%s</span>'
                   '<span class="track"><span class="fill" style="width:%d%%;background:%s"></span></span>'
                   '<span class="val">%d</span></div>'
                   % (html.escape(str(k)), w, color, v))
    return "".join(out) or '<div class="muted">暂无数据</div>'


def build(tid):
    prof = load_profile(tid)
    ev = load_events(tid)
    rows, tiers, regions = load_staging(prof["staging"])
    led = load_ledger(tid)

    company = html.escape(prof["company"])
    p0 = tiers.get("P0", 0)
    L = []
    L.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
             '<title>%s · Agent 服务看板</title>' % company)
    L.append('''<style>
:root{--bg:#f5f7fa;--card:#fff;--primary:#2f6fed;--text:#1f2933;--muted:#6b7785;--line:#e6ebf2;--warn:#c2410c;}
*{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);}
.hero{background:linear-gradient(135deg,#2f6fed,#1f4fc4);color:#fff;padding:24px 18px;}
.hero h1{margin:0;font-size:20px;} .hero p{margin:6px 0 0;font-size:13px;opacity:.95;}
.wrap{max-width:800px;margin:0 auto;padding:16px;}
section{background:var(--card);border-radius:14px;padding:16px;margin:12px 0;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.sec-h{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:10px;}
.sec-h h2{margin:0;font-size:16px;color:var(--primary);} .sec-h .sub{font-size:12px;color:var(--muted);}
.kpis{display:flex;gap:10px;flex-wrap:wrap;} .kpi{flex:1;min-width:96px;background:#f8fafc;border-radius:10px;padding:12px;text-align:center;}
.kpi .n{font-size:22px;font-weight:800;color:var(--primary);} .kpi .l{font-size:12px;color:var(--muted);margin-top:3px;}
.row{display:flex;align-items:center;margin:6px 0;font-size:13px;}
.row .lab{width:88px;color:var(--text);flex:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.row .track{flex:1;background:var(--line);border-radius:6px;height:14px;margin:0 8px;overflow:hidden;}
.row .fill{display:block;height:100%;border-radius:6px;}
.row .val{width:30px;text-align:right;color:var(--muted);flex:none;}
table{width:100%;border-collapse:collapse;font-size:12.5px;} th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;}
th{color:var(--muted);font-weight:600;} td.num{text-align:right;font-variant-numeric:tabular-nums;}
.flag{background:#fff8ef;border:1px solid #ffe2b8;color:#8a6d1a;border-radius:8px;padding:10px 12px;font-size:12px;margin-top:10px;line-height:1.7;}
.note{font-size:12px;color:var(--muted);margin-top:10px;line-height:1.7;}
.muted{color:var(--muted);font-size:13px;}
.alert{background:#fff1f2;border:1px solid #fecdd3;color:#9f1239;border-radius:8px;padding:10px 12px;font-size:12.5px;margin-top:8px;}
</style></head><body>''')

    # 头部
    L.append('<div class="hero"><h1>%s · Agent 服务看板</h1>'
             '<p>%s · %s · 数据截至 %s</p></div>'
             % (company, html.escape(prof["industry"] or "-"),
                html.escape(prof["region"] or "-"), date.today().isoformat()))
    L.append('<div class="wrap">')

    # 三腿运行
    L.append('<section><div class="sec-h"><h2>一、Agent 三条腿运行状态</h2>'
             '<span class="sub">本期累计</span></div><div class="kpis">')
    for leg, name in LEG_NAMES.items():
        # 取该腿第一个指标作为主数值
        metrics = [(m, v) for (lg, m), v in ev.items() if lg == leg]
        main = metrics[0] if metrics else ("-", 0)
        L.append('<div class="kpi"><div class="n">%s</div><div class="l">%s · %s</div></div>'
                 % (("%g" % main[1]) if isinstance(main[1], float) else main[1],
                    name, html.escape(str(main[0]))))
    L.append('</div></section>')

    # 线索库
    L.append('<section><div class="sec-h"><h2>二、线索库（贵司自有 / 公开脱敏）</h2>'
             '<span class="sub">共 %d 条</span></div><div class="kpis">'
             '<div class="kpi"><div class="n">%d</div><div class="l">线索总数</div></div>'
             '<div class="kpi"><div class="n">%d</div><div class="l">P0 强信号</div></div>'
             '<div class="kpi"><div class="n">%d</div><div class="l">覆盖区域</div></div></div>'
             % (len(rows), len(rows), p0, len([k for k in regions if k])))
    L.append('<div style="margin-top:10px;font-size:13px;font-weight:700;color:var(--primary)">评分档位分布</div>')
    L.append(bars(tiers, order=["P0", "P1", "P2", "P3"]))
    L.append('<div style="margin-top:10px;font-size:13px;font-weight:700;color:var(--primary)">区域分布 Top</div>')
    L.append(bars(regions))

    # 本期线索明细（客户最想看的：到底捞上来哪些厂）
    if rows:
        L.append('<div style="margin-top:14px;font-size:13px;font-weight:700;color:var(--primary)">'
                 '本期线索明细（共 %d 家）</div>' % len(rows))
        L.append('<table style="margin-top:6px"><tr><th>企业名称</th><th>地区</th>'
                 '<th>档位</th><th>需求信号</th><th>公开联系方式</th></tr>')
        for r in rows[:20]:
            L.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                html.escape((r.get("企业名称") or "").strip()),
                html.escape(region_key(r.get("地区"))),
                html.escape((r.get("评分档位") or "").strip()),
                html.escape((r.get("需求信号") or "").strip()[:28]),
                html.escape((r.get("电话") or "").strip()[:22]),
            ))
        L.append('</table>')
        L.append('<div class="note">以上联系方式均为公开渠道（官网 / 黄页 / 公示）取得，'
                 '由贵司自行合规触达。</div>')
    L.append('</section>')

    # 明账
    L.append('<section><div class="sec-h"><h2>三、明账账本（透明结算）</h2>'
             '<span class="sub">红线③：明账 + 防跳单</span></div><div class="kpis">'
             '<div class="kpi"><div class="n">%d</div><div class="l">线索数</div></div>'
             '<div class="kpi"><div class="n">%d</div><div class="l">成交数</div></div>'
             '<div class="kpi"><div class="n">¥%.0f</div><div class="l">预估分成</div></div>'
             '<div class="kpi"><div class="n">¥%.0f</div><div class="l">净收益</div></div></div>'
             % (led["leads"], led["deals"], led["share"], led["net"]))
    if led["rows"]:
        L.append('<table style="margin-top:12px"><tr><th>业务日</th><th>类型</th>'
                 '<th class="num">金额(元)</th><th>对象</th></tr>')
        for r in led["rows"][:12]:
            L.append('<tr><td>%s</td><td>%s</td><td class="num">%.2f</td><td>%s</td></tr>'
                     % (html.escape(r["date"]), html.escape(r["kind"]), r["amount"],
                        html.escape(r["customer"])))
        L.append('</table>')
    else:
        L.append('<div class="muted">暂无账目</div>')

    # 防跳单
    if led["alerts"]:
        L.append('<div class="alert">⚠ 防跳单提醒：本期 %d 笔成交归因非 Agent 渠道（处于 24 个月'
                 '排他期内），已按协议标记并进入核对流程——这是对双方的透明保护。</div>' % led["alerts"])
    else:
        L.append('<div class="note">✓ 本期无跳单嫌疑，成交均经 Agent 留痕渠道。</div>')
    L.append('</section>')

    # 红线声明
    L.append('<section><div class="sec-h"><h2>四、数据主权与边界</h2></div>'
             '<div class="flag">'
             '· <b>数据主权归贵司</b>：本看板全部数据为贵司自有或公开渠道脱敏所得，贵司可随时导出、停用、删除。<br>'
             '· <b>乙方核心资产不出门</b>：服务方的主表 / 评分引擎 / 采集管线不进入贵司系统，也不出现在本看板。<br>'
             '· <b>本看板仅含贵司自身数据</b>：不含任何其他客户的数据，也不含服务方平台运营数据。<br>'
             '· <b>合规</b>：企微仅用官方 API，回复带 AI 标识；短信含签名与退订指令，遵守频控。'
             '</div></section>')

    L.append('<p class="note">本看板由成长型 Agent 平台 · 客户版看板生成器自动产出'
             '（Python 标准库，零依赖，可离线打开）。生成时间 %s</p>'
             % date.today().isoformat())
    L.append('</div></body></html>')
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="客户版看板生成器（单租户视角）")
    ap.add_argument("--tenant", required=True, help="租户ID，如 profile_003")
    ap.add_argument("--out", default="", help="输出 HTML 路径")
    args = ap.parse_args()
    doc = build(args.tenant)
    out = args.out or os.path.join(HERE, "单租户看板_%s_%s.html"
                                   % (args.tenant, date.today().strftime("%Y%m%d")))
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("[完成] 单租户看板已生成：%s（%.1f KB）" % (out, len(doc.encode("utf-8")) / 1024))
    print("      注意：本看板仅含 %s 自身数据，不含其他租户/平台运营数据。" % args.tenant)


if __name__ == "__main__":
    main()
