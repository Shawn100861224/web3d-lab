#!/usr/bin/env python3
"""把一组照片统一成同一分辨率（并可选做轻度曝光归一）。

为什么需要：COLMAP 默认按「同一台相机」重建（single_camera），所有图共用一套内参。
一旦混入不同分辨率的图片，那批就会系统性失配、几乎全部注册失败 ——
实测：1024x1366 注册 48%，1279x1706 注册 0%。

做法：以**出现最多的尺寸**为目标，其余按相同比例缩放到该尺寸；同时按 EXIF 摆正、
统一存成高质量 JPEG（quality=95，避免二次压缩损失）。

用法:
    python prep_unify_size.py <源目录> <目标目录> [--normalize]
--normalize: 把每张图的平均亮度对齐到全组中位数（轻度线性的，不做直方图均衡），
             用于缓解"中途开灯/反光"造成的亮度跳变。默认关闭。
"""
from __future__ import annotations

import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    normalize = "--normalize" in sys.argv
    if len(args) < 2:
        print(__doc__)
        return 2
    src, dst = Path(args[0]), Path(args[1])
    if not src.is_dir():
        print(f"源目录不存在: {src}")
        return 2

    files = sorted(p for p in src.rglob("*") if p.suffix.lower() in EXTS)
    if not files:
        print("没有图片")
        return 1

    sizes: Counter = Counter()
    loaded: list[tuple[Path, Image.Image]] = []
    for p in files:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            sizes[im.size] += 1
            loaded.append((p, im.copy()))

    target, n = sizes.most_common(1)[0]
    print(f"共 {len(files)} 张；尺寸分布: {dict(sizes)}")
    print(f"目标尺寸（出现最多）= {target[0]}x{target[1]}（{n} 张）")

    # 亮度中位数（用于 --normalize）
    med = None
    if normalize:
        means = [float(np.asarray(im.convert("L"), dtype=np.float32).mean()) for _, im in loaded]
        med = float(np.median(means))
        print(f"全组平均亮度中位数 = {med:.1f}（将把每张对齐到它）")

    dst.mkdir(parents=True, exist_ok=True)
    changed = 0
    for idx, (p, im) in enumerate(loaded, start=1):
        if im.size != target:
            im = im.resize(target, Image.LANCZOS)
            changed += 1
        if normalize and med is not None:
            arr = np.asarray(im, dtype=np.float32)
            cur = float(arr.mean())
            if cur > 1:
                arr = np.clip(arr * (med / cur), 0, 255)
                im = Image.fromarray(arr.astype(np.uint8))
        out = dst / f"{idx:03d}.jpg"
        im.save(out, "JPEG", quality=95, subsampling=0)
        im.close()

    print(f"已写出 {len(loaded)} 张 -> {dst}（其中 {changed} 张做了缩放，亮度归一={normalize}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
