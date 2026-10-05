#!/usr/bin/env python3
"""拍照体检：在跑 COLMAP 之前先判断这组照片能不能用。

为什么需要它：COLMAP 一轮约 6 分钟、训练 5–15 分钟。如果照片本身糊了、
曝光在整组里乱跳、或分辨率不一致，跑完才发现是白费时间。这个脚本只看
"能不能用"，不判断内容（内容对不对得人眼看）。

检查项：
  1. 张数（<20 基本无望，20–30 可用，35–60 最佳，>100 收益低）
  2. 分辨率是否一致（不一致会被 COLMAP 当成不同相机，严重影响内参估计）
  3. 清晰度：拉普拉斯方差，逐张算，用于揪出糊片
  4. 曝光：全图平均亮度的分布，用于发现"中途开灯/拉窗帘"
  5. 文件体积异常（过小通常意味着被压缩过，例如微信传图）

用法：
    python photos_check.py <图片目录>
退出码：0 = 可以跑；1 = 建议先处理（会列出具体哪几张）
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
BLUR_VAR_MIN = 40.0      # 拉普拉斯方差低于此值基本可判为糊
BRIGHT_SPREAD_MAX = 55.0  # 全组平均亮度的极差（0-255）


def laplacian_var(gray: np.ndarray) -> float:
    g = gray.astype(np.float32)
    lap = (
        4.0 * g[1:-1, 1:-1]
        - g[:-2, 1:-1] - g[2:, 1:-1]
        - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return float(lap.var())


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python photos_check.py <图片目录>")
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"目录不存在: {root}")
        return 2

    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXTS)
    if not files:
        print(f"{root} 里没有找到图片")
        return 1

    print(f"=== 拍照体检：{root} ===")
    print(f"图片张数: {len(files)}")
    if len(files) < 20:
        print("  ⚠ 少于 20 张：单物体环绕重建基本无望（会有大面积空洞）")
    elif len(files) < 30:
        print("  ~ 20–30 张：可以试，但顶部/某一侧容易有洞")
    elif len(files) <= 60:
        print("  ✓ 35–60 张：理想区间")
    else:
        print("  ~ 超过 60 张：能用，但 COLMAP 会更慢、收益有限")

    sizes: Counter = Counter()
    rows = []
    for p in files:
        try:
            with Image.open(p) as im:
                im = ImageOps.exif_transpose(im)  # 按 EXIF 摆正，和 COLMAP 一致
                w, h = im.size
                gray = np.asarray(im.convert("L"), dtype=np.uint8)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ 无法读取 {p.name}: {exc}")
            continue
        sizes[(w, h)] += 1
        rows.append({
            "name": p.name,
            "size": (w, h),
            "kb": p.stat().st_size / 1024,
            "bright": float(gray.mean()),
            "sharp": laplacian_var(gray),
        })

    if not rows:
        print("没有可解析的图片")
        return 1

    print("\n--- 分辨率分布 ---")
    for (w, h), n in sizes.most_common():
        print(f"  {w}x{h}: {n} 张")
    if len(sizes) > 1:
        print("  ⚠ 分辨率不一致：COLMAP 会按不同相机处理，内参估计变差，建议统一")

    bright = np.array([r["bright"] for r in rows])
    sharp = np.array([r["sharp"] for r in rows])
    kb = np.array([r["kb"] for r in rows])

    print("\n--- 清晰度（拉普拉斯方差，越高越锐）---")
    print(f"  中位 {np.median(sharp):.0f} | 最小 {sharp.min():.0f} | 最大 {sharp.max():.0f}")
    blurry = [r for r in rows if r["sharp"] < BLUR_VAR_MIN]
    if blurry:
        print(f"  ⚠ {len(blurry)} 张疑似糊片（<{BLUR_VAR_MIN:.0f}），建议重拍：")
        for r in sorted(blurry, key=lambda x: x["sharp"])[:12]:
            print(f"    {r['name']}  sharp={r['sharp']:.0f}")
    else:
        print("  ✓ 没有明显糊片")

    print("\n--- 曝光一致性（全图平均亮度 0-255）---")
    print(f"  中位 {np.median(bright):.1f} | 极差 {bright.max() - bright.min():.1f}")
    if bright.max() - bright.min() > BRIGHT_SPREAD_MAX:
        print(f"  ⚠ 亮度极差 >{BRIGHT_SPREAD_MAX:.0f}：拍摄期间光照变了（开灯/窗帘/阴影），")
        print("    这会让匹配大量出错。最亮/最暗的几张：")
        for r in sorted(rows, key=lambda x: x["bright"])[:3] + sorted(rows, key=lambda x: -x["bright"])[:3]:
            print(f"    {r['name']}  bright={r['bright']:.1f}  sharp={r['sharp']:.0f}")
    else:
        print("  ✓ 曝光基本一致")

    print("\n--- 文件体积 ---")
    print(f"  中位 {np.median(kb):.0f} KB | 最小 {kb.min():.0f} KB | 最大 {kb.max():.0f} KB")
    tiny = [r for r in rows if r["kb"] < 80]
    if tiny:
        print(f"  ~ {len(tiny)} 张明显偏小（可能被压缩过，例如微信传图会重压缩）：")
        for r in sorted(tiny, key=lambda x: x["kb"])[:8]:
            print(f"    {r['name']}  {r['kb']:.0f} KB  {r['size'][0]}x{r['size'][1]}")

    ok = not blurry and (bright.max() - bright.min()) <= BRIGHT_SPREAD_MAX and len(sizes) == 1
    print("\n=== 结论 ===")
    if ok:
        print("✓ 这组可以用，建议直接跑 COLMAP")
        return 0
    print("~ 有上面标 ⚠ 的问题，建议先重拍/补齐那几张；仍可强行跑，但成功率会下降")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
