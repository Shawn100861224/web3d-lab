#!/usr/bin/env python3
"""把 COLMAP 数据集裁到主体区域，让高斯容量与分辨率都花在主体上。

为什么有用：手机环绕拍小物体时，虚化的背景往往占掉一半以上画面——
它既训不出细节（散焦是视角相关的），又白占显存和渲染瓦片。
裁掉背景后：渲染瓦片数下降 → WSL 能塞下的高斯数上限上升；主体像素占比上升。

⚠️ 裁剪等于**移动主点**：必须同步改 cameras.txt 的 cx/cy（减偏移）与 WIDTH/HEIGHT，
   否则相机会系统性错位，训练结果会糊成一团（本项目实测过）。

用法（Windows 侧跑，读 WSL 里的数据集用 UNC 路径）:
    python prep_crop_roi.py --src <数据集目录> --dst <输出目录> \
        --x0 484 --y0 665 --w 3064 --h 2359

数据集目录里应有 images/ 与 sparse/0/{cameras.txt,images.txt,points3D.txt}。
输出目录结构与之相同，可直接喂给 03_train_gsplat.py / 06_train_from_colmap.sh。
"""
from __future__ import annotations

import argparse
import os
import shutil


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="源数据集目录（含 images/ 与 sparse/0/）")
    ap.add_argument("--dst", required=True, help="输出数据集目录")
    ap.add_argument("--x0", type=int, required=True, help="裁剪左上角 x（原图像素）")
    ap.add_argument("--y0", type=int, required=True, help="裁剪左上角 y（原图像素）")
    ap.add_argument("--w", type=int, required=True, help="裁剪宽度")
    ap.add_argument("--h", type=int, required=True, help="裁剪高度")
    ap.add_argument("--quality", type=int, default=95, help="输出 JPEG 质量")
    args = ap.parse_args()

    from PIL import Image  # 延迟导入，便于 --help 在没有 PIL 的环境里也能看

    src, dst = args.src, args.dst
    img_src = os.path.join(src, "images")
    img_dst = os.path.join(dst, "images")
    sparse_src = os.path.join(src, "sparse")
    sparse_dst = os.path.join(dst, "sparse")
    for p in (img_src, os.path.join(sparse_src, "0", "cameras.txt")):
        if not os.path.exists(p):
            print("❌ 找不到:", p)
            return 2

    os.makedirs(img_dst, exist_ok=True)
    names = sorted(f for f in os.listdir(img_src) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    for i, n in enumerate(names, 1):
        im = Image.open(os.path.join(img_src, n))
        w, h = im.size
        box = (args.x0, args.y0, min(args.x0 + args.w, w), min(args.y0 + args.h, h))
        im.crop(box).save(os.path.join(img_dst, n), "JPEG", quality=args.quality)
        if i % 20 == 0:
            print("  已裁 %d/%d" % (i, len(names)))
    print("裁剪 %d 张 -> %s（%dx%d）" % (len(names), img_dst, args.w, args.h))

    if os.path.exists(sparse_dst):
        shutil.rmtree(sparse_dst)
    shutil.copytree(sparse_src, sparse_dst)

    cam_txt = os.path.join(sparse_dst, "0", "cameras.txt")
    out_lines = []
    for ln in open(cam_txt, encoding="utf-8").read().splitlines():
        if ln.strip() and not ln.startswith("#"):
            p = ln.split()
            fx, fy, cx, cy = float(p[4]), float(p[5]), float(p[6]), float(p[7])
            rest = " ".join(p[8:])
            new = "%s %s %d %d %.10f %.10f %.4f %.4f %s" % (
                p[0], p[1], args.w, args.h, fx, fy, cx - args.x0, cy - args.y0, rest)
            print("cameras.txt:\n  旧 %s\n  新 %s" % (ln.strip(), new))
            out_lines.append(new)
        else:
            out_lines.append(ln)
    open(cam_txt, "w", encoding="utf-8").write("\n".join(out_lines) + "\n")
    print("✅ 完成:", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
