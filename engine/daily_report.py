# 骷髅幻戏 · 每日复盘 / 提醒（P2 配套）
# 输出纯文本日报：逾期清单 + 3天内到期 + 四部门在办 + P0未动。
# 供每日自动化调用（stdout 直接可推送/存档），不依赖任何外部服务。
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import STAGE_CN, STAGES, digest, due_soon, overdue  # noqa: E402


def render(days=3):
    d = digest()
    od = overdue()
    ds = due_soon(days)
    lines = []
    lines.append(f"【骷髅幻戏 · 每日复盘】{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("■ 四部门在办")
    for s in STAGES:
        lines.append(f"  {STAGE_CN[s]}({s}): {d['stages'][s]}")
    lines.append(f"  线索总数 {d['total_leads']} | P0未动 {d['p0_open']} | 逾期 {d['overdue']}")
    lines.append("")
    lines.append(f"■ 已逾期（{len(od)}）")
    if od:
        for r in od:
            lines.append(f"  [{STAGE_CN.get(r[0], r[0])}] #{r[1]} {r[2]} 档={r[3]} 到期={r[4]}")
            if r[5]:
                lines.append(f"      备注: {r[5]}")
    else:
        lines.append("  （无）")
    lines.append("")
    lines.append(f"■ {days} 天内到期（{len(ds)}）")
    if ds:
        for r in ds:
            lines.append(f"  [{STAGE_CN.get(r[0], r[0])}] #{r[1]} {r[2]} 档={r[3]} 到期={r[4]}")
    else:
        lines.append("  （无）")
    return "\n".join(lines)


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(render(days))
