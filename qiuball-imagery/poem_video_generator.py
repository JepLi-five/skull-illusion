#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
poem_video_generator.py
诗词歌赋 → 配套动图（含朗诵）生成器 · 球球·心象（生成器内核 v2）

思路（对应「一键生成网文生成器」范式）：
  输入诗词文本 → 按「首/句」拆分成意象单元 → 抽意境锚点(主体/气势/光影/镜头)
  → 映射英文视觉语言 → 输出可直接丢进 VideoGen 的分镜 prompt
  → 甲(精选最炸单镜头) / 乙(全镜头分段) 任选 → 预估积分预算
  → [可选] 朗诵：免费微软 TTS 生成诗词人声，视频生成后 ffmpeg 混音

用法：
  python poem_video_generator.py --poem "..." --mode 乙 --narration
  python poem_video_generator.py --file 诗词.txt --mode 甲
  python poem_video_generator.py --interactive

输出：
  - 控制台打印分镜 prompt + 预算
  - 导出 prompts_时间戳.md（交给视频生成工具 / 球球接手）
  - [--narration] 导出 narration_时间戳.mp3（免费 TTS 朗诵）

注：本脚本产出 prompt + 朗诵音频；视频画面由 VideoGen（球球接手）生成，乙模式用 ffmpeg concat copy 拼接，朗诵用 ffmpeg 混音。TTS 免费，不耗积分。
"""
import argparse, os, re, sys
from datetime import datetime

# ---------- 意境锚点 → 英文视觉语言映射 ----------
# 键=中文意象字；值=(主体片段, 气势/动作, 光影, 推荐镜头)
VISION = {
    "山": ("a towering mountain peak", "majestic and immovable", "epic cinematic light", "low-angle heroic shot"),
    "峰": ("a jagged mountain peak", "razor-edged", "golden dawn light", "low-angle heroic shot"),
    "岭": ("rolling mountain ranges", "vast and endless", "soft horizon light", "wide establishing shot"),
    "马": ("a galloping horse", "breakneck speed", "wind-torn mist", "dynamic tracking shot"),
    "骑": ("a lone rider on horseback", "spurring forward", "wind-torn mist", "dynamic tracking shot"),
    "天": ("the looming azure sky", "vast heavens", "divine light rays", "upward tilt"),
    "云": ("a churning sea of clouds", "roiling", "soft glow", "wide shot"),
    "风": ("howling wind", "tearing through", "dramatic storm light", "whip-pan"),
    "浪": ("raging ocean waves", "surging", "foam and spray", "low wide shot"),
    "江": ("a torrential river", "rushing", "cold reflection", "follow shot"),
    "河": ("a rushing river", "torrential", "cold sheen", "follow shot"),
    "海": ("a boundless ocean", "endless", "horizon light", "wide shot"),
    "剑": ("a giant unsheathed sword", "sharp and unbroken", "metallic gleam", "heroic low-angle"),
    "刺": ("stabbing upward", "piercing the sky", "sharp light contrast", "low-angle thrust"),
    "战": ("a fierce battle", "chaotic energy", "dramatic firelight", "chaotic wide shot"),
    "万": ("thousands of", "countless", "epic scale", "massive wide shot"),
    "月": ("a luminous full moon", "serene", "cool silver glow", "slow push-in"),
    "雪": ("falling snow", "quiet blanket", "soft blue light", "slow aerial"),
    "花": ("bursting blossoms", "delicate", "warm petal light", "macro drift"),
    "水": ("flowing water", "gentle current", "reflective sheen", "top-down glide"),
    "星": ("scattered stars", "twinkling", "night glow", "slow tilt"),
    "龙": ("a coiled dragon", "majestic", "bioluminescent scales", "orbiting shot"),
    "松": ("an ancient pine", "weathered", "dappled light", "low angle"),
    "鹤": ("a flying crane", "graceful", "soft dawn light", "slow follow"),
}

# 视觉冲击加权（用于甲模式选最炸镜头）
IMPACT = {"剑": 3, "刺": 3, "战": 3, "天": 2, "万": 2, "峰": 2, "浪": 2, "龙": 2, "海": 1, "雪": 1, "月": 1}

# 每段视频最低/最高积分（5 秒）；朗诵 TTS 免费
COST_MIN, COST_MAX = 50, 100


def split_units(poem):
    """多行按首拆；单行按句拆。返回意象单元列表。"""
    if "\n" in poem:
        units = [u.strip() for u in poem.split("\n") if u.strip()]
    else:
        units = [u.strip() for u in re.split(r"[。；;！!？?]", poem) if u.strip()]
    return units


def translate_unit(unit):
    subj, mood, light, shot = [], [], [], []
    matched = False
    for ch, val in VISION.items():
        if ch in unit:
            matched = True
            subj.append(val[0]); mood.append(val[1]); light.append(val[2]); shot.append(val[3])
    if not matched:
        return None
    subject = ", ".join(dict.fromkeys(subj))
    atmosphere = ", ".join(dict.fromkeys(mood))
    lighting = ", ".join(dict.fromkeys(light))
    camera = shot[0]
    return f"{subject}, {atmosphere}, {lighting}, {camera}, cinematic 8k, hyper-detailed"


def score_unit(unit):
    return sum(IMPACT.get(ch, 0) for ch in unit if ch in IMPACT)


def generate_narration(text, voice, out_path):
    """调用免费微软 TTS 生成朗诵音频。返回路径或 None。"""
    try:
        import asyncio, edge_tts
    except ImportError:
        print("⚠ 未安装 edge-tts：请先 `pip install edge-tts`（免费微软中文语音）")
        return None
    async def _run():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(out_path)
    asyncio.run(_run())
    return out_path


def main():
    ap = argparse.ArgumentParser(description="诗词 → 配套动图(含朗诵) prompt 生成器")
    ap.add_argument("--poem", help="诗词文本（多行则按首拆）")
    ap.add_argument("--file", help="诗词文件（utf-8）")
    ap.add_argument("--mode", choices=["甲", "乙"], default="乙")
    ap.add_argument("--narration", action="store_true", help="生成诗词朗诵音频(免费TTS)")
    ap.add_argument("--voice", default="zh-CN-YunxiNeural", help="朗诵音色，默认云希男声")
    args = ap.parse_args()

    poem = args.poem
    if not poem and args.file:
        with open(args.file, encoding="utf-8") as f:
            poem = f.read()
    if not poem:
        poem = input("粘贴诗词文本（多行按首拆）：")
    if not poem.strip():
        print("无输入，退出"); sys.exit(1)

    units = split_units(poem)
    shots = []
    for u in units:
        p = translate_unit(u)
        if p:
            shots.append((u, p, score_unit(u)))

    if not shots:
        print("⚠ 未能识别意象，请补充 VISION 词典或手动提供 prompt。")
        sys.exit(1)

    if args.mode == "甲":
        best = max(shots, key=lambda x: x[2])
        selected = [best]
        cost = f"{COST_MIN}-{COST_MAX} 积分（单镜头 5 秒）"
    else:
        selected = shots
        n = len(selected)
        cost = f"{COST_MIN*n}-{COST_MAX*n} 积分（{n} 段 ×5 秒）"
    narr_cost = "0 积分（免费 TTS）" if args.narration else "未生成"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_md = f"prompts_{ts}.md"
    lines = [f"# 诗词动图 Prompt（{args.mode} 模式）", "",
             f"> 原词：{poem[:50]}{'...' if len(poem) > 50 else ''}",
             f"> 预估预算：视频 {cost} ｜ 朗诵 {narr_cost}", ""]
    for idx, (u, p, sc) in enumerate(selected, 1):
        lines += [f"## 镜头 {idx}（原句：{u}）", "", "```", p, "```", ""]
    if args.mode == "乙":
        lines += ["## 合成说明",
                  f"将以上 {len(selected)} 段各 5 秒视频按镜头顺序拼接为 {len(selected)*5} 秒成片"
                  "（ffmpeg -f concat -c copy）。", ""]
    if args.narration:
        lines += ["## 朗诵混音",
                  f"朗诵音频 narration_{ts}.mp3 由免费 TTS 生成；视频生成后执行：",
                  f"ffmpeg -i 视频.mp4 -i narration_{ts}.mp3 -c:v copy -c:a aac -map 0:v -map 1:a -shortest 输出.mp4", ""]
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"模式：{args.mode} | 识别镜头：{len(selected)} | 视频预算：{cost} | 朗诵：{narr_cost}")
    print("-" * 60)
    for idx, (u, p, sc) in enumerate(selected, 1):
        print(f"[{idx}] {u}\n    {p}")
    print("-" * 60)
    print(f"已导出：{out_md}")
    if args.narration:
        rp = generate_narration(poem, args.voice, f"narration_{ts}.mp3")
        if rp:
            print(f"朗诵音频：{rp}")
            print(f"混音：视频生成后执行 ffmpeg -i 视频.mp4 -i {rp} -c:v copy -c:a aac -map 0:v -map 1:a -shortest 输出.mp4")
    print("下一步：将各镜头 prompt 交给 VideoGen（球球接手）生成视频；乙模式用 ffmpeg 拼接；朗诵用 ffmpeg 混音。")


if __name__ == "__main__":
    main()
