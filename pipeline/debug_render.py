#!/usr/bin/env python3
"""debug_render.py —— 一击定位：用初始高斯渲染训练视角，和原图并排存 PNG。

渲染出来若是"灰团" → 相机/内参/归一化/渲染调用这条链路有错（两版共用）
渲染出能看出鞋 → 链路没错，问题在优化环节
"""
import argparse
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import torch
from PIL import Image

_PIPE = Path(__file__).resolve().parent
_spec = spec_from_file_location("t03", _PIPE / "03_train_gsplat.py")
t03 = module_from_spec(_spec); _spec.loader.exec_module(t03)
_v2spec = spec_from_file_location("tv2", _PIPE / "03_train_gsplat_v2.py")
v2 = module_from_spec(_v2spec); _v2spec.loader.exec_module(v2)

from gsplat import rasterization  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--down", type=int, default=4)
ap.add_argument("--view", type=int, default=0)
ap.add_argument("--out", default="/mnt/d/lab/web3d-lab/work/debug_render")
ap.add_argument("--raw-scales", action="store_true",
                help="【仅 A/B 复现历史 bug】把未 exp() 激活的 log 尺度直接喂给 rasterization")
args = ap.parse_args()
scale_mode = "raw" if args.raw_scales else "exp"

DEV = "cuda" if torch.cuda.is_available() else "cpu"
data = Path(args.data); sparse = data / "sparse" / "0"
cameras, images, pts_xyz, pts_rgb = t03.read_colmap_txt(sparse)
print(f"视角 {len(images)} | 稀疏点 {len(pts_xyz)}")

views, shapes = [], []
for im in images:
    img = Image.open(data / "images" / im["name"]).convert("RGB")
    w, h = img.size
    if args.down > 1:
        img = img.resize((w // args.down, h // args.down), Image.LANCZOS)
    views.append(img)
H, W = views[0].size[1], views[0].size[0]
print(f"分辨率 {W}x{H}")

viewmats, Ks = [], []
for im in images:
    cam = cameras[im["cam_id"]]
    R = t03.qvec_to_rotmat(im["qvec"]).astype(np.float32)
    t = im["tvec"].reshape(3, 1).astype(np.float32)
    vm = np.concatenate([np.concatenate([R, t], axis=1), np.array([[0, 0, 0, 1]], np.float32)], axis=0)
    viewmats.append(vm)
    s = args.down
    Ks.append(np.array([[cam["fx"]/s, 0, cam["cx"]/s], [0, cam["fy"]/s, cam["cy"]/s], [0, 0, 1]], np.float32))
viewmats = torch.tensor(np.stack(viewmats), device=DEV)
Ks = torch.tensor(np.stack(Ks), device=DEV)

cam_t = viewmats[:, :3, 3].cpu().numpy()
pts_all = np.concatenate([pts_xyz, cam_t])
radius = float(np.linalg.norm(pts_all - pts_all.mean(0), axis=1).max())
s = 1.5 / max(radius, 1e-6)
viewmats[:, :3, 3] *= s
pts_xyz_n = pts_xyz * s
print(f"归一化 半径 {radius:.2f} -> 1.5 (系数 {s:.4f})")
_cc = (-viewmats[:, :3, :3].transpose(1, 2) @ viewmats[:, :3, 3:4]).cpu().numpy().reshape(-1, 3)
print(f"归一化后 点云跨度 {np.linalg.norm(pts_xyz_n.max(0)-pts_xyz_n.min(0)):.4f}"
      f" | 相机中心到原点距离 中位 {np.median(np.linalg.norm(_cc, axis=1)):.3f}"
      f" | 相机中心跨度 {np.linalg.norm(_cc.max(0)-_cc.min(0)):.3f}")

params = v2.build_params(pts_xyz_n, pts_rgb)
i = args.view
print(f"尺度激活：{scale_mode}")
with torch.no_grad():
    colors = torch.cat([params["sh0"], params["shN"]], dim=1)
    r, a, _ = rasterization(params["means"], params["quats"],
                            v2.activated_scales(params, scale_mode),
                            torch.sigmoid(params["opacities"]).squeeze(-1), colors,
                            viewmats[i:i+1], Ks[i:i+1], W, H, sh_degree=3, packed=False)
    img = (r[0].clamp(0, 1) * 255).byte().cpu().numpy()
    alpha = (a[0, ..., 0].clamp(0, 1) * 255).byte().cpu().numpy()
gt = np.asarray(views[i], dtype=np.uint8)

print(f"\n视角 {i}（{images[i]['name']}）")
print(f"  渲染图 均值 RGB {img.reshape(-1,3).mean(0).round(1)}  标准差 {img.reshape(-1,3).std(0).round(1)}")
print(f"  原  图 均值 RGB {gt.reshape(-1,3).mean(0).round(1)}  标准差 {gt.reshape(-1,3).std(0).round(1)}")
print(f"  alpha>0.5 的像素占比 {(alpha>128).mean()*100:.1f}%")
mse = float(((img.astype(np.float32)/255 - gt.astype(np.float32)/255)**2).mean())
print(f"  初始渲染 vs 原图的 PSNR {10*np.log10(1/max(mse,1e-12)):.2f} dB")

out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
Image.fromarray(img).save(out / "init_render.png")
Image.fromarray(alpha).save(out / "init_alpha.png")
Image.fromarray(gt).save(out / "gt.png")
side = np.concatenate([img, gt], axis=1)
Image.fromarray(side).save(out / "side_by_side.png")
print(f"\n已存：{out}/side_by_side.png（左=初始渲染 右=原图）、init_alpha.png")
