# ffmpeg filter graph 逐段图解

需要手工改图（加滤镜、改动画曲线、换叠加方式）时读此文件。
以下以黑底模式、1080×1920、画面带 1080×608 为例；实际表达式由
`burst_effect.py` 按参数生成，运行时会打印完整命令。

## 输入

| 输入 | 内容 | 规格 |
|---|---|---|
| `-i norm.mkv`（input 0） | 归一化底片 | 1080×608，30fps，ffv1（含可选音频） |
| `-i mask.mkv`（input 1） | 灰度抠像 | 1080×608，gray，ffv1 |

## 黑底模式 graph

```
color=c=black:s=1080x1920:r=30:d=<时长>[base];
[0:v]setpts=PTS-STARTPTS,split=2[foot][foot3];
[1:v]format=gray,setpts=PTS-STARTPTS[alpha];
[foot][alpha]alphamerge,format=rgba[fg0];
[fg0]scale=w='iw*(s表达式)':h='ih*(s表达式)':eval=frame:flags=bilinear[fg];
[base][foot3]overlay=0:656:eval=init[stage];
[stage][fg]overlay=x='round(1080/2-(s表达式)*0.5*1080)':
               y='round(1920/2-(s表达式)*0.5*608)':
               eval=frame:eof_action=pass[outv]
```

### 各段作用

1. **`color [base]`**：纯黑竖屏画布；`d=时长` 保证 color 源不过早结束。
2. **`setpts + split`**：时间戳归零（保证动画 t 从 0 起算）；
   `foot` 给抠像层，`foot3` 给画面带叠加。
   blur 模式多一路 `foot2` 做模糊底（split=3）。
3. **`alphamerge`**：把灰度 mask 作为 alpha 通道贴到画面上 → RGBA 前景。
4. **`scale eval=frame`**：每帧按 `s(t)` 表达式缩放（动画核心）。
5. **`[base][foot3]overlay=0:656`**：画面带垂直居中。
   居中 y = (1920−608)/2 = 656。
6. **前景 overlay 锚点公式**：锚点（默认画面带中心）在缩放中保持不动：
   ```
   x = CW/2 − s·ax·W
   y = CH/2 − s·ay·H
   ```
   `round()` 防止非整数位置帧间抖动。

## blur 模式差异

把第 1、5 段替换为：

```
[foot2]scale=1080:1920:force_original_aspect_ratio=increase,
       crop=1080:1920,gblur=sigma=28,
       eq=brightness=-0.15:saturation=1.1[bgb];
[bgb][foot3]overlay=0:656:eval=init[stage];
```

即：原画面 cover 填充竖屏 → 高斯模糊 28 → 压暗 15%，再在其上叠清晰画面带。

## 缩放表达式 s(t)

线性（默认）：

```
s(t) = 1 + (S−1)·clip( (t−t0)/(t1−t0), 0, 1 )
```

- `t < t0`：s=1，前景与画面带严格重合（无缝是效果成立的前提）；
- `t0→t1`：线性增长到 S；
- `t > t1`：s=S 保持。

缓入缓出（`--ease smooth`）把 `clip(...)` 记作 y，乘上 `y·y·(3−2y)`（smoothstep）。

## 手工改图常用方向

| 想做的事 | 改哪里 |
|---|---|
| 放大同时带一点旋转 | scale 后接 `rotate='0.05*(s-1)':fillcolor=none:overlay` |
| 主体投影 | 前景 scale 后再取一条 alpha→gblur→黑色填充层，叠在 fg 之下（黑底上不需要） |
| 背景画面带也轻微推近 | `[foot3]scale=w=iw*(1+0.1*...)...`（会破坏带内无缝，慎用） |
| 冲出瞬间加闪白 | 在 stage 与 fg 之间按 `(s-1)` 峰值加 `color=white` 短时 overlay |
| 改画幅为 4:5 封面 | 调 `--canvas` 与画面带高度即可，表达式自动适配 |

注意：任何改动都要保证每个 split pad 恰好被消费一次（见 lessons.md L5）。
