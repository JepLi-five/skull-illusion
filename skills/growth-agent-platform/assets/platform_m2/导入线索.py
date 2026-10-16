#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入线索 —— 把任意格式的名单（Excel / CSV / TXT）转成平台标准线索格式。

解决的痛点：各家名单的列名五花八门（公司名称 / 厂名 / 单位名称 / 老板 / 手机号 / 地址…），
平台后续脚本只认标准 11 列。本脚本做三件事：

  1) 导入：自动识别列名并映射到标准字段；**认不出的列一律保留**，统一收进「备注」，信息不丢。
  2) 累积：多次导入可追加进同一个线索库（按企业名称去重，重复不计数）。
  3) 检索：按关键词（企业名称 / 地区 / 行业 / 需求信号 / 评分档位 / 备注）模糊筛选。

用法：
    python 导入线索.py --input "D:/名单.xlsx"
    python 导入线索.py --input "名单.csv" --add
    python 导入线索.py --input "名单.xlsx" --keyword "铸造,示例市"
    python 导入线索.py --input "名单.xlsx" --out "本批线索.csv" --dashboard

与平台其他组件的关系：
    · 本脚本产出的线索库是「客户自有数据」，行数不受限（红线②约束的是**乙方主表**不得进平台包）。
    · 若要用 `onboard_client.py` 把某客户接入多租户平台做**演示**，需另取 ≤10 行脱敏样例——
      那是我方的样例闸门，与客户自己的名单库无关。

依赖：仅 Python 3 标准库（读 .xlsx 亦无需 openpyxl）。
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

FIELDS = ["序号", "企业名称", "地区", "行业", "需求信号", "规模参考",
          "联系人", "电话", "来源", "评分档位", "备注"]

# 标准列 -> 常见别名（归一化后匹配：去空白 / 符号 / 大小写）
ALIASES = {
    "企业名称": ["企业名称", "公司名称", "单位名称", "客户名称", "客户名单", "客户",
                 "厂名", "工厂名称", "商家名称", "公司", "企业", "名称", "name", "company"],
    "地区": ["地区", "地址", "所在地", "所在地区", "城市", "区县", "省市区", "行政区划",
             "所属区域", "区域", "位置", "region", "address", "city"],
    "联系人": ["联系人", "联系人姓名", "负责人", "法人", "法定代表人", "老板", "经理",
               "对接人", "姓名", "contact", "owner"],
    "电话": ["电话", "联系电话", "手机", "手机号码", "手机号", "座机", "联系方式",
             "电话号", "tel", "phone", "mobile"],
    "行业": ["行业", "所属行业", "行业类别", "行业类型", "从事行业", "industry"],
    "需求信号": ["需求信号", "需求", "采购意向", "购买意向", "主营产品", "产品",
                 "工艺", "经营范围", "需求描述", "signal"],
    "规模参考": ["规模参考", "规模", "企业规模", "注册资本", "注册资金", "员工人数",
                 "参保人数", "营业额", "年产值", "人数", "scale"],
    "来源": ["来源", "数据来源", "渠道", "渠道来源", "线索来源", "source"],
    "评分档位": ["评分档位", "评分", "档位", "等级", "评级", "意向等级", "客户等级",
                 "优先级", "tier", "grade"],
    "备注": ["备注", "说明", "备注说明", "其他", "comment", "note", "remark"],
}

TIER_RANK = {"P0": 3, "P1": 2, "P2": 1}


# ---------- 基础工具 ----------

def norm(s):
    """归一化列名：去空白与各种符号，转小写。"""
    return re.sub(r"[\s\-_（）()【】\[\]{}:：、/\\.,，。·'\"#*+]", "", str(s or "")).lower()


