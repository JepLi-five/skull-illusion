# 骷髅幻戏 · 评分引擎（移植自 priority_engine.py，2026-10-05 子羿拍板版）
# 透明、可调权重、可审计。纯函数，无文件 IO。
# 子羿调参只改下方 WEIGHTS / THRESHOLDS / OUTPROV_*。

WEIGHTS = {
    # P0 热线索三件套
    '强需求': 25, '已接触': 10, '强切换': 25,
    # P1 涂漆信号
    '水性': 20, '油性信号': 20,
    # P2 渠道/网络四件套
    '协会': 5, '展会': 5, '工艺': 5, '网络拓展': 5,
    # 负向
    '弱信号': -10,
}
THRESHOLDS = {'P0': 60, 'P1': 40, 'P2': 20}  # 低于 P2 阈值 => P3
ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}

# 外省降级机制：'penalty' 扣分（推荐）/ 'cap' 封顶 / 'none' 不降级
OUTPROV_MODE = 'penalty'
OUTPROV_CAP = 'P2'
OUTPROV_PENALTY = 15  # 2026-10-08 子羿拍板 -15（区域=减分项非否决项）

import re


def parse_priority(s):
    """P档·标志·重点(判据) -> (tier, tokens, flags)"""
    if not s:
        return ('?', set(), set())
    s = str(s)
    m = re.match(r'^(P[0-3])', s)
    tier = m.group(1) if m else '?'
    toks, flags = set(), set()
    pm = re.search(r'\(([^)]*)\)', s)
    if pm:
        for t in pm.group(1).split('/'):
            t = t.strip()
            if t:
                toks.add(t)
    if '外省降级' in s:
        flags.add('外省降级')
    for f in ('待开发', '中意向', '高意向', '开发'):
        if f in s:
            flags.add(f)
    return (tier, toks, flags)


def score_signals(toks, flags):
    """加权打分 -> (score, tier, contrib)"""
    score = 0
    contrib = []
    for sig in toks:
        if sig in WEIGHTS:
            score += WEIGHTS[sig]
            contrib.append((sig, WEIGHTS[sig]))
    if '外省降级' in flags and OUTPROV_MODE == 'penalty':
        score -= OUTPROV_PENALTY
        contrib.append(('外省降级', -OUTPROV_PENALTY))
    tier = 'P3'
    for t in ('P0', 'P1', 'P2'):
        if score >= THRESHOLDS[t]:
            tier = t
            break
    if '外省降级' in flags and OUTPROV_MODE == 'cap' and ORDER[tier] < ORDER[OUTPROV_CAP]:
        tier = OUTPROV_CAP
    return score, tier, contrib


def score_from_string(priority_str):
    """给获客流水线用：主表优先级字符串 -> 结构化结果"""
    orig_tier, toks, flags = parse_priority(priority_str)
    score, engine_tier, contrib = score_signals(toks, flags)
    return {
        'orig_tier': orig_tier,
        'engine_tier': engine_tier,
        'score': score,
        'contrib': contrib,
        'flags': sorted(flags),
        'signals': sorted(toks),
    }
