#!/usr/bin/env python
"""逐帧抠像，输出灰度 mask 视频（ffv1/mkv）。

输入任意视频 -> ffmpeg 解出 rgb24 原始帧 -> rembg 推理 -> mask 后处理
（主体跨帧跟踪 / 去粘连杂块 / 色阶硬化 / 翻转保护 / 羽化）
-> ffmpeg 编码 ffv1 gray mkv。

输出 mask 与输入同尺寸、同帧率，供后续 ffmpeg alphamerge 使用。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def ffprobe_info(path: Path) -> dict:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    info = json.loads(out)
    st = info["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    dur = float(st.get("duration") or info["format"]["duration"])
    return {"width": int(st["width"]), "height": int(st["height"]),
            "fps": fps, "duration": dur}


def frame_reader(path: Path, w: int, h: int):
    """yield np.uint8 rgb frames from ffmpeg rawvideo pipe."""
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE,
    )
    frame_size = w * h * 3
    try:
        while True:
            buf = proc.stdout.read(frame_size)
            if not buf or len(buf) < frame_size:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
    finally:
        proc.stdout.close()
        proc.wait()


class HeroTracker:
    """跨帧锁定同一个主体。

    rembg 模型偶尔会在主体贴近镜头时把显著性翻转给远处的完整小目标，
    也会把主体背后的路人/阴影粘连进 mask。本跟踪器：
      - 按与上一帧主体的重叠量选择当前帧主体（而非单纯比大小）；
      - 软 alpha 只保留在主体硬区域的膨胀范围内，砍掉远处粘连块；
      - 检测到主体置信骤降（翻转帧）时加大与上一帧的混合。
    """

    def __init__(self, grow: int = 10, temporal: float = 0.25,
                 flip_temporal: float = 0.6):
        self.grow = grow
        self.temporal = temporal
        self.flip_temporal = flip_temporal
        self.prev: np.ndarray | None = None

    @staticmethod
    def _components(binary: np.ndarray):
        return ndimage.label(binary, structure=np.ones((3, 3)))

    def _choose_hero(self, soft: np.ndarray) -> np.ndarray:
        """返回主体二值区域（在 alpha>.3 的连通域上选择）。"""
        labels, n = self._components(soft > 0.3)
        if n == 0:
            return np.zeros_like(soft, dtype=bool)
        if self.prev is None:
            sizes = ndimage.sum(np.ones_like(labels), labels,
                               index=range(1, n + 1))
            return labels == int(np.argmax(sizes)) + 1
        prev_region = self.prev > 0.2
        overlap = ndimage.sum(prev_region.astype(np.float32), labels,
                              index=range(1, n + 1))
        if overlap.max() <= 0:
            sizes = ndimage.sum(np.ones_like(labels), labels,
                               index=range(1, n + 1))
            return labels == int(np.argmax(sizes)) + 1
        return labels == int(np.argmax(overlap)) + 1

    def update(self, raw: np.ndarray) -> np.ndarray:
        """raw: float 0..1 -> 返回硬化+时序处理后的 float mask。"""
        # 填内部小洞（腿间、身体缝隙）
        solid = ndimage.binary_fill_holes(raw > 0.5)
        raw = np.maximum(raw, solid.astype(np.float32) * 0.6)

        hero = self._choose_hero(raw)
        # 主体硬身体（含填洞），软 alpha 只允许出现在其附近
        hard = solid & self._near(hero, 4)
        allowed = self._near(hard, self.grow) | hero
        m = raw * allowed

        # 再砍一次：只保留与主体连通的块（丢弃远处第二只狗/路人）
        labels, n = self._components(m > 0.15)
        if n > 1:
            hero_labels = np.unique(labels[hero])
            hero_labels = hero_labels[hero_labels > 0]
            m = m * np.isin(labels, hero_labels)

        if self.prev is None:
            pass
        else:
            # 翻转检测：主体区域内平均不透明度骤降 -> 加强粘连
            cur_mean = float(m[allowed].mean()) if allowed.any() else 0.0
            prev_mean = float(self.prev[allowed].mean()) if allowed.any() else 0.0
            beta = self.flip_temporal if prev_mean - cur_mean > 0.18 \
                else self.temporal
            if beta > 0:
                m = (1 - beta) * m + beta * self.prev
            # 上一帧带入的残影不得超出当前帧主体范围
            m = m * allowed
        self.prev = m
        return m

    @staticmethod
    def _near(binary: np.ndarray, iterations: int) -> np.ndarray:
        if iterations <= 0:
            return binary
        return ndimage.binary_dilation(binary, iterations=iterations)


def finish(mask: np.ndarray, alpha_lo: float, alpha_hi: float,
           alpha_gamma: float, feather: float) -> np.ndarray:
    """色阶 + gamma + 羽化，返回 uint8。"""
    mask = np.clip((mask - alpha_lo) / max(alpha_hi - alpha_lo, 1e-6), 0, 1)
    if alpha_gamma and alpha_gamma != 1.0:
        mask = np.power(mask, alpha_gamma)
    if feather > 0:
        mask = ndimage.gaussian_filter(mask.astype(np.float32), feather)
        mask = np.clip(mask * 1.05, 0, 1)
    return (mask * 255).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--model", default="u2net",
                    help="rembg 模型: isnet-general-use / u2net / u2netp / "
                         "silueta / u2net_human_seg ...")
    ap.add_argument("--infer-width", type=int, default=0,
                    help="推理时缩放到此宽度，0=原生分辨率（边缘最好）")
    ap.add_argument("--feather", type=float, default=1.2,
                    help="羽化 sigma（输出分辨率像素），0 关闭")
    ap.add_argument("--temporal", type=float, default=0.25,
                    help="正常帧的前一帧混合系数，0 关闭")
    ap.add_argument("--flip-temporal", type=float, default=0.6,
                    help="显著性翻转帧的前一帧混合系数")
    ap.add_argument("--grow", type=int, default=10,
                    help="主体硬区域外允许软 alpha 的像素范围")
    ap.add_argument("--alpha-lo", type=float, default=0.1,
                    help="低于此透明度的 mask 压为 0（去毛边）")
    ap.add_argument("--alpha-hi", type=float, default=0.8,
                    help="高于此透明度的 mask 拉向 1（收紧边缘）")
    ap.add_argument("--alpha-gamma", type=float, default=0.6,
                    help="<1 硬化半透明运动模糊身体区，1 关闭")
    args = ap.parse_args()

    # 延迟导入，缺依赖时给出明确报错
    try:
        from rembg import new_session, remove
    except ImportError:
        print("ERROR: 未安装 rembg。请在项目 venv 中执行:\n"
              "  uv pip install rembg pillow numpy scipy onnxruntime",
              file=sys.stderr)
        return 2

    info = ffprobe_info(args.input)
    w, h, fps = info["width"], info["height"], info["fps"]
    print(f"[segment] {w}x{h} @ {fps:.2f}fps  model={args.model}")

    session = new_session(args.model)
    tracker = HeroTracker(grow=args.grow, temporal=args.temporal,
                          flip_temporal=args.flip_temporal)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
         "-r", f"{fps:g}", "-i", "-",
         "-c:v", "ffv1", "-an", str(args.output)],
        stdin=subprocess.PIPE,
    )

    n = 0
    for frame in frame_reader(args.input, w, h):
        pil = Image.fromarray(frame)
        if args.infer_width and args.infer_width < w:
            ratio = args.infer_width / w
            small = pil.resize((args.infer_width, max(1, round(h * ratio))),
                               Image.BILINEAR)
            m_small = remove(small, session=session, only_mask=True,
                             post_process_mask=True)
            mask = np.asarray(m_small.resize((w, h), Image.BILINEAR),
                              dtype=np.float32) / 255.0
        else:
            m = remove(pil, session=session, only_mask=True,
                       post_process_mask=True)
            mask = np.asarray(m, dtype=np.float32) / 255.0

        tracked = tracker.update(mask)
        out = finish(tracked, args.alpha_lo, args.alpha_hi,
                     args.alpha_gamma, args.feather)
        writer.stdin.write(out.tobytes())
        n += 1
        if n % 30 == 0:
            print(f"[segment] {n} frames")

    writer.stdin.close()
    code = writer.wait()
    print(f"[segment] done, {n} frames -> {args.output}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
