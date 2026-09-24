# Lessons：执行本 skill 的踩坑记录

按「现象 → 原因 → 正确做法」记录。每次执行前先读，避免重蹈。

---

## L1. 本机 `python` 是 Windows 商店占位符，不是解释器

- **现象：** `python --version` 无输出/退出码异常，`where python` 指向
  `C:\Users\engineer\AppData\Local\Microsoft\WindowsApps\python.exe`。
- **原因：** 那是 Windows 的应用商店别名，运行只会跳转商店。
- **做法：** 一律用项目 venv：`.venv/Scripts/python.exe`（Python 3.13.6）。
  没有 venv 就用 `uv venv` 建，装包用
  `uv pip install --python .venv/Scripts/python.exe <pkg>`。
  **不要用 Node 处理图像**（用户明确要求）。

## L2. rembg 模型直连 GitHub 只有 21KB/s

- **现象：** `new_session()` 下载 u2net.onnx（176MB）卡住，10 分钟无文件。
- **原因：** release 资源走 objects.githubusercontent.com，国内慢。
- **做法：** 用 `scripts/fetch_model.py <model>`，自动尝试镜像
  （gh-proxy.com 实测 2.9MB/s，ghfast.top 次之）。
  模型文件位置：`~/.u2net/<name>.onnx`（所有模型共用此目录，不止 u2net）。
  birefnet* 由 HuggingFace 分发 → `export HF_ENDPOINT=https://hf-mirror.com`。

## L3. u2net 在主体贴近镜头时会把主体误判为"背景"

- **现象：** 狗冲到镜头前、占画面 >50% 时，u2net 输出的主体变成远处第二只完整小狗，
  前景大狗只剩 alpha 5% 的鬼影——成片高潮帧主体丢失。
- **原因：** u2net 是显著性目标检测，偏好"完整、居中、尺寸适中"的目标；
  贴脸大主体被当作近景背景。
- **做法：** 默认模型用 **isnet-general-use**（贴脸帧不翻转，代价 ~3× 耗时）。
  需要快出片且主体不会贴脸时才用 u2net。

## L4. 即便 isnet 也会有 1~2 帧显著性翻转 + 把次要目标一起抠出

- **现象：** 个别帧主体 alpha 骤降到 ~35%，且 mask 里带着远处第二只狗、背后路人。
- **做法（已内建在 segment.py 的 HeroTracker）：**
  - 跨帧按与上一帧主体的**重叠量**选主体，而非每帧独立取最大块；
  - 软 alpha 只允许出现在主体硬区域 `--grow`（默认10px）范围内，砍粘连杂块；
  - 检测到主体区域平均 alpha 骤降 >0.18 时，该帧与上一帧混合 0.6（`--flip-temporal`）；
  - 时序混合后再乘当前帧范围，防止上一帧残影被带入。
  排查时用 `--keep-temp` 保留 mask.mkv，直接看灰度帧比看成片快。

## L5. filter_complex 里未链接的 label 会直接报错（退出码 -22）

- **现象：** 加了 `[base]` 颜色源但 blur 模式没用到，或 split 出 3 路只用 2 路，
  ffmpeg 静默返回非零（`-v error` 下报错信息可能很短）。
- **做法：** graph 里每个 split 分支都必须被消费：
  黑底 split=2（抠像 + 画面带 overlay），blur split=3（抠像 + 模糊底 + 画面带）。
  调试时把 `-v error` 临时换成 `-v info` 看完整链路报错。

## L6. 中间件必须无损，否则抠像层边缘带压缩痕迹

- **做法：** 归一化底片与 mask 都用 **ffv1/mkv**（ffv1 在 1080×608 体积可接受），
  mask 用 gray pix_fmt；最终才编码 H.264（crf 18）。
  不要用 H.264 当中间件——8×8 块误差在放大 2× 后会变成主体周围的方块鬼影。

## L7. 16:9 画面带的偶数高

- **做法：** 画面带高 = 宽 × 9/16，1080 → 607.5 取 608（偶）。
  yuv420p 要求宽高均为偶数；720 宽对应 405（奇），由编排器统一 round 到偶数。

## L8. 调参顺序：时机/强度先于边缘质量

- **做法：** 先 ffmpeg `-t 3` 截短片段 + 默认模型快速试 `--start/--scale/--anchor`，
  contact sheet 目检满意后再全片精修 `--feather/--alpha-gamma/--grow`。
  isnet ~1.36s/帧、u2net ~0.47s/帧，全片反复跑很浪费时间。

## L9. 竖屏素材不能静态中心裁 16:9

- **现象：** 竖屏拍的狗朝镜头跑来，纵向穿越画面。中心裁出的 16:9 band 里，
  远处的狗在带外（上方），高潮近景帧头被裁掉只剩躯干。
- **做法：** 用 `scripts/track_crop.py`（编排器 `--track-crop`）：
  低分辨率 u2net + HeroTracker 逐帧取主体中心 → 插值+滑动平均平滑 →
  裁切窗口沿 y 跟随主体。两遍纯 rawvideo 管道，开销只多一次低分辨率 u2net。
  band 宽 = 源宽，水平方向不跟踪（横向运动靠构图留白）。

## L10. 横屏源禁止输出竖屏；黑边被用户明确否决

- **现象：** 把横屏 16:9 素材塞进默认 1080×1920 竖屏画布，横屏内容被缩成
  画面带——用户强烈反对；`--bg black` 的黑边也被明确判为"丑"。
- **做法（硬性规则）：**
  - 先 ffprobe 看源方向：横屏源 → `--canvas 1920x1080 --band-scale 0.82`，
    输出必须横屏；`--fps` 取源帧率。
  - 背景默认/一律 `--bg blur`（同源画面放大模糊+压暗），不要 black。
  - 改变画布方向前必须先问用户，不能拿默认值直接跑。
