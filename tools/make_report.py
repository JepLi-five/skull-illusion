#!/usr/bin/env python3
"""make_report: 通用 CSV -> Markdown 报表生成器（零依赖）。

把任意 CSV 转成可读的 Markdown 表格。示例数据均为占位，
不含任何真实业务信息。可独立运行：

    python make_report.py <input.csv> [标题]
"""
import csv
import sys


def make_report(csv_path: str, title: str = "报表") -> str:
    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return f"# {title}\n\n（空文件）"
        rows = [r for r in reader if any(c.strip() for c in r)]
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in rows:
        # 防止单元格里出现 | 破坏表格
        cells = [c.replace("|", "\\|") for c in r]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python make_report.py <input.csv> [标题]")
        return 1
    title = sys.argv[2] if len(sys.argv) > 2 else "报表"
    print(make_report(sys.argv[1], title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
