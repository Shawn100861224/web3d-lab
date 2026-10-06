#!/usr/bin/env python3
"""用 COLMAP 位姿把「主体稀疏点」投影回每张图，算出所有视角下主体占据的公共 2D 范围，
用于确定一个**统一的裁剪框**（COLMAP 单相机模型下所有图必须用同一个框）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def read_model(sparse: Path):
    cams, imgs = {}, []
    for ln in (sparse / "cameras.txt").read_text().splitlines():
        if ln.strip() and not ln.startswith("#"):
            p = ln.split()
            cams[int(p[0])] = dict(model=p[1], w=int(p[2]), h=int(p[3]),
                                   fx=float(p[4]), fy=float(p[5]), cx=float(p[6]), cy=float(p[7]))
    lines = [l for l in (sparse / "images.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    for i in range(0, len(lines), 2):
        p = lines[i].split()
        imgs.append(dict(qvec=np.array([float(x) for x in p[1:5]]),
                         tvec=np.array([float(x) for x in p[5:8]]),
                         cam_id=int(p[8]), name=p[9]))
    pts = []
    for ln in (sparse / "points3D.txt").read_text().splitlines():
        if ln.strip() and not ln.startswith("#"):
            p = ln.split()
            pts.append([float(p[1]), float(p[2]), float(p[3])])
    return cams, imgs, np.array(pts)


def q2r(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--keep-radius-frac", type=float, default=0.35,
                    help="与训练脚本一致：只保留相机群半径×该比例内的点（≈主体）")
    ap.add_argument("--margin", type=float, default=0.06, help="裁剪框相对主体的外扩比例")
    args = ap.parse_args()

    data = Path(args.data)
    cams, imgs, pts = read_model(data / "sparse" / "0")
    print(f"{len(imgs)} 视角 / {len(pts)} 稀疏点")

    # 相机群中心与半径（与训练脚本同口径）
    C = np.array([-q2r(i["qvec"]).T @ i["tvec"] for i in imgs])
    c0 = C.mean(0)
    radius = float(np.linalg.norm(C - c0, axis=1).max())
    d = np.linalg.norm(pts - c0, axis=1)
    keep = d <= args.keep_radius_frac * radius
    if keep.sum() < 200:
        keep = d <= radius
    obj = pts[keep]
    print(f"主体点 {int(keep.sum())}/{len(pts)}（相机群半径 {radius:.3f}）")

    x0s, y0s, x1s, y1s = [], [], [], []
    for im in imgs:
        cam = cams[im["cam_id"]]
        R, t = q2r(im["qvec"]), im["tvec"].reshape(3, 1)
        pc = R @ obj.T + t                     # 相机坐标系
        z = pc[2]
        m = z > 1e-6
        if m.sum() < 10:
            continue
        u = cam["fx"] * pc[0][m] / z[m] + cam["cx"]
        v = cam["fy"] * pc[1][m] / z[m] + cam["cy"]
        # 用 2%-98% 分位，避免个别离群点把框撑大
        x0s.append(np.percentile(u, 2)); x1s.append(np.percentile(u, 98))
        y0s.append(np.percentile(v, 2)); y1s.append(np.percentile(v, 98))
        print(f"  {im['name']}: u {np.percentile(u,2):.0f}~{np.percentile(u,98):.0f} "
              f"v {np.percentile(v,2):.0f}~{np.percentile(v,98):.0f}")

    W, H = cams[imgs[0]["cam_id"]]["w"], cams[imgs[0]["cam_id"]]["h"]
    print(f"图像 {W}x{H}")
    x0 = max(0, int(min(x0s) - args.margin * W)); x1 = min(W, int(max(x1s) + args.margin * W))
    y0 = max(0, int(min(y0s) - args.margin * H)); y1 = min(H, int(max(y1s) + args.margin * H))
    # 取成 2 的倍数，方便 down 整除
    w = (x1 - x0) // 2 * 2; h = (y1 - y0) // 2 * 2
    print(f"\n✅ 统一裁剪框（全部视角的主体都在里面）：")
    print(f"   --x0 {x0} --y0 {y0} --w {w} --h {h}")
    print(f"   框内主体像素占比（保守估计）≈ 由各视角 2%-98% 分位推得；框尺寸 {w}x{h} 占原图 {w/W*100:.0f}%x{h/H*100:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
