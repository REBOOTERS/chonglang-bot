#!/usr/bin/env python
"""下载 rembg 模型到模型目录，自动尝试 GitHub 加速镜像。

国内直连 GitHub release 经常只有几十 KB/s，本脚本依次尝试镜像。
birefnet* 等模型由 HuggingFace 分发，请设置环境变量
HF_ENDPOINT=https://hf-mirror.com 后再运行 rembg。
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path

GITHUB_BASE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0"
MIRRORS = [
    "https://gh-proxy.com/",
    "https://ghfast.top/",
    "https://ghproxy.net/",
    "",  # 最后直连
]

MODELS = {
    "u2net": "u2net.onnx",
    "u2netp": "u2netp.onnx",
    "u2net_human_seg": "u2net_human_seg.onnx",
    "silueta": "silueta.onnx",
    "isnet-general-use": "isnet-general-use.onnx",
    "isnet-anime": "isnet-anime.onnx",
}


def download(url: str, dest: Path, min_speed: float = 50_000) -> bool:
    print(f"[fetch] {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            total = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                print(f"\r[fetch] {total / 1e6:.1f} MB", end="", flush=True)
        print()
        return dest.stat().st_size > 1_000_000
    except Exception as e:  # noqa: BLE001
        print(f"\n[fetch] failed: {e}", file=sys.stderr)
        if dest.exists():
            dest.unlink()
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model", nargs="?", default="u2net", choices=MODELS)
    args = ap.parse_args()

    home = Path(os.environ.get("U2NET_HOME", Path.home() / ".u2net"))
    home.mkdir(parents=True, exist_ok=True)
    dest = home / MODELS[args.model]
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"[fetch] already exists: {dest}")
        return 0

    src = f"{GITHUB_BASE}/{MODELS[args.model]}"
    for mirror in MIRRORS:
        if download(mirror + src, dest):
            print(f"[fetch] OK -> {dest}")
            return 0
    print("[fetch] all mirrors failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
