#!/usr/bin/env python3
"""合成一组「多视角拍摄」当训练输入（离线、可复现、零下载）。

为什么要它：模块 8 要验证的是 **COLMAP → 3DGS → 导出 → 网页** 这条链路本身。
真实照片只有本人能拍，所以在照片到位前用这个脚本合成一组等价输入。

**纹理踩坑史（三次，别重复）**：
  v1 纯高频白噪声 1024x512 → 同一块纹理在不同视角下采样点全变，SIFT 没有稳定特征，
     COLMAP 40 张只注册 2 张。
  v2 多尺度分形噪声 + 棋盘地面 → 自相似 + 周期性太强，匹配到大量**错误**对应，
     RANSAC 全否掉，**依然只注册 2 张**。
  v3 **抖动网格 Voronoi 马赛克**（随机格色 + 暗色格边 + 少量高亮点）：每个格点唯一、
     边缘密集、完全没有周期性 —— 等价于摄影测量里贴满随机标记的标定板。

用法：
    python3 01_make_synthetic_capture.py --out ~/web3d/data/toy40 --views 40

产出：
    <out>/images/000.png …       给 COLMAP 的输入
    <out>/cameras.json           真实相机位姿（仅用于事后核对，不参与训练）
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

SPHERE_C = np.array([0.0, 0.25, 0.0])
SPHERE_R = 0.95
FLOOR_Y = -0.85
FLOOR_SIZE = 8.0
TILE_SCALE = 2.4          # 地面贴图的世界平铺周期
LIGHT_DIR = np.array([0.42, 0.78, 0.36])
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)

BACKDROP_R = 8.0           # 环绕背景球半径（把「天空」换成有纹理的面，否则 COLMAP 在背景上
                           # 一个特征点都没有，3DGS 永远重建不出那块区域，PSNR 会被它拖死）
FLOOR_TEX: np.ndarray | None = None   # 由 main 注入（避免层层传参）
BACKDROP_TEX: np.ndarray | None = None


def voronoi_mosaic(rng: np.random.Generator, size: int = 768, cells: int = 24,
                   saturation: float = 0.6) -> np.ndarray:
    """抖动网格 Voronoi 马赛克贴图（向量化实现）。

    每个像素只需要在「本格 + 8 邻格」的种子间比距离，所以整张图 9 次全图运算就够，
    不需要逐格 Python 循环。
    """
    block = size // cells
    assert block * cells == size, f"size({size}) 必须能被 cells({cells}) 整除"

    # 抖动网格种子（落在各自的格内）
    jitter = 0.42
    yy, xx = np.meshgrid(np.arange(cells), np.arange(cells), indexing="ij")
    cy = (yy + 0.5 + rng.uniform(-jitter, jitter, (cells, cells))) / cells
    cx = (xx + 0.5 + rng.uniform(-jitter, jitter, (cells, cells))) / cells
    colors = rng.random((cells * cells, 3)) * saturation + (1 - saturation) * 0.3

    v = (np.arange(size) + 0.5) / size
    py, px = np.meshgrid(v, v, indexing="ij")
    ci = np.minimum(np.arange(size) // block, cells - 1)
    cj = np.minimum(np.arange(size) // block, cells - 1)

    best = np.full((size, size), 1e9, dtype=np.float32)
    second = np.full((size, size), 1e9, dtype=np.float32)
    idx = np.zeros((size, size), dtype=np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sy = cy[(ci[:, None] + dy) % cells, (cj[None, :] + dx) % cells]
            sx = cx[(ci[:, None] + dy) % cells, (cj[None, :] + dx) % cells]
            d = (py - sy) ** 2 + (px - sx) ** 2
            hit = d < best
            second = np.where(hit, best, np.minimum(second, d))
            idx = np.where(hit, ((ci[:, None] + dy) % cells) * cells + (cj[None, :] + dx) % cells, idx)
            best = np.where(hit, d, best)

    rgb = colors[idx]
    # 格边压暗：到第二近种子只比最近种子远一点点 → 这是一条边界
    edge = (np.sqrt(second) - np.sqrt(best)) < 0.0025
    rgb = np.where(edge[..., None], rgb * 0.22, rgb)
    # 少量高亮点，让多尺度上都存在特征
    dots = rng.random((size, size)) > 0.9988
    rgb = np.where(dots[..., None], np.clip(rgb + 0.8, 0, 1), rgb)
    return np.clip(rgb, 0.03, 1.0).astype(np.float32)


def sample_tex(tex: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    h, w = tex.shape[:2]
    x = np.clip((u * w).astype(np.int32), 0, w - 1)
    y = np.clip((v * h).astype(np.int32), 0, h - 1)
    return tex[y, x]


def make_tiles(rng: np.random.Generator, n: int = 6) -> list[dict]:
    """地面上立着的平板：绕物体一圈，给平面上的稳定特征。"""
    tiles = []
    for k in range(n):
        ang = 2 * math.pi * k / n + rng.uniform(-0.25, 0.25)
        r = rng.uniform(1.7, 2.4)
        tiles.append(
            {
                "center": np.array([r * math.cos(ang), FLOOR_Y + 0.02, r * math.sin(ang)]),
                "sx": float(rng.uniform(0.9, 1.4)),
                "sz": float(rng.uniform(0.9, 1.4)),
                "yaw": float(rng.uniform(0, math.pi)),
                "uv_off": rng.random(2),
            }
        )
    return tiles


def render(width: int, height: int, fov_deg: float, eye: np.ndarray, target: np.ndarray,
           tex: np.ndarray, tiles: list[dict], rng: np.random.Generator) -> np.ndarray:
    fy = 0.5 * height / math.tan(math.radians(fov_deg) / 2)
    fx = fy
    cx, cy = width / 2.0, height / 2.0

    j, i = np.meshgrid(np.arange(width), np.arange(height))
    dx = (j - cx) / fx
    dy = -(i - cy) / fy
    dz = np.ones_like(dx)

    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
    right = right / np.linalg.norm(right)
    up = np.cross(right, forward)

    dirs = dx[..., None] * right + dy[..., None] * up + dz[..., None] * forward
    dirs = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)

    # 背景球（从内部看，取"出射"交点）
    oc = eye
    b = np.sum(dirs * oc, axis=-1)
    c = float(np.dot(oc, oc) - BACKDROP_R**2)
    disc = b * b - c
    color = np.zeros((height, width, 3), dtype=np.float32)
    depth = np.full((height, width), np.inf, dtype=np.float32)
    with np.errstate(invalid="ignore"):
        t_b = -b + np.sqrt(np.maximum(disc, 0))
    hitb = disc > 0
    if hitb.any():
        p = eye + dirs * t_b[..., None]
        n = (p - np.array([0.0, 0.0, 0.0])) / BACKDROP_R
        u = (np.arctan2(n[..., 2], n[..., 0]) / (2 * math.pi)) % 1.0
        v = (np.arccos(np.clip(n[..., 1], -1, 1)) / math.pi)
        texb = BACKDROP_TEX if BACKDROP_TEX is not None else tex
        base = sample_tex(texb, (u * 3) % 1.0, (v * 3) % 1.0)
        shade = np.clip(n @ LIGHT_DIR, 0, 1)[..., None]
        color = np.where(hitb[..., None], np.clip(base * (0.45 + 0.55 * shade), 0, 1), color)
        depth = np.where(hitb, t_b, depth)

    # ---- 地面（平铺 Voronoi）----
    with np.errstate(divide="ignore", invalid="ignore"):
        t_p = (FLOOR_Y - eye[1]) / dirs[..., 1]
    hit = (t_p > 1e-4) & np.isfinite(t_p)
    if hit.any():
        p = eye + dirs * t_p[..., None]
        mask = hit & (np.abs(p[..., 0]) < FLOOR_SIZE) & (np.abs(p[..., 2]) < FLOOR_SIZE)
        if mask.any():
            floor = FLOOR_TEX if FLOOR_TEX is not None else tex
            u = ((p[..., 0] / TILE_SCALE) % 1.0).astype(np.float32)
            v = ((p[..., 2] / TILE_SCALE) % 1.0).astype(np.float32)
            color[mask] = sample_tex(floor, u[mask], v[mask]) * 0.92
            depth[mask] = t_p[mask]

    # ---- 地面平板 ----
    for tile in tiles:
        with np.errstate(divide="ignore", invalid="ignore"):
            t_t = (tile["center"][1] - eye[1]) / dirs[..., 1]
        hit_t = (t_t > 1e-4) & np.isfinite(t_t) & (t_t < depth)
        if not hit_t.any():
            continue
        p = eye + dirs * t_t[..., None]
        rel = p - tile["center"]
        ca, sa = math.cos(-tile["yaw"]), math.sin(-tile["yaw"])
        u = rel[..., 0] * ca - rel[..., 2] * sa
        v = rel[..., 0] * sa + rel[..., 2] * ca
        m = hit_t & (np.abs(u) < tile["sx"] / 2) & (np.abs(v) < tile["sz"] / 2)
        if m.any():
            uu = (u[m] / tile["sx"] + 0.5 + tile["uv_off"][0]) % 1.0
            vv = (v[m] / tile["sz"] + 0.5 + tile["uv_off"][1]) % 1.0
            shade = 0.62 + 0.38 * max(float(LIGHT_DIR[1]), 0.0)
            color[m] = np.clip(sample_tex(tex, uu, vv) * shade, 0, 1)
            depth[m] = t_t[m]

    # ---- 球 ----
    oc = eye - SPHERE_C
    b = np.sum(dirs * oc, axis=-1)
    c = float(np.dot(oc, oc) - SPHERE_R**2)
    disc = b * b - c
    cand = disc > 0
    if cand.any():
        t_s = -b[cand] - np.sqrt(disc[cand])
        idx = np.where(cand)
        ok = (t_s > 1e-4) & (t_s < depth[idx])
        idx = (idx[0][ok], idx[1][ok])
        t_s = t_s[ok]
        p = eye + dirs[idx] * t_s[:, None]
        n = (p - SPHERE_C) / SPHERE_R
        u = (np.arctan2(n[:, 2], n[:, 0]) / (2 * math.pi)) % 1.0
        v = np.arccos(np.clip(n[:, 1], -1, 1)) / math.pi
        base = sample_tex(tex, (u * 2) % 1.0, (v * 2) % 1.0)
        shade = np.clip(n @ LIGHT_DIR, 0, 1)[:, None]
        color[idx] = np.clip(base * (0.34 + 0.86 * shade), 0, 1)
        depth[idx] = t_s

    color = np.clip(color + rng.normal(0, 0.005, color.shape), 0, 1)
    return (color ** (1 / 2.2) * 255).astype(np.uint8)


def main() -> int:
    global FLOOR_TEX, BACKDROP_TEX
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", type=int, default=40)
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--height", type=int, default=675)
    ap.add_argument("--fov", type=float, default=52.0)
    ap.add_argument("--distance", type=float, default=3.1)
    ap.add_argument("--elevation", type=float, default=26.0)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--save-texture", action="store_true", help="顺便把贴图存出来看")
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    (out / "images").mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    tex = voronoi_mosaic(rng, size=768, cells=24)        # 物体 / 平板（768/24=32）
    FLOOR_TEX = voronoi_mosaic(rng, size=768, cells=48)    # 地面（不同密度；768/48=16 整除）
    BACKDROP_TEX = voronoi_mosaic(rng, size=768, cells=16)  # 背景球（更粗的格子，远看也稳）
    tiles = make_tiles(rng)
    if args.save_texture:
        Image.fromarray((tex ** (1 / 2.2) * 255).astype(np.uint8)).save(out / "texture.png")
        Image.fromarray((FLOOR_TEX ** (1 / 2.2) * 255).astype(np.uint8)).save(out / "texture_floor.png")

    target = np.array([0.0, 0.0, 0.0])
    poses = []
    means = []
    for k in range(args.views):
        az = 2 * math.pi * k / args.views
        el = math.radians(args.elevation)
        eye = np.array(
            [
                args.distance * math.cos(el) * math.cos(az),
                args.distance * math.sin(el) + 0.2,
                args.distance * math.cos(el) * math.sin(az),
            ]
        )
        img = render(args.width, args.height, args.fov, eye, target, tex, tiles, rng)
        name = f"{k:03d}.png"
        Image.fromarray(img).save(out / "images" / name)
        poses.append({"image": name, "eye": [float(x) for x in eye]})
        means.append(float(img.mean()))
        if k % 10 == 0:
            print(f"  {name} 亮度均值 {img.mean():.1f}")

    (out / "cameras.json").write_text(
        json.dumps(
            {
                "note": "合成捕获 v3：Voronoi 马赛克纹理球 + 同纹理地面 + 6 块平板，环绕视角，针孔相机",
                "views": args.views,
                "width": args.width,
                "height": args.height,
                "fov_deg": args.fov,
                "mean_brightness": round(float(np.mean(means)), 2),
                "poses": poses,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n完成：{args.views} 张 {args.width}x{args.height} -> {out/'images'}"
          f"（平均亮度 {np.mean(means):.1f}，不为 0 说明图确实渲染出来了）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
