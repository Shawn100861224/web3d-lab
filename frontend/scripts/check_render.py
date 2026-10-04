"""对查看器截图做像素级核验：证明画布里真的渲染出了高斯泼溅，
而不是「加载成功但画面全黑」这种假通过。

用法：
    python scripts/check_render.py <screenshot.png> [--rect x,y,w,h]

判据（都很朴素，但足够区分「渲染出来了」和「空画布」）：
  1. 画布区域内亮像素（亮度 > 60）占比落在 0.5% ~ 60% 之间；
  2. 亮像素的重心不在图像边缘（说明是个物体，不是边框或噪点）；
  3. 亮度标准差 > 8（画面有结构，不是纯色）。
"""

from __future__ import annotations

import argparse
import sys

from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--rect", default=None, help="x,y,w,h（CSS 像素，相对页面左上角）")
    ap.add_argument("--scale", type=float, default=None, help="截图相对 CSS 像素的缩放比")
    args = ap.parse_args()

    img = Image.open(args.png).convert("L")
    W, H = img.size
    print(f"截图尺寸：{W}x{H}")

    if args.rect:
        x, y, w, h = (int(float(v)) for v in args.rect.split(","))
        # 视觉截图可能带 device scale；未显式给出时按窗口宽度推断
        s = args.scale if args.scale else 1.0
        box = (int(x * s), int(y * s), int((x + w) * s), int((y + h) * s))
        box = (max(box[0], 0), max(box[1], 0), min(box[2], W), min(box[3], H))
    else:
        box = (0, 0, W, H)

    crop = img.crop(box)
    px = list(crop.getdata())
    n = len(px)
    if n == 0:
        print("裁剪区域为空")
        return 1

    bright = [(i % crop.width, i // crop.width) for i, v in enumerate(px) if v > 60]
    frac = len(bright) / n
    mean = sum(px) / n
    var = sum((v - mean) ** 2 for v in px) / n
    std = var**0.5

    print(f"裁剪区域：{box} -> {crop.width}x{crop.height}")
    print(f"亮度均值 {mean:.1f} / 标准差 {std:.1f}")
    print(f"亮像素（>60）占比 {frac * 100:.2f}%（{len(bright)} 个）")

    ok = True
    if not (0.005 <= frac <= 0.60):
        print(f"✗ 亮像素占比 {frac * 100:.2f}% 不在 0.5%~60%，像是空画布或纯噪点")
        ok = False
    else:
        print("✓ 亮像素占比合理")

    if std <= 8:
        print(f"✗ 亮度标准差 {std:.1f} <= 8，画面没有结构")
        ok = False
    else:
        print(f"✓ 画面有结构（标准差 {std:.1f}）")

    if bright:
        cx = sum(p[0] for p in bright) / len(bright) / crop.width
        cy = sum(p[1] for p in bright) / len(bright) / crop.height
        print(f"亮像素重心：({cx:.2f}, {cy:.2f})（相对画布）")
        if 0.05 < cx < 0.95 and 0.02 < cy < 0.98:
            print("✓ 重心在画布内部（是物体，不是边框）")
        else:
            print("✗ 重心贴边，可能只渲染了边框/背景")
            ok = False

    print("结论：" + ("渲染有效" if ok else "疑似空画布"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
