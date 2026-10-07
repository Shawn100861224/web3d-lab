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


def center_of_mass(xyz: np.ndarray, refine: bool = True) -> np.ndarray:
    """估物体中心：先用全体中位点，再用「离它最近的 60% 点」重新算一次。

    为什么要 refine：整体中位点会被那一圈糊背景往旁边拽；迭代一次就能落到物体本体上。
    """
    c = np.median(xyz, axis=0)
    if not refine:
        return c
    d = np.linalg.norm(xyz - c, axis=1)
    core = xyz[d <= np.percentile(d, 60)]
    return np.median(core, axis=0) if len(core) > 50 else c


def neighbor_counts(xyz: np.ndarray, radius: float) -> np.ndarray:
    """数每个高斯在给定半径内的邻居数（用体素网格做，避免 O(n²)）。

    孤立点（邻居很少）几乎都是浮动点；连贯表面的高斯邻居很多。这是"保留清晰部分"最贴切的一条判据 ——
    比按尺度/透明度硬筛更稳，因为它看的是**局部结构**，不是单个高斯的属性。
    """
    cell = float(radius)
    keys = np.floor(xyz / cell).astype(np.int64)
    grid: dict[tuple[int, int, int], int] = {}
    for k in map(tuple, keys):
        grid[k] = grid.get(k, 0) + 1

    offsets = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    counts = np.empty(len(xyz), dtype=np.int64)
    for i, k in enumerate(map(tuple, keys)):
        total = 0
        for dx, dy, dz in offsets:
            total += grid.get((k[0] + dx, k[1] + dy, k[2] + dz), 0)
        counts[i] = total - 1  # 减去自己
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None, help="不填则只统计（等价 --dry-run）")
    ap.add_argument("--min-alpha", type=float, default=0.10, help="丢掉 alpha 低于此值的高斯（近乎透明）")
    ap.add_argument("--scale-k", type=float, default=6.0, help="丢掉最大尺度 > k×尺度中位数的高斯（大团子）")
    ap.add_argument("--clamp-scale-k", type=float, default=0.0, help="把最大尺度压到 k×中位数（0=不压）")
    ap.add_argument("--dist-pct", type=float, default=99.0, help="丢掉离中心超过该百分位距离的高斯（浮动点）")
    ap.add_argument("--keep-radius", type=float, default=0.0, help="只保留离物体中心该半径内的内容（0=不裁）")
    ap.add_argument("--fade-to", type=float, default=0.0, help="从 keep-radius 到该半径之间把 alpha 线性衰减到 0")
    ap.add_argument("--neighbor-radius", type=float, default=0.0, help="密度过滤的邻域半径（世界单位，0=不做密度过滤）")
    ap.add_argument("--min-neighbors", type=int, default=4, help="邻域内少于该数量的高斯视为孤立点丢掉")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    xyz, scale, rgba, rot = load_splat(args.src)
    print(f"源文件：{args.src.name}（{args.src.stat().st_size / 1048576:.2f} MB）")
    stats("原始", xyz, scale, rgba)

    smax = scale.max(axis=1)
    alpha = rgba[:, 3].astype(np.float32) / 255.0
    keep = np.ones(len(xyz), dtype=bool)
    ran_crop = False

    # ① 半径裁切 + 透明度衰减（先做，后面的尺度统计就只反映物体本体）
    if args.keep_radius > 0:
        ran_crop = True
        centre = center_of_mass(xyz)
        fade_to = args.fade_to if args.fade_to > args.keep_radius else args.keep_radius * 1.4
        dist = np.linalg.norm(xyz - centre, axis=1)
        weight = np.clip((fade_to - dist) / (fade_to - args.keep_radius), 0.0, 1.0)
        outside = int((dist > fade_to).sum())
        faded = int(((dist > args.keep_radius) & (dist <= fade_to)).sum())
        keep &= dist <= fade_to
        alpha = alpha * weight
        print(f"  ① 裁切：中心 {centre.round(3)}，保留半径 {args.keep_radius}→淡出 {fade_to:.2f}")
        print(f"     直接丢掉（超出淡出半径）{outside:,} 个；渐隐 {faded:,} 个；保留 {int(keep.sum()):,} 个")
        print(f"     圆形边界（r={args.keep_radius}）内的尺度中位 {np.median(smax[dist <= args.keep_radius]):.4f}")

    # ② 密度过滤：丢掉孤立点（周围邻居太少的）
    if args.neighbor_radius > 0:
        counts = neighbor_counts(xyz, args.neighbor_radius)
        step = counts >= args.min_neighbors
        kept_n = int(keep.sum())
        dropped_n = int((keep & ~step).sum())
        print(
            f"  ② 密度：半径 {args.neighbor_radius} 内邻居 ≥ {args.min_neighbors}"
            f"（当前候选 {kept_n:,} 个中丢 {dropped_n:,} 个孤立点；"
            f"邻居数中位 {int(np.median(counts[keep]))}）"
        )
        keep &= step

    step = alpha >= args.min_alpha
    print(f"  ③ alpha ≥ {args.min_alpha}: 保留 {step.sum():,} / {len(xyz):,}（丢 {len(xyz) - step.sum():,}）")
    keep &= step

    med = float(np.median(smax[keep])) if keep.any() else 0.0
    if args.scale_k > 0 and med > 0:
        step = smax <= args.scale_k * med
        print(f"  ④ 最大尺度 ≤ {args.scale_k}×中位数({med:.4f}): 再丢 {(keep & ~step).sum():,}")
        keep &= step

    if len(xyz[keep]) > 100 and not ran_crop:
        centre = xyz[keep].mean(axis=0)
        dist = np.linalg.norm(xyz[keep] - centre, axis=1)
        thr = float(np.percentile(dist, args.dist_pct))
        step = dist <= thr
        print(f"  ⑤ 到中心距离 ≤ p{args.dist_pct}({thr:.3f}): 再丢 {(~step).sum():,}")
        idx = np.flatnonzero(keep)
        keep[idx[~step]] = False

    xyz2, scale2, rot2 = xyz[keep], scale[keep], rot[keep]
    alpha2 = np.clip(alpha[keep], 0.0, 1.0)
    rgba2 = rgba[keep].copy()
    rgba2[:, 3] = (alpha2 * 255).round().astype(np.uint8)

    if args.clamp_scale_k > 0 and len(scale2):
        cap = args.clamp_scale_k * float(np.median(scale2.max(axis=1)))
        before = int((scale2.max(axis=1) > cap).sum())
        scale2 = np.minimum(scale2, cap)
        print(f"  ⑤ 把 {before:,} 个超大高斯压到 ≤ {cap:.4f}")

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
