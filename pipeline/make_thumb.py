#!/usr/bin/env python3
"""make_thumb.py —— 从查看器截图里裁出一张干净的场景缩略图。

为什么需要它：网页截图里除了 3D 画布还有导航栏、简介文字、指标面板，而且画布常常比视口高
（鞋子落在折叠线以下），按整图百分比裁切必然混进 UI。正确做法是：
  1) 先把画布 scrollIntoView 再截图（由调用方用 JS 做），
  2) 把「画布在屏幕上的矩形」传进来（CSS 像素 × dpr），只在矩形内取景，
  3) 在矩形内用「高饱和 + 高亮度」找出物体包围盒（深色网格背景与浅灰文字都不满足），
     再向外留边距、按 4:3 输出 —— 主体自然居中，且不会沾到任何界面元素。

用法：
  python pipeline/make_thumb.py shot.png -o out.jpg --rect x y w h
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def object_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    """找画面里的主体包围盒（高饱和 或 明显亮于背景的像素）。找不到返回 None。"""
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    val = mx
    hist = np.bincount((val * 255).astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    bg = float(np.argmax(hist)) / 255.0  # 众数亮度 ≈ 背景
    # 背景是暗色网格：只保留"明显更亮"或"明显有颜色"的像素
    mask = ((val > bg + 0.10) & (sat > 0.45)) | (val > bg + 0.16)
    if mask.sum() < 200:
        return None
    ys, xs = np.nonzero(mask)
    # 用分位数而非极值，避免个别飘点把框撑大
    x0, x1 = np.percentile(xs, [1, 99]).astype(int)
    y0, y1 = np.percentile(ys, [1, 99]).astype(int)
    return int(x0), int(y0), int(x1), int(y1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("shot", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--rect", type=float, nargs=4, required=True, metavar=("X", "Y", "W", "H"),
                    help="画布在截图里的矩形（与截图同坐标系；调用方用 JS 的 getBoundingClientRect 读）")
    ap.add_argument("--size", type=int, default=640, help="输出宽度")
    ap.add_argument("--aspect", type=float, default=4 / 3, help="输出宽高比（默认 4:3）")
    ap.add_argument("--margin", type=float, default=0.14, help="物体周围留白比例")
    args = ap.parse_args()

    shot = Image.open(args.shot).convert("RGB")
    W, H = shot.size
    x, y, w, h = args.rect
    box = (max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h)))
    if box[2] - box[0] < 40 or box[3] - box[1] < 40:
        print(f"❌ 画布矩形太小或越界：{box}（截图 {shot.size}）")
        return 2
    canvas = shot.crop(box)

    bb = object_bbox(canvas)
    if bb is None:
        print("⚠️ 没找到主体（画面可能还没渲染完），退化为画布居中裁切")
        bb = (0, 0, canvas.size[0], canvas.size[1])
    bx0, by0, bx1, by1 = bb
    bw, bh = bx1 - bx0, by1 - by0
    exp = 1.0 + 2 * args.margin
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    tw, th = bw * exp, bh * exp
    if tw / th > args.aspect:      # 框太宽 → 按高度撑满
        th = tw / args.aspect
    else:
        tw = th * args.aspect
    l, t = cx - tw / 2, cy - th / 2
    r, b = cx + tw / 2, cy + th / 2
    # 先把取景框夹进画布内，再用画布背景色补齐（不引入画布外的界面像素）
    pad = int(max(0, -l, -t, r - canvas.size[0], b - canvas.size[1])) + 2
    if pad:
        bgcol = tuple(int(v) for v in np.asarray(canvas).reshape(-1, 3)[0])
        padded = Image.new("RGB", (canvas.size[0] + 2 * pad, canvas.size[1] + 2 * pad), bgcol)
        padded.paste(canvas, (pad, pad))
        l, t, r, b = l + pad, t + pad, r + pad, b + pad
        canvas = padded
    crop = canvas.crop((int(l), int(t), int(r), int(b)))
    out = crop.resize((args.size, int(round(args.size / args.aspect))), Image.LANCZOS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.out, quality=90, optimize=True)
    print(f"✅ {args.out}  {out.size}  {args.out.stat().st_size:,} bytes"
          f"（画布 {box[2]-box[0]}×{box[3]-box[1]} → 主体框 {bw}×{bh}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