def detect_encoding(path):
    for enc in ("utf-8-sig", "gbk", "utf-8", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8"


def read_xlsx(path):
    """零依赖读 Excel（xlsx 本质是 zip+xml），返回二维列表。"""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    def col_idx(ref):
        s = ""
        for ch in ref:
            if ch.isdigit():
                break
            s += ch
        n = 0
        for ch in s:
            n = n * 26 + (ord(ch.upper()) - 64)
        return n - 1

    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(ns + "si"):
            shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in root.iter(ns + "row"):
        cells = {}
        for c in row.findall(ns + "c"):
            ref, t = c.get("r"), c.get("t")
            v, isel = c.find(ns + "v"), c.find(ns + "is")
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif isel is not None:
                val = "".join(x.text or "" for x in isel.iter(ns + "t"))
            elif v is not None:
                val = v.text
            else:
                val = ""
            cells[col_idx(ref)] = (val or "").strip()
        if cells and any(cells.values()):
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
    out = []
    for r in rows:
        while r and r[-1] == "":
            r = r[:-1]
        out.append(r)
    return out


def read_table(path):
    """读 Excel / CSV，返回表头列表 + 字典行列表。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        rows = read_xlsx(path)
        if not rows:
            return [], []
        # 跳过文档标题行：真正的表头 = 第一个「非空单元格 ≥2 个」的行
        hidx = 0
        for i, r in enumerate(rows):
            if sum(1 for x in r if str(x).strip()) >= 2:
                hidx = i
                break
        header = [str(x).strip() for x in rows[hidx]]
        body = rows[hidx + 1:]
        width = len(header)
        data = []
        for r in body:
            r = (list(r) + [""] * width)[:width]
            data.append({header[i]: r[i] for i in range(width)})
        return header, data
    enc = detect_encoding(path)
    with open(path, encoding=enc, newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        rows = []
        for r in reader:
            rows.append({(k or "").strip(): (v or "").strip()
                         for k, v in r.items() if k is not None})
        header = [h for h in (reader.fieldnames or []) if h]
        return header, [r for r in rows if any(r.values())]


def build_map(header):
    """列名 -> 标准列 的映射（优先精确，再子串）。"""
    mapping, used = {}, set()
    lowered = {h: norm(h) for h in header}
    for std, names in ALIASES.items():
        for h in header:
            if h in used:
                continue
            if lowered[h] in [norm(n) for n in names]:
                mapping[std] = h
                used.add(h)
                break
    for std, names in ALIASES.items():
        if std in mapping:
            continue
        for h in header:
            if h in used:
                continue
            lh = lowered[h]
            if any(norm(n) in lh or lh in norm(n) for n in names if norm(n)):
                mapping[std] = h
                used.add(h)
                break
    return mapping


def convert(data, mapping, header):
    """转成标准 11 列；认不出的列收进备注，保证信息不丢。"""
    rest = [h for h in header if h not in set(mapping.values())]
    out = []
    for r in data:
        row = {k: (r.get(mapping.get(k, ""), "") or "").strip() for k in FIELDS if k != "备注"}
        old = (r.get(mapping.get("备注", ""), "") or "").strip()
        extra = ["%s:%s" % (h, (r.get(h, "") or "").strip())
                 for h in rest if (r.get(h, "") or "").strip()]
        row["备注"] = "；".join(([old] if old else []) + extra)
        if row.get("企业名称"):
            out.append(row)
    return out


def load_existing(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding=detect_encoding(path), newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def save(rows, path):
    rows = sorted(rows, key=lambda r: -TIER_RANK.get((r.get("评分档位") or "").strip().upper(), 0))
    for i, r in enumerate(rows, 1):
        r["序号"] = str(i)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


SEARCH_HINT = "说明：检索范围＝企业名称 / 地区 / 行业 / 需求信号 / 评分档位 / 备注"


def search(rows, keywords):
    """按关键词模糊筛选；任一关键词命中即保留（或的关系）。"""
    kws = [k.strip() for k in re.split(r"[,，\s]+", keywords or "") if k.strip()]
    if not kws:
        return rows
    res = []
    for r in rows:
        hay = " ".join([r.get("企业名称", ""), r.get("地区", ""), r.get("行业", ""),
                        r.get("需求信号", ""), r.get("评分档位", ""), r.get("备注", "")])
        if any(k.lower() in hay.lower() for k in kws):
            res.append(r)
    return res


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description="导入线索：任意名单 → 平台标准格式（含检索与追加去重）")
    ap.add_argument("--input", required=True, help="名单文件（.xlsx / .csv / .txt）")
    ap.add_argument("--out", default="我的线索库.csv", help="输出 CSV（默认 我的线索库.csv）")
    ap.add_argument("--add", action="store_true", help="追加进已有线索库（按企业名称去重）")
    ap.add_argument("--keyword", default="", help="检索关键词，逗号分隔，如：铸造,示例市")
    ap.add_argument("--dashboard", action="store_true", help="导入后顺带生成看板 HTML")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print("[出错] 找不到文件：%s" % args.input)
        print("      小技巧：把文件直接拖进命令行窗口，会自动带出路径。")
        sys.exit(1)

    header, data = read_table(args.input)
    if not data:
        print("[出错] 没读到有效数据（空表？还是只有一行表头？）")
        sys.exit(1)

    mapping = build_map(header)
    print("[1/4] 读到 %d 行；识别到 %d 个字段：" % (len(data), len(mapping)))
    for std in FIELDS:
        if mapping.get(std):
            print("      %s ← %s" % (std, mapping[std]))
    if "企业名称" not in mapping:
        print("[出错] 没认出「企业名称」列——确认表里有一列是公司/客户名称。")
        print("      现有列名：%s" % "、".join(header[:12]))
        sys.exit(1)

    new_rows = convert(data, mapping, header)
    print("[2/4] 转换完成 %d 条有效线索。" % len(new_rows))

    if args.keyword:
        new_rows = search(new_rows, args.keyword)
        print("[3/4] 按关键词「%s」筛出 %d 条。%s" % (args.keyword, len(new_rows), SEARCH_HINT))
    else:
        print("[3/4] 未指定关键词，保留全部。")

    if args.add:
        old = load_existing(args.out)
        seen = {r.get("企业名称", "") for r in old}
        merged = old + [r for r in new_rows if r.get("企业名称") not in seen]
        n = save(merged, args.out)
        print("[4/4] 已追加 → %s（原 %d 条，现共 %d 条，重复已跳过）" % (args.out, len(old), n))
    else:
        out = args.out if os.path.isabs(args.out) else os.path.join(os.getcwd(), args.out)
        n = save(new_rows, out)
        print("[4/4] 已保存 → %s（共 %d 条）" % (out, n))

    if not any(r.get("评分档位") for r in new_rows):
        print("      ⓘ 原表无评分列，档位留空；可在 CSV 填 P0/P1/P2/P3 后重出看板。")

    if args.dashboard:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "线索看板.py")
        if os.path.exists(script):
            html_out = os.path.join(os.getcwd(), "线索看板_%s.html" % date.today().strftime("%Y%m%d"))
            subprocess.run([sys.executable, script, args.out, html_out], check=False)
            print("      看板已生成：%s" % html_out)
        else:
            print("      ⓘ 未找到 线索看板.py，跳过看板生成。")

    print("\n下一步：python 周报脚本.py %s" % args.out)


if __name__ == "__main__":
    main()
