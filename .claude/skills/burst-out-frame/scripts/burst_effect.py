#!/usr/bin/env python
"""「人物冲出画面」效果编排器（裸眼 3D pop-out）。

流程:
  1. ffmpeg 归一化输入 -> 横向 16:9 底片 (norm.mkv)
  2. segment.py 逐帧抠像 -> mask.mkv (ffv1 gray)
  3. ffmpeg 合成竖屏: 背景(黑边/模糊) + 16:9 画面带居中层 + 抠像前景
     关键帧放大冲出画面带

用法:
  python burst_effect.py input.mp4 -o out.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def has_audio(path: Path) -> bool:
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


def duration_of(path: Path) -> float:
    info = probe(path)
    return float(info["format"]["duration"])


def scale_expr(t0: float, t1: float, final: float, ease: str) -> str:
    """返回 ffmpeg 表达式 s(t)，t0 前为 1，t1 时为 final。"""
    p = f"((t-{t0:.4f})/{max(t1 - t0, 1e-6):.4f})"
    y = f"clip({p},0,1)"
    if ease == "smooth":
        k = f"({y})*({y})*(3-2*({y}))"
    else:
        k = y
    return f"1+({final}-1)*{k}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="人物冲出画面 / 裸眼3D pop-out（本地 ffmpeg + rembg）")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--canvas", default="1080x1920",
                    help="输出尺寸 WxH。竖屏素材 1080x1920；横屏素材保持横屏"
                         "（如 1920x1080，配合 --band-scale 与 --bg blur）")
    ap.add_argument("--band-scale", type=float, default=1.0,
                    help="画面带相对画布宽度的比例。竖屏默认 1.0 铺满；"
                         "横屏画布用 0.8~0.85，四周留出模糊区供主体冲出")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--start", type=float, default=0.55,
                    help="开始放大的时刻（占总时长比例 0~1）")
    ap.add_argument("--end", type=float, default=1.0,
                    help="放大到最大的时刻（比例）")
    ap.add_argument("--scale", dest="final_scale", type=float, default=2.0,
                    help="最终放大倍数，1.6 轻微冲出，2.0~2.4 强烈冲出")
    ap.add_argument("--ease", choices=["linear", "smooth"], default="linear",
                    help="linear=剪映默认线性关键帧；smooth=缓入缓出")
    ap.add_argument("--bg", choices=["black", "blur"], default="black",
                    help="black=黑边（复刻教程）；blur=模糊填充（现代风格）")
    ap.add_argument("--anchor", default="0.5,0.5",
                    help="放大锚点 ax,ay（画面带比例），默认正中心")
    # 抠像相关
    ap.add_argument("--track-crop", action="store_true",
                    help="竖屏素材：16:9 裁切窗口跟随主体（track_crop.py），"
                         "避免主体被静态中心裁切掉")
    ap.add_argument("--track-width", type=int, default=384,
                    help="--track-crop 的跟踪检测宽度")
    ap.add_argument("--track-model", default="u2net",
                    help="跟踪裁切用的检测模型，翻转严重换 isnet-general-use")
    ap.add_argument("--model", default="isnet-general-use",
                    help="isnet-general-use 默认（贴近镜头帧稳）；u2net 更快")
    ap.add_argument("--infer-width", type=int, default=0)
    ap.add_argument("--feather", type=float, default=1.2)
    ap.add_argument("--temporal", type=float, default=0.25)
    ap.add_argument("--flip-temporal", type=float, default=0.6)
    ap.add_argument("--grow", type=int, default=10)
    ap.add_argument("--alpha-lo", type=float, default=0.1)
    ap.add_argument("--alpha-hi", type=float, default=0.8)
    ap.add_argument("--alpha-gamma", type=float, default=0.6)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    cw_s, ch_s = args.canvas.lower().split("x")
    CW, CH = int(cw_s), int(ch_s)
    W = max(2, round(CW * args.band_scale / 2) * 2)
    H = max(2, round(W * 9 / 16 / 2) * 2)  # 16:9 画面带，偶数高
    if H > CH:  # 带过高兜底：按高内缩
        W = max(2, round(W * CH / H / 2) * 2)
        H = max(2, round(W * 9 / 16 / 2) * 2)
    BX, BY = (CW - W) // 2, (CH - H) // 2
    ax, ay = (float(x) for x in args.anchor.split(","))

    tmp = Path(tempfile.mkdtemp(prefix="burst_"))
    print(f"[burst] temp: {tmp}")
    try:
        # 1) 归一化底片 -----------------------------------------
        norm = tmp / "norm.mkv"
        if args.track_crop:
            run([
                sys.executable, str(SCRIPT_DIR / "track_crop.py"),
                str(args.input), str(norm),
                "--band", f"{W}x{H}", "--fps", f"{args.fps:g}",
                "--infer-width", str(args.track_width),
                "--model", args.track_model,
            ])
        else:
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},setsar=1,fps={args.fps:g},format=yuv420p")
            run([
                "ffmpeg", "-y", "-v", "error", "-i", str(args.input),
                "-vf", vf, "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "ffv1", "-c:a", "copy", str(norm),
            ])

        D = duration_of(norm)
        audio = has_audio(norm) and not args.no_audio
        print(f"[burst] band {W}x{H}, canvas {CW}x{CH}, duration {D:.2f}s")

        # 2) 抠像 ------------------------------------------------
        mask = tmp / "mask.mkv"
        run([
            sys.executable, str(SCRIPT_DIR / "segment.py"),
            str(norm), str(mask),
            "--model", args.model,
            "--infer-width", str(args.infer_width),
            "--feather", str(args.feather),
            "--temporal", str(args.temporal),
            "--flip-temporal", str(args.flip_temporal),
            "--grow", str(args.grow),
            "--alpha-lo", str(args.alpha_lo),
            "--alpha-hi", str(args.alpha_hi),
            "--alpha-gamma", str(args.alpha_gamma),
        ])

        # 3) 合成 ------------------------------------------------
        t0, t1 = args.start * D, args.end * D
        S = scale_expr(t0, t1, args.final_scale, args.ease)
        print(f"[burst] scale expr: {S}")

        g: list[str] = [
            "[1:v]format=gray,setpts=PTS-STARTPTS[alpha]",
            "[foot][alpha]alphamerge,format=rgba[fg0]",
            f"[fg0]scale=w='iw*({S})':h='ih*({S})':eval=frame:"
            "flags=bilinear[fg]",
        ]
        if args.bg == "blur":
            g.insert(0, "[0:v]setpts=PTS-STARTPTS,split=3[foot][foot2][foot3]")
            g += [
                f"[foot2]scale={CW}:{CH}:force_original_aspect_ratio=increase,"
                f"crop={CW}:{CH},gblur=sigma=28,"
                "eq=brightness=-0.15:saturation=1.1[bgb]",
                f"[bgb][foot3]overlay={BX}:{BY}:eval=init[stage]",
            ]
        else:
            g.insert(0, "[0:v]setpts=PTS-STARTPTS,split=2[foot][foot3]")
            g.insert(0, f"color=c=black:s={CW}x{CH}:r={args.fps:g}:"
                        f"d={D:.3f}[base]")
            g += [
                f"[base][foot3]overlay={BX}:{BY}:eval=init[stage]",
            ]
        # 锚点在画布上的固定位置 = 带偏移 + ax*W；放大层从该点向四周扩张
        ox = f"round({BX}+{ax}*{W}-({S})*{ax}*{W})"
        oy = f"round({BY}+{ay}*{H}-({S})*{ay}*{H})"
        g.append(f"[stage][fg]overlay=x='{ox}':y='{oy}':eval=frame:"
                 "eof_action=pass[outv]")

        compose = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(norm), "-i", str(mask),
            "-filter_complex", ";".join(g),
            "-map", "[outv]",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
        if audio:
            compose += ["-map", "0:a", "-c:a", "aac", "-b:a", "192k"]
        compose += ["-shortest", str(args.output)]
        run(compose)

        print(f"[burst] DONE -> {args.output}")
        return 0
    finally:
        if not args.keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"[burst] temp kept: {tmp}")


if __name__ == "__main__":
    raise SystemExit(main())
