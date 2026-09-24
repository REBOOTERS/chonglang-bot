# 故障排查：症状 → 处置

成片不合格时按症状查表。排查通用手段：`--keep-temp` 保留 norm.mkv / mask.mkv，
直接看灰度 mask；必要时把命令里 `-v error` 换成 `-v info`。

## A. Mask / 抠像问题

### A1. 冲出的主体边缘有矩形/方块状半透明毛边
- 主体背后的路人、杂物被粘连进 mask。
- 处置：`--grow 6`（缩小软 alpha 允许范围）；`--alpha-lo 0.2` 压低 alpha 碎块；
  仍有块影说明中间件被 H.264 压过（应使用 ffv1，见 lessons.md L6）。

### A2. 主体冲出时带着第二只狗/路人一起放大
- 模型抠出了多个目标。
- 处置：确认用的是最新 segment.py（HeroTracker 默认只保留与主体连通块）。
  若两目标有淡 alpha 桥连，调 `--grow 6` 断桥。

### A3. 高潮帧主体短暂变半透明 / 丢失 1~2 帧
- 显著性翻转帧。
- 处置：换 `--model isnet-general-use`；调大 `--flip-temporal 0.75`；
  阈值 `--alpha-gamma 0.5` 让残留软区域更实。

### A4. 主体边缘锯齿、硬边、有毛茬
- 羽化不足或源片本身分辨率低。
- 处置：`--feather 2`；确认 `--infer-width 0`（原生分辨率推理）。

### A5. 主体发虚、像隔了层纱
- 羽化/色阶过头。
- 处置：`--feather 0.6 --alpha-gamma 0.8 --grow 14`。

### A6. Mask 帧间抖动、边缘闪烁
- 处置：`--temporal 0.4`；源片噪点严重时先在归一化阶段轻度降噪
  （在 burst_effect.py 归一化 vf 中加 `hqdn3d=2`）。

### A7. 第一帧/主体静止时 mask 就不对
- 显著性选错了初始目标。
- 处置：换模型（人→`u2net_human_seg`，动漫→`isnet-anime`）；
  或先裁剪画面让主体成为最显著目标后再跑。

## B. 流程 / 环境问题

### B1. `import rembg` 失败 / 模型加载报错
- venv 未激活或包装在别处。
- 处置：用 `.venv/Scripts/python.exe` 显式调用；
  `uv pip install --python .venv/Scripts/python.exe rembg onnxruntime`。

### B2. `new_session` 卡在下载
- GitHub 慢。处置：`scripts/fetch_model.py <model>`（镜像），见 lessons.md L2。

### B3. ffmpeg 退出码非零且几乎无报错
- 多为 graph 链接错误（未消费的 label / pad 复用）。
- 处置：`-v info` 重跑 compose；对照 references/ffmpeg-graph.md 检查 split 路数。

### B4. 输出时长不对 / 结尾被裁
- `-shortest` 按最短流收尾，mask 与底片帧数以 fps 归一化后应一致。
- 处置：检查 `--fps` 是否与源差异过大；用 ffprobe 对比 norm/mask 的 nb_frames。

### B5. 输出没有声音
- 处置：确认输入有音轨（`ffprobe`）；未加 `--no-audio`；
  norm 阶段 `-map 0:a?`，合成阶段 `-map 0:a`。AAC 兼容差时改 `-c:a aac -b:a 192k`（默认）。

### B6. 处理速度太慢
- isnet 1.36s/帧。
- 处置：先用 `-t` 短片段调参；试 `--model u2net`（确认主体不会贴脸）；
  `--infer-width 640`；降低输出画布。
