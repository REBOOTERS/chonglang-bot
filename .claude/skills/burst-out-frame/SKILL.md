---
name: burst-out-frame
description: 用本地 ffmpeg + rembg 复刻「人物/主体冲出画面」裸眼 3D 视频效果（画面带中主体与背景无缝，关键帧放大冲出画面边缘）。当用户要求"冲出画面、裸眼3D、主体弹出画面、3D 运镜封面、人物穿出屏幕、复刻 lesson 视频效果"时使用。横屏源保持横屏（1920x1080）、竖屏源出竖屏，默认模糊填充（不用黑边），自动 AI 抠像、主体跨帧跟踪防止目标丢失，并保留原音频。
---

# 人物冲出画面（裸眼 3D pop-out）Skill

复刻剪映教程类视频「人物如何冲出画面」的效果：竖屏画布中央是一条 16:9 画面带，
主体在带内时与背景完全重合，随后沿关键帧放大，**冲破画面带边缘进入黑色/模糊区域**，
形成主体穿出屏幕的裸眼 3D 观感。

## 0. 执行前必读

1. 读 `lessons.md` —— 历史踩坑记录（Python 商店占位符、模型下载慢、抠像翻转、竖屏裁切），**先避开已知坑**。
2. 环境自检（见下）。缺什么补什么，不要在错误环境里反复跑。

### 环境自检

| 依赖 | 检查 | 缺失时 |
|---|---|---|
| ffmpeg / ffprobe | `ffmpeg -version`（需 6.x+，本脚本只用内置 filter） | 提示用户安装 |
| Python venv | 项目目录 `.venv/Scripts/python.exe`（Windows） | `uv venv` 创建 |
| rembg 等 | `.venv/Scripts/python.exe -c "import rembg"` | `uv pip install rembg pillow numpy scipy onnxruntime` |
| 抠像模型 | `~/.u2net/isnet-general-use.onnx` | 用 `scripts/fetch_model.py isnet-general-use` 镜像下载 |

模型从 GitHub release 分发，国内直连实测仅 21KB/s；`fetch_model.py` 会依次尝试
gh-proxy.com 等镜像（实测 2.9MB/s）。birefnet 类模型走 HuggingFace，
需设 `HF_ENDPOINT=https://hf-mirror.com`。

## 1. 一条命令用法

竖屏源（输出 1080×1920）：

```bash
.venv/Scripts/python.exe <skill目录>/scripts/burst_effect.py INPUT.mp4 -o OUTPUT.mp4 --bg blur
```

**横屏源（必须保持横屏，不得改成竖屏）：**

```bash
.venv/Scripts/python.exe <skill目录>/scripts/burst_effect.py INPUT.mp4 -o OUTPUT.mp4 \
  --canvas 1920x1080 --band-scale 0.82 --bg blur --fps <源帧率>
```

横屏版画面带占宽 82%、居中，四周（含冲出区）是同源画面放大模糊+压暗，
不存在黑边。`--fps` 用 ffprobe 查到的源帧率，不要改变帧率。

默认参数：1080×1920 输出、30fps、isnet-general-use 抠像、
主体在 55% 处开始线性放大、结尾达到 2.0×。
**背景一律优先 `--bg blur`；black 仅在用户明确要复刻教程黑边时使用。**

**调参建议：** 先用短片段（ffmpeg `-t 3` 截 3 秒）快速确认放大时机和强度，
抽 contact sheet 目检满意后再跑全片——抠像约 1.4s/帧，全片跑一遍不便宜。

## 2. 参数调优表

| 参数 | 默认 | 调优说明 |
|---|---|---|
| `--start` | 0.55 | 开始放大的时刻（占总时长比例）。教程选在「主体即将冲出画面」处 |
| `--end` | 1.0 | 达到最大倍数的时刻 |
| `--scale` | 2.0 | 最终倍数：1.6 轻微冲出 / 2.0~2.4 强烈冲出；过大会露出 mask 边缘缺陷 |
| `--ease` | linear | `linear`=剪映线性关键帧；`smooth`=缓入缓出更自然 |
| `--anchor` | 0.5,0.5 | 放大锚点（画面带比例）。主体偏上时用 `0.5,0.4` 避免冲出时脚留在带内 |
| `--track-crop` | 关 | **竖屏素材必开**：16:9 裁切窗口沿 y 轴跟随主体，避免主体（尤其高潮近景）被静态中心裁切掉；横屏无需开 |
| `--track-width` / `--track-model` | 384 / u2net | 跟踪检测的分辨率与模型；跟踪翻转严重时 track-model 换 isnet-general-use |
| `--bg` | black | **优先 blur**=原画面模糊压暗填充；black=黑边（丑，仅复刻教程时用） |
| `--canvas` | 1080x1920 | 输出尺寸。竖屏源用竖屏；**横屏源必须保持横屏（1920x1080），禁止改方向** |
| `--band-scale` | 1.0 | 画面带占画布宽比例。横屏画布用 0.8~0.85 留出四周模糊区；竖屏保持 1.0 |
| `--fps` | 30 | 帧率；归一化时统一 |
| `--model` | isnet-general-use | `u2net` 快 3 倍但主体贴镜头易丢主体；`u2net_human_seg` 纯人物 |
| `--infer-width` | 0（原生） | 设 512 可加速但边缘变软 |
| `--feather` | 1.2 | mask 羽化；边缘有硬齿时调大，主体发虚时调小 |
| `--grow` | 10 | 主体硬区域外允许软 alpha 的像素范围；毛边多就调小 |
| `--alpha-gamma` | 0.6 | <1 让运动模糊的半透明身体变实；主体出现灰影就调小 |
| `--temporal` / `--flip-temporal` | 0.25 / 0.6 | mask 抖动调大 temporal；主体短暂半透明检查 flip 检测 |
| `--no-audio` | 关 | 不携带音轨 |
| `--keep-temp` | 关 | 保留 norm/mask 中间件用于排查 |

## 3. 输出质量判定（抽帧目检）

```bash
ffmpeg -y -i OUTPUT.mp4 -vf "fps=2,scale=216:384,tile=3x3:margin=4:padding=4" -frames:v 1 sheet.png
```

合格标准：
1. 放大前：主体完全看不出两层（与背景严格重合，无双边、无阴影）；
2. 放大中：主体冲出带缘的瞬间，带内背景的主体仍在（抠像层只负责"多出来"的部分）；
3. 结尾：主体贴镜头时边缘干净，无矩形半透明块、无第二只狗/路人被带出来。

不合格时的症状→参数对照见 `references/troubleshooting.md`；
filter graph 逐段图解见 `references/ffmpeg-graph.md`，需要手工改图时读它。

## 4. 原理速览

两层结构（对应剪映的「背景层 + 画中画层」）：

- **背景层**：原视频中心裁剪为 16:9，铺满竖屏宽度、垂直居中（黑边）；
  blur 模式下背后再铺一层同画面的放大模糊+压暗。
- **前景层**：同一画面 → rembg AI 抠像得灰度 mask → `alphamerge` 合成 RGBA
  → `scale eval=frame` 按时间表达式分段缩放 → 按锚点 overlay。

ffmpeg 不做 AI 推理，抠像由 Python（rembg/onnxruntime）完成；
其余全部特效（裁剪、合成、关键帧动画、编码）都在本地 ffmpeg filter graph 内完成。
