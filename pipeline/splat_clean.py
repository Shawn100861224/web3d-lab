"""清理 .splat 资产里的浮动点与「大团子」——不改训练，只做后处理。

为什么需要它：自训场景的观感差，除了拍摄本身，还有两类**后处理能救**的东西：
  1. **浮动点（floaters）**：离主体很远的孤立高斯，飘在周围像雾；
  2. **超大高斯**：单个高斯尺度很大时会把画面糊成一片（尤其背景/地面）。
这两类是 3DGS 的常见产物，剪掉它们通常能让画面干净不少，且**零成本、不动训练**。

.splat 布局（32 字节/条，来自本项目 splat_x180.py 的约定）：
  [0:12]   xyz      float32×3
  [12:24]  scale    float32×3（**线性**，不是 log）
  [24:28]  RGBA     uint8×4    ← 第 4 个字节是 alpha（不透明度）
  [28:32]  rotation 四元数 uint8×4（w,x,y,z 各 = q*128+128）

用法（先看统计再动刀，推荐先 --dry-run）：

    python pipeline/splat_clean.py frontend/public/demo/shoe.splat --dry-run
    python pipeline/splat_clean.py frontend/public/demo/shoe.splat \
        -o work/shoe-clean.splat --min-alpha 30 --scale-k 6 --dist-pct 99.0 --clamp-scale-k 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REC = 32


def load_splat(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = np.fromfile(path, dtype=np.uint8)
    if raw.size % REC:
        raise SystemExit(f"{path}：字节数 {raw.size} 不是 32 的倍数，不像 .splat")
    rec = raw.reshape(-1, REC).copy()
    xyz = rec[:, 0:12].copy().view("<f4").reshape(-1, 3)
    scale = rec[:, 12:24].copy().view("<f4").reshape(-1, 3)
    rgba = rec[:, 24:28].copy()
    rot = rec[:, 28:32].copy()
    return xyz, scale, rgba, rot


def save_splat(path: Path, xyz: np.ndarray, scale: np.ndarray, rgba: np.ndarray, rot: np.ndarray) -> None:
    out = np.concatenate(
        [
            np.ascontiguousarray(xyz, dtype="<f4").view(np.uint8).reshape(-1, 12),
            np.ascontiguousarray(scale, dtype="<f4").view(np.uint8).reshape(-1, 12),
            rgba.astype(np.uint8).reshape(-1, 4),
            rot.astype(np.uint8).reshape(-1, 4),
        ],
        axis=1,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    out.reshape(-1).tofile(path)


def stats(name: str, xyz: np.ndarray, scale: np.ndarray, rgba: np.ndarray) -> None:
    smax = scale.max(axis=1)
    alpha = rgba[:, 3].astype(np.float32) / 255.0
    span = xyz.max(axis=0) - xyz.min(axis=0)
    print(
        f"  {name:10} 高斯 {len(xyz):>7,} | 尺度中位 {np.median(smax):.4f} / p95 {np.percentile(smax, 95):.4f}"
        f" | alpha 中位 {np.median(alpha):.2f}、<0.1 占 {(alpha < 0.1).mean() * 100:.1f}%"
        f" | 包围盒 {span[0]:.2f}×{span[1]:.2f}×{span[2]:.2f}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None, help="不填则只统计（等价 --dry-run）")
    ap.add_argument("--min-alpha", type=float, default=0.10, help="丢掉 alpha 低于此值的高斯（近乎透明）")
    ap.add_argument("--scale-k", type=float, default=6.0, help="丢掉最大尺度 > k×尺度中位数的高斯（大团子）")
    ap.add_argument("--clamp-scale-k", type=float, default=0.0, help="把最大尺度压到 k×中位数（0=不压）")
    ap.add_argument("--dist-pct", type=float, default=99.0, help="丢掉离中心超过该百分位距离的高斯（浮动点）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    xyz, scale, rgba, rot = load_splat(args.src)
    print(f"源文件：{args.src.name}（{args.src.stat().st_size / 1048576:.2f} MB）")
    stats("原始", xyz, scale, rgba)

    smax = scale.max(axis=1)
    alpha = rgba[:, 3].astype(np.float32) / 255.0
    keep = np.ones(len(xyz), dtype=bool)

    step = alpha >= args.min_alpha
    print(f"  ① alpha ≥ {args.min_alpha}: 保留 {step.sum():,} / {len(xyz):,}（丢 {len(xyz) - step.sum():,}）")
    keep &= step

    med = float(np.median(smax[keep])) if keep.any() else 0.0
    if args.scale_k > 0 and med > 0:
        step = smax <= args.scale_k * med
        print(f"  ② 最大尺度 ≤ {args.scale_k}×中位数({med:.4f}): 再丢 {(keep & ~step).sum():,}")
        keep &= step

    if len(xyz[keep]) > 100:
        centre = xyz[keep].mean(axis=0)
        dist = np.linalg.norm(xyz[keep] - centre, axis=1)
        thr = float(np.percentile(dist, args.dist_pct))
        step = dist <= thr
        print(f"  ③ 到中心距离 ≤ p{args.dist_pct}({thr:.3f}): 再丢 {(~step).sum():,}")
        idx = np.flatnonzero(keep)
        drop = idx[~step]
        keep[drop] = False

    xyz2, scale2, rgba2, rot2 = xyz[keep], scale[keep], rgba[keep], rot[keep]
    if args.clamp_scale_k > 0 and len(scale2):
        cap = args.clamp_scale_k * float(np.median(scale2.max(axis=1)))
        before = int((scale2.max(axis=1) > cap).sum())
        scale2 = np.minimum(scale2, cap)
        print(f"  ④ 把 {before:,} 个超大高斯压到 ≤ {cap:.4f}")

    stats("清理后", xyz2, scale2, rgba2)
    kept_pct = len(xyz2) / len(xyz) * 100
    print(f"  → 保留 {len(xyz2):,} / {len(xyz):,}（{kept_pct:.1f}%）")

    if args.dry_run or args.out is None:
        print("（未写文件；加 -o 输出路径即可落盘）")
        return 0
    save_splat(args.out, xyz2, scale2, rgba2, rot2)
    print(f"✅ 已写出：{args.out}（{args.out.stat().st_size / 1048576:.2f} MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
