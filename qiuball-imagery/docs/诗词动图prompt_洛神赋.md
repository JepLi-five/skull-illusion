# 诗词动图 Prompt · 曹植《洛神赋》（节选）· 球球·心象 生成

> 阶段：实战验证（洛神赋）。转换逻辑 = 抽意境锚点 → 配视觉语言（同生成器内核 `poem_video_generator.py`）。
> 洛神赋为抒情小赋，意象柔美（鸿/龙/云/月/波/神），不走「山/马/剑」式刚健字典，故采用**人工意境锚点转译**——即生成器内核的「难译文本兜底分支」。
> 四要素：① 主体（洛神 + 洛水烟波）② 气质（惊鸿游龙之柔逸）③ 光影（朝霞金 / 玉波银）④ 镜头（推近 / 横移 / 拉远）。

## 原赋节选（叙事弧：出场 → 行步 → 离别）
- **出场**：翩若惊鸿，婉若游龙。髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。远而望之，皎若太阳升朝霞；迫而察之，灼若芙蕖出渌波。
- **行步**：凌波微步，罗袜生尘。动无常则，若危若安。进止难期，若往若还。
- **离别**：忽不悟其所舍，怅神宵而蔽光。

## 镜头 1 —— 出场·惊鸿游龙（薄暮洛水现身）
**英文 prompt（直接丢 VideoGen）：**
```
An ethereal goddess of the Luo River materializing from shimmering mist above tranquil water at dawn, her form graceful as a startled swan and sinuous as a wandering dragon, light gauze robes drifting like clouds veiling the moon, soft pink-and-gold morning light, slow cinematic push-in, dreamy and majestic, 8k, hyper-detailed
```
**中文锚点**：主体=洛神+洛水晨雾；气质=惊鸿游龙之柔逸；光影=朝霞粉金；镜头=缓慢推近。

## 镜头 2 —— 行步·凌波微步（水面轻盈行走）
**英文 prompt（直接丢 VideoGen）：**
```
The Luo River goddess stepping lightly across the water's surface, slender feet leaving faint trails of mist like dust above the ripples, flowing robes, shimmering reflection below, serene wide shot, cool jade-and-silver light, gentle camera glide, elegant and weightless, 8k, hyper-detailed
```
**中文锚点**：主体=洛神+水面微步+罗袜生尘；气质=轻盈若危若安；光影=玉波银辉；镜头=横移跟拍。

## 镜头 3 —— 离别·怅然回顾（神女隐入朝霞）
**英文 prompt（直接丢 VideoGen）：**
```
The Luo River goddess fading into luminous morning haze as she departs, looking back with melancholy grace, a lone mortal poet standing on the riverbank gazing after her, longing and loss in the air, soft golden farewell light, slow pull-back, poignant and cinematic, 8k, hyper-detailed
```
**中文锚点**：主体=洛神隐去+岸上怅望的诗人；气质=怅然若失、神光蔽失；光影=告别金光；镜头=缓慢拉远。

## 朗诵选段（云希男声 · 约 48 字 · 匹配 15 秒成片）
> 翩若惊鸿，婉若游龙。髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。凌波微步，罗袜生尘。

## 预算
- 乙模式 3 镜头 ×5 秒 = 15 秒成片：约 **150–300 积分**
- 朗诵 TTS：0 积分（免费微软云希男声）
- 合计视频约 150–300 积分（已提前告知）

## 合成命令（视频生成后，球球接手）
1. 拼接三段（流式 copy 零损）：
```
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy 洛神赋_乙_合成15秒.mp4
```
2. 混朗诵：
```
ffmpeg -i 洛神赋_乙_合成15秒.mp4 -i narration_洛神赋.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest 洛神赋_乙_朗诵版.mp4
```

## 状态
[实战验证] 三镜头 prompt + 朗诵选段已就位，待球球接手生成视频并混音。

---
*本转译文档由「球球·心象」生成 · 洛神赋离别原句经返照补强修正（原误记"于是背下陵高…顾望怀愁"，正为"忽不悟其所舍，怅神宵而蔽光"）· 原文经公版底本核验*
