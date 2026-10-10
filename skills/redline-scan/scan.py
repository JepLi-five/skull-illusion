#!/usr/bin/env python3
"""redline-scan: 扫描文本/文件中的潜在敏感信息（红线扫描器）。

设计原则：
- 不输出命中内容，只报告位置、类型与脱敏摘要（掩码）。
- 零依赖：仅用标准库 re / os / sys。
- 干净：不含任何真实业务数据；匹配模式为通用正则。

用法: python scan.py <path> [--json]
"""
import re
import sys
import os

# 通用敏感信息模式（示例均为占位，不含真实数据）
PATTERNS = {
    "手机号": re.compile(r"(?:\+?86)?1[3-9]\d{9}"),
    "身份证": re.compile(r"\b\d{17}[\dXx]\b"),
    "邮箱": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "APIKey": re.compile(r"(?:sk|api|token|key)[-_][0-9A-Za-z]{16,}"),
    "密码行": re.compile(r"(?:password|passwd|secret)[\s:=]+[^\s]+", re.I),
    "金额": re.compile(r"\d{2,}(?:\.\d+)?\s*(?:万元|万|元|RMB|￥)"),
}


def mask(s: str) -> str:
    s = s.strip()
    if len(s) <= 4:
        return "****"
    return s[:2] + "****" + s[-2:]


def scan_text(text: str):
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for name, pat in PATTERNS.items():
            for m in pat.finditer(line):
                hits.append((line_no, name, mask(m.group(0))))
    return hits


def scan_path(path: str):
    results = {}
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in files:
                if f.endswith((".md", ".txt", ".py", ".json", ".csv", ".yaml", ".yml")):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, encoding="utf-8", errors="ignore") as fh:
                            h = scan_text(fh.read())
                            if h:
                                results[fp] = h
                    except Exception:
                        pass
    else:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            h = scan_text(fh.read())
            if h:
                results[path] = h
    return results


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scan.py <path> [--json]")
        return 1
    path = sys.argv[1]
    as_json = "--json" in sys.argv
    res = scan_path(path)
    if as_json:
        import json
        print(json.dumps(res, ensure_ascii=False))
    else:
        if not res:
            print("CLEAN: 未发现高危敏感信息")
        for fp, hits in res.items():
            print(f"== {fp} ==")
            for ln, name, masked in hits:
                print(f"  L{ln}  {name}  {masked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
