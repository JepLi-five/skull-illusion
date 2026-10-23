# 诗词动图 Prompt · 毛泽东《十六字令三首》· 球球·心象 生成

> 阶段：C 验证（手动跑通样例）。prompt 先以文本就位，待子羿点头生成动图验证后，固化进「诗词歌赋配套动图生成器」脚本。
> 转换逻辑（生成器核心算法）：诗词 → 动图不是直译，是「抽意境锚点 → 配视觉语言」。
> 四要素：① 主体（山+动态元素）② 气势（险/阔/刚）③ 光影（苍茫/金/青）④ 镜头（仰拍/俯瞰/推近）。

## 原词（三首皆以「山」起头）
- 其一：山，快马加鞭未下鞍。惊回首，离天三尺三。
- 其二：山，倒海翻江卷巨澜。奔腾急，万马战犹酣。
- 其三：山，刺破青天锷未残。天欲堕，赖以拄其间。

## 镜头 1 —— 其一·险峰疾马（离天三尺三）
**英文 prompt（直接丢 VideoGen）：**
```
A towering jagged mountain peak piercing a sea of clouds just beneath the heavens, a lone red-cloaked rider spurring a horse at breakneck speed along a narrow cliff path, dizzying vertical perspective looking up, wind tearing through mist, epic cinematic, golden dawn light, 8k, hyper-detailed
```
**中文锚点**：主体=险峰+红衣骑者；气势=险绝；光影=破晓金光；镜头=仰拍近天。

## 镜头 2 —— 其二·群山如澜（万马战犹酣）
**英文 prompt（直接丢 VideoGen）：**
```
Vast rolling mountain ranges surging like enormous ocean waves and raging rivers, thousands of galloping horses charge through the valleys as if in fierce battle, dynamic wide shot, dramatic storm light, dust and motion blur, cinematic epic scale, 8k
```
**中文锚点**：主体=群山+万马；气势=磅礴如战场；光影=风暴戏剧光；镜头=大全景俯瞰。

## 镜头 3 —— 其三·刺天擎柱（刺破青天锷未残）
**英文 prompt（直接丢 VideoGen）：**
```
A colossal mountain peak shaped like a giant unsheathed sword stabbing through the azure sky, its blade edge sharp and unbroken, the crumbling heavens leaning yet held up by the mountain as a pillar, low-angle heroic shot, divine golden light rays, apocalyptic yet majestic, cinematic 8k, hyper-detailed
```
**中文锚点**：主体=如剑山峰+将倾苍穹；气势=刚毅擎天；光影=神性金光；镜头=低角度英雄镜头。

## 合成建议
- 方案甲（镇楼）：单取镜头 3 出 5 秒，最有视觉冲击，烧分最少。
- 方案乙（完整）：三段各 5 秒合成 15 秒短视频，完整呈现三首意境递进（险→阔→刚）。

## 状态
[C 验证阶段] 三镜头 prompt 已就位，待子羿点头生成动图验证。

---
*本转译文档由「球球·心象」生成 · 原文经公版底本核验*
