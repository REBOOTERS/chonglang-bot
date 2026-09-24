# videox-factory

「人物冲出画面（裸眼 3D pop-out）」skill 的实验场与产出目录。本目录由
`task.md` 的任务产生：看 `lesson.mp4` 教程学会剪法 → 沉淀为 skill →
对 `example/` 里的任意素材复刻效果。

skill 本体在**仓库根** `.claude/skills/burst-out-frame/`（SKILL.md + scripts +
lessons.md + references），本目录只放素材、venv 和实验/产出文件。
跑效果的命令形态：用**本目录的 venv** 去执行 skill 里的脚本。

```bash
.venv/Scripts/python.exe ../.claude/skills/burst-out-frame/scripts/burst_effect.py INPUT.mp4 -o OUTPUT.mp4 --bg blur
```

## 目录结构

| 路径 | 内容 | 入库？ |
|---|---|---|
| `task.md` | 任务定义 | ✅ |
| `lesson.mp4` | 教程源视频（只读，2.5MB） | ❌ 视频 |
| `example/1~4.mp4` | 待复刻的素材 | ❌ 视频 |
| `output/N_3d.mp4` | 最终成片 | ❌ 视频 |
| `analysis/` | 调试中间产物（抽帧、mask、contact sheet、试跑片段） | ❌ 全忽略 |
| `.venv/` | Python 3.13 venv | ❌ 跨设备重建 |

## 环境配置（新设备复刻步骤）

前提：Windows + [uv](https://docs.astral.sh/uv/) + ffmpeg 6.x+（本流程只用内置 filter）。

1. **不要用系统 `python`** —— 本机 `python` 是 Windows 商店占位符（`where python`
   指向 WindowsApps），运行只会跳商店。一律用 venv 解释器。
2. 建 venv 并装依赖（图像处理用 Python/uv，**禁止用 Node**）：

   ```bash
   cd videox-factory
   uv venv                          # Python 3.13.x
   uv pip install --python .venv/Scripts/python.exe rembg pillow numpy scipy onnxruntime
   ```

   当前实测版本（Python 3.13.6）：rembg 2.0.85、onnxruntime 1.30.0、
   numpy 2.5.3、pillow 12.3.0、scipy 1.18.1、scikit-image 0.26.0。
3. **下载抠像模型**（rembg 首次 `new_session()` 会直连 GitHub，国内仅 21KB/s，
   不要等它）。用 skill 自带脚本走镜像（gh-proxy.com 实测 2.9MB/s）：

   ```bash
   .venv/Scripts/python.exe ../.claude/skills/burst-out-frame/scripts/fetch_model.py isnet-general-use
   .venv/Scripts/python.exe ../.claude/skills/burst-out-frame/scripts/fetch_model.py u2net   # 跟踪用，可选
   ```

   模型落在 `~/.u2net/*.onnx`（所有模型共用此目录）。birefnet* 走 HuggingFace，
   需 `HF_ENDPOINT=https://hf-mirror.com`。
4. 自检：`ffmpeg -version`、`.venv/Scripts/python.exe -c "import rembg"`。

## 硬性规则（来自 lessons.md，违反会被用户否决）

- **横屏源必须出横屏**：`--canvas 1920x1080 --band-scale 0.82`，先 ffprobe 看源方向；
  改画布方向前必须问用户。
- **背景一律 `--bg blur`**（同源画面放大模糊+压暗），禁黑边；black 仅用户点名复刻教程时用。
- **先短片段后全片**：ffmpeg `-t 3` 截 3 秒调 `--start/--scale/--anchor`，contact sheet
  目检满意再跑全片（isnet ~1.4s/帧）。
- 输出质量判定、症状→参数对照、filter graph 图解见 skill 的
  `SKILL.md` / `lessons.md` / `references/`，执行前先读。
