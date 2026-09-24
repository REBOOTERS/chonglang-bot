#!/usr/bin/env python
"""主体跟踪裁切：把任意（尤其竖屏）视频裁成 16:9 底片，裁切窗口跟随主体。

静态中心裁对竖屏素材会切掉主体（狗从远处跑来，纵向穿越画面，
高潮帧只剩躯干）。本脚本两遍处理：
  1. 低分辨率解码 + u2net/isnet + HeroTracker，逐帧得到主体中心 y；
  2. 缺失帧插值、轨迹平滑后，按帧从原生帧上裁切出 16:9 窗口，
     缩放成目标 band 尺寸，ffv1 编码并保留原音频。

输出与 burst_effect.py 的 norm 底片同规格（ffv1/mkv，可带音频）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment import HeroTracker, ffprobe_info  # noqa: E402


def raw_reader(path: Path, w: int, h: int, vf: str):
    """按给定 -vf 解出 rgb24 原始帧。"""
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", vf, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
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


def smooth_centers(centers: list[float | None], n: int,
                   window: int) -> np.ndarray:
    """缺失帧线性插值，再做居中滑动平均。"""
    ys = np.array([np.nan if c is None else c for c in centers],
                  dtype=np.float64)
    if np.isnan(ys).all():
        return np.full(n, 0.5)
    if np.isnan(ys).any():
        idx = np.arange(n)
        ys = np.interp(idx, idx[~np.isnan(ys)], ys[~np.isnan(ys)])
    if window > 1:
        kernel = np.ones(window) / window
        # edge-padding，窗口居中
        pad = window // 2
        padded = np.pad(ys, (pad, window - 1 - pad), mode="edge")
        ys = np.convolve(padded, kernel, mode="valid")
    return ys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--band", default="1080x608",
                    help="输出 band 尺寸 WxH（16:9，偶数高）")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--infer-width", type=int, default=384,
                    help="跟踪检测的解码宽度，越小越快")
    ap.add_argument("--model", default="u2net",
                    help="跟踪用抠像模型；翻转严重换 isnet-general-use")
    ap.add_argument("--smooth", type=int, default=9,
                    help="轨迹平滑窗口（帧），奇数语义；1 关闭")
    ap.add_argument("--grow", type=int, default=10)
    args = ap.parse_args()

    try:
        from rembg import new_session, remove
    except ImportError:
        print("ERROR: 未安装 rembg。请在项目 venv 中执行:\n"
              "  uv pip install rembg pillow numpy scipy onnxruntime",
              file=sys.stderr)
        return 2

    bw_s, bh_s = args.band.lower().split("x")
    BW, BH = int(bw_s), int(bh_s)

    info = ffprobe_info(args.input)
    sw, sh, fps = info["width"], info["height"], info["fps"]
    iw = args.infer_width
    ih = max(2, round(sh * iw / sw / 2) * 2)
    print(f"[track] source {sw}x{sh}, infer {iw}x{ih}, band {BW}x{BH}")

    # ---- pass 1: 低分辨率检测主体中心 ----
    session = new_session(args.model)
    tracker = HeroTracker(grow=args.grow, temporal=0.3, flip_temporal=0.6)
    vf1 = f"fps={args.fps:g},scale={iw}:{ih}"
    centers: list[float | None] = []
    for frame in raw_reader(args.input, iw, ih, vf1):
        m = remove(Image.fromarray(frame), session=session,
                   only_mask=True, post_process_mask=True)
        m = tracker.update(np.asarray(m, dtype=np.float32) / 255.0)
        ys = np.where(m > 0.3)[0]
        centers.append(float(ys.mean()) / ih if len(ys) else None)

    n = len(centers)
    if n == 0:
        print("[track] ERROR: 未解码到任何帧", file=sys.stderr)
        return 2
    cy = smooth_centers(centers, n, args.smooth) * sh  # 映射到源高

    # band 窗口映射到源像素（band 宽铺满源宽）
    win_h = BH * sw / BW
    win_h_i = max(2, round(win_h / 2) * 2)
    y0 = np.clip(np.round(cy - win_h_i / 2).astype(int),
                 0, max(0, sh - win_h_i))
    print(f"[track] {n} frames, window {sw}x{win_h_i}, "
          f"y range {int(y0.min())}..{int(y0.max())}")

    # ---- pass 2: 原生帧按帧裁切 -> ffv1 ----
    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{BW}x{BH}",
         "-r", f"{args.fps:g}", "-i", "-",
         "-i", str(args.input),
         "-map", "0:v:0", "-map", "1:a?",
         "-c:v", "ffv1", "-c:a", "copy", "-shortest", str(args.output)],
        stdin=subprocess.PIPE,
    )

    vf2 = f"fps={args.fps:g}"
    k = 0
    for frame in raw_reader(args.input, sw, sh, vf2):
        y = int(y0[k]) if k < len(y0) else int(y0[-1])
        crop = frame[y:y + win_h_i, :, :]
        if crop.shape[0] != BH or crop.shape[1] != BW:
            crop = np.asarray(
                Image.fromarray(crop).resize((BW, BH), Image.BILINEAR))
        writer.stdin.write(np.ascontiguousarray(crop).tobytes())
        k += 1

    writer.stdin.close()
    code = writer.wait()
    print(f"[track] done, {k} frames -> {args.output}")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
