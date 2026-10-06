#!/usr/bin/env python3
"""splat_roi_crop.py —— 从训练好的 3DGS PLY 裁出「主体」并写成上网用 .splat（零训练成本）。

动机：单物体环拍里，桌面/房间背景会吃掉大量高斯预算，结果整个场景 bbox 被背景撑大
→ 网页查看器按 bbox 取景 → 主体只占画面一小块，四周全是背景杂点（看起来像"碎片云"）。
裁到主体后：主体像素占比上升、取景自动收紧、体积也变小。

用法：
    python splat_roi_crop.py --ply <ckpt.ply> --analyze
    python splat_roi_crop.py --ply <ckpt.ply> --out out.splat \
        --max-dist 0.8 --min-opacity 0.05 --max-scale 0.05

约定（与 gsplat exporter 一致）：
    PLY 里 scale_* 是 **log 值**、opacity 是 **logit**；.splat 里 scale 是线性、alpha 是 0-255。
"""
from __future__ import annotations

import argparse
import numpy as np

PLY_TYPES = {"float": 4, "float32": 4, "double": 8, "uchar": 1, "uint8": 1, "int": 4, "uint": 4}


def read_ply(path: str):
    with open(path, "rb") as f:
        header = []
        while True:
            line = f.readline().decode("ascii").strip()
            header.append(line)
            if line == "end_header":
                break
        props = [l.split()[-1] for l in header if l.startswith("property")]
        n = next(int(l.split()[-1]) for l in header if l.startswith("element vertex"))
        arr = np.frombuffer(f.read(), dtype=np.float32, count=n * len(props)).reshape(n, len(props))
    return props, arr


def morton_order(xyz: np.ndarray, bits: int = 21) -> np.ndarray:
    """按 Morton 码排序（与 gsplat sort_centers 同一目的：让 .splat 里相邻点空间相邻）。"""
    lo, hi = xyz.min(0), xyz.max(0)
    span = np.where(hi - lo <= 0, 1.0, hi - lo)
    q = np.clip(((xyz - lo) / span * ((1 << bits) - 1)).astype(np.uint64), 0, (1 << bits) - 1)

    def spread(v: np.ndarray) -> np.ndarray:
        v = v & np.uint64((1 << bits) - 1)
        r = np.zeros_like(v)
        for i in range(bits):
            r |= ((v >> np.uint64(i)) & np.uint64(1)) << np.uint64(3 * i)
        return r

    key = spread(q[:, 0]) | (spread(q[:, 1]) << np.uint64(1)) | (spread(q[:, 2]) << np.uint64(2))
    return np.argsort(key)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ply", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--center", default="p50", help="主体中心：p50=按不透明度加权的分位数中心 | 或 'x,y,z'")
    ap.add_argument("--max-dist", type=float, default=None, help="到中心的距离上限（世界单位）")
    ap.add_argument("--box", default=None, help="改用包围盒：xmin,xmax,ymin,ymax,zmin,zmax")
    ap.add_argument("--min-opacity", type=float, default=0.05)
    ap.add_argument("--max-scale", type=float, default=None, help="线性尺度上限（丢掉糊的大团子）")
    args = ap.parse_args()

    props, arr = read_ply(args.ply)
    idx = {p: i for i, p in enumerate(props)}
    xyz = arr[:, [idx["x"], idx["y"], idx["z"]]]
    scale_lin = np.exp(arr[:, [idx["scale_0"], idx["scale_1"], idx["scale_2"]]])
    opacity = 1.0 / (1.0 + np.exp(-arr[:, idx["opacity"]]))          # logit -> 线性
    n = len(xyz)
    print(f"PLY: {n} 个高斯 | 位置总量程 {np.round(xyz.min(0),2)} ~ {np.round(xyz.max(0),2)}")

    # 主体中心：按「不透明度 × 尺度」加权，避免被一堆透明大团子拉偏
    w = opacity * scale_lin.max(1)
    order = np.argsort(w)[::-1]
    top = xyz[order[: max(200, n // 20)]]
    center = top.mean(0)
    print(f"加权中心（前 5% 最'实'的点）: {np.round(center,3)}")

    d = np.linalg.norm(xyz - center, axis=1)
    for q in (50, 75, 90, 95, 99):
        print(f"  到中心距离 {q}% 分位: {np.percentile(d, q):.3f}")
    if args.analyze and args.out is None:
        return 0

    keep = opacity >= args.min_opacity
    print(f"opacity>={args.min_opacity}: {keep.sum()} / {n}")
    if args.max_scale is not None:
        keep &= scale_lin.max(1) <= args.max_scale
        print(f"  + max_scale<={args.max_scale}: {keep.sum()}")
    if args.max_dist is not None:
        keep &= d <= args.max_dist
        print(f"  + 距离<={args.max_dist}: {keep.sum()}")
    if args.box:
        x0, x1, y0, y1, z0, z1 = (float(v) for v in args.box.split(","))
        keep &= ((xyz[:, 0] >= x0) & (xyz[:, 0] <= x1) & (xyz[:, 1] >= y0)
                 & (xyz[:, 1] <= y1) & (xyz[:, 2] >= z0) & (xyz[:, 2] <= z1))
        print(f"  + 包围盒: {keep.sum()}")

    sel = np.nonzero(keep)[0]
    if len(sel) < 100:
        print("❌ 裁得太狠（<100 个点）")
        return 2
    xyz_s, sc_s, op_s = xyz[sel], scale_lin[sel], opacity[sel]
    dc = arr[sel][:, [idx["f_dc_0"], idx["f_dc_1"], idx["f_dc_2"]]]
    rgb = np.clip(0.5 + 0.28209479177387814 * dc, 0, 1)
    quat = arr[sel][:, [idx["rot_0"], idx["rot_1"], idx["rot_2"], idx["rot_3"]]]
    quat = quat / np.linalg.norm(quat, axis=1, keepdims=True)          # (w,x,y,z) 单位化
    rots = np.clip(quat * 128 + 128, 0, 255).astype(np.uint8)
    print(f"保留 {len(sel)} 个高斯 | 新位置量程 {np.round(xyz_s.min(0),2)} ~ {np.round(xyz_s.max(0),2)}"
          f" | 跨度 {np.round(xyz_s.max(0)-xyz_s.min(0),2)}")

    if args.out:
        o = morton_order(xyz_s)
        f32 = lambda a: a.astype("<f4").tobytes()
        # .splat 记录 = 位置 12B + 线性尺度 12B + 颜色 RGBA 4B + 四元数（uint8）4B = 32B
        out = bytearray()
        for i in o:
            out += f32(xyz_s[i])
            out += f32(sc_s[i])
            out += bytes((int(rgb[i, 0] * 255), int(rgb[i, 1] * 255), int(rgb[i, 2] * 255),
                          int(op_s[i] * 255)))
            out += rots[i].tobytes()
        with open(args.out, "wb") as f:
            f.write(bytes(out))
        print(f"✅ 写出 {args.out}（{len(out)/1048576:.2f} MB，{len(out)//32} 点 × 32 字节"
              f" | 字节数能被 32 整除: {len(out) % 32 == 0}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
