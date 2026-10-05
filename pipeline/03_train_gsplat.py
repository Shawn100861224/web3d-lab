#!/usr/bin/env python3
"""03 —— 用 gsplat 的 CUDA 光栅化核训练 3DGS（自写精简版）。

为什么不用 gsplat 仓库里的 examples/simple_trainer.py：它的源码包在本机反复下载被截断，
而且拖着 tyro / viser / torchmetrics / fused-ssim 一堆依赖。这条链路的目的是「跑通」，
所以这里只依赖 torch + gsplat + numpy + Pillow，把 3DGS 的核心（可微光栅化 + 稠密化 +
SH 渐进升阶）自己写清楚，指标与导出都自己控制。

    python 03_train_gsplat.py --data ~/web3d/data/toy40 --steps 7000 --sh-degree 3

产出：
    <data>/train/ckpt_<steps>.ply      标准 3DGS PLY（Spark 可直接加载）
    <data>/train/metrics.json          训练耗时 / 显存峰值 / PSNR（含留出视角）
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

try:
    from gsplat import rasterization, export_splats
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "gsplat 未安装或导入失败（需要先 source ~/web3d/env-gs.sh 让 CUDA_HOME 指向拼装好的工具链）"
    ) from exc


# --------------------------------------------------------------------------- #
# COLMAP 文本模型解析（02 脚本已用 model_converter 转成 TXT）
# --------------------------------------------------------------------------- #

def read_colmap_txt(sparse_dir: Path) -> tuple[dict, list[dict], np.ndarray, np.ndarray]:
    cameras: dict[int, dict] = {}
    for line in (sparse_dir / "cameras.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        cam_id = int(parts[0])
        model = parts[1]
        w, h = int(parts[2]), int(parts[3])
        params = [float(x) for x in parts[4:]]
        if model == "OPENCV":
            fx, fy, cx, cy = params[:4]
        elif model in ("PINHOLE", "SIMPLE_PINHOLE"):
            if model == "PINHOLE":
                fx, fy, cx, cy = params[:4]
            else:
                fx = fy = params[0]
                cx, cy = params[1], params[2]
        else:  # RADIAL / 其它：取前四个当 fx,fy,cx,cy
            fx, fy, cx, cy = params[:4]
        cameras[cam_id] = {"w": w, "h": h, "fx": fx, "fy": fy, "cx": cx, "cy": cy}

    # 流式读：Mip-NeRF 360 的 images.txt 有 ~100 MB，read_text().splitlines() 会把
    # 它展开成几百 MB 的 Python 字符串列表，WSL 里内存一紧张 GPU 分配就失败（踩过）。
    images: list[dict] = []
    with (sparse_dir / "images.txt").open(encoding="utf-8") as fh:
        idx = -1
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            idx += 1
            if idx % 2 == 1:  # 偶数行是 2D 观测，跳过
                continue
            parts = line.split()
            # 必须显式 float32：np.array([float(x)…]) 默认是 float64，
            # 拼进 viewmat 后会整块变 double，gsplat 的 CUDA 核直接报
            # "expected scalar type Float but found Double"。
            qvec = np.array([float(x) for x in parts[1:5]], dtype=np.float32)  # w x y z
            tvec = np.array([float(x) for x in parts[5:8]], dtype=np.float32)
            cam_id = int(parts[8])
            name = parts[9]
            images.append({"qvec": qvec, "tvec": tvec, "cam_id": cam_id, "name": name})

    xyz, rgb = [], []
    with (sparse_dir / "points3D.txt").open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
            rgb.append([int(parts[4]), int(parts[5]), int(parts[6])])
    return cameras, images, np.array(xyz, dtype=np.float32), np.array(rgb, dtype=np.uint8)


def qvec_to_rotmat(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * w * z, 2 * x * z + 2 * w * y],
            [2 * x * y + 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * w * x],
            [2 * x * z - 2 * w * y, 2 * y * z + 2 * w * x, 1 - 2 * x * x - 2 * y * y],
        ],
        dtype=np.float32,
    )


# --------------------------------------------------------------------------- #
# 损失 / 指标
# --------------------------------------------------------------------------- #

def ssim_simple(a: torch.Tensor, b: torch.Tensor, window: int = 11) -> torch.Tensor:
    """可微 SSIM（高斯窗，通道平均）。用不到 torchvision/metrics 的额外依赖。"""
    coords = torch.arange(window, dtype=a.dtype, device=a.device) - window // 2
    g = torch.exp(-(coords**2) / (2 * 1.5**2))
    g = (g / g.sum()).view(1, 1, 1, window)
    pad = window // 2
    mu_a = F.conv2d(a, g.expand(3, 1, 1, window), padding=(0, pad), groups=3)
    mu_a = F.conv2d(mu_a, g.transpose(-1, -2).expand(3, 1, window, 1), padding=(pad, 0), groups=3)
    mu_b = F.conv2d(b, g.expand(3, 1, 1, window), padding=(0, pad), groups=3)
    mu_b = F.conv2d(mu_b, g.transpose(-1, -2).expand(3, 1, window, 1), padding=(pad, 0), groups=3)
    sigma_a = F.conv2d(a * a, g.expand(3, 1, 1, window), padding=(0, pad), groups=3)
    sigma_a = F.conv2d(sigma_a, g.transpose(-1, -2).expand(3, 1, window, 1), padding=(pad, 0), groups=3) - mu_a**2
    sigma_b = F.conv2d(b * b, g.expand(3, 1, 1, window), padding=(0, pad), groups=3)
    sigma_b = F.conv2d(sigma_b, g.transpose(-1, -2).expand(3, 1, window, 1), padding=(pad, 0), groups=3) - mu_b**2
    sigma_ab = F.conv2d(a * b, g.expand(3, 1, 1, window), padding=(0, pad), groups=3)
    sigma_ab = F.conv2d(sigma_ab, g.transpose(-1, -2).expand(3, 1, window, 1), padding=(pad, 0), groups=3) - mu_a * mu_b
    c1, c2 = 0.01**2, 0.03**2
    s = ((2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)) / ((mu_a**2 + mu_b**2 + c1) * (sigma_a + sigma_b + c2))
    return s.mean()


def psnr(a: torch.Tensor, b: torch.Tensor) -> float:
    mse = F.mse_loss(a.clamp(0, 1), b.clamp(0, 1))
    return float(10 * torch.log10(1.0 / mse.clamp_min(1e-12)))


def rgb_to_sh_dc(rgb: torch.Tensor) -> torch.Tensor:
    return (rgb - 0.5) / 0.28209479177387814


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="COLMAP 数据集目录（含 images/ 与 sparse/0/）")
    ap.add_argument("--steps", type=int, default=7000)
    ap.add_argument("--sh-degree", type=int, default=3)
    ap.add_argument("--holdout", type=int, default=4, help="留出多少个视角只做评估")
    ap.add_argument("--down", type=int, default=2, help="图像降采样倍数（8GB 显存建议 2）")
    ap.add_argument("--max-splats", type=int, default=300_000,
                    help="稠密化后的高斯数上限（8GB 显存建议 30–80 万）")
    ap.add_argument("--max-init-points", type=int, default=0,
                    help="初始化点数上限（0=全部）。公开数据集的稀疏点云常有几十万点，"
                         "随机下采样可以控制显存与首轮耗时")
    ap.add_argument("--lr-pos", type=float, default=1.6e-4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    data = Path(args.data).expanduser()
    sparse = data / "sparse" / "0"
    out_dir = data / "train"
    out_dir.mkdir(parents=True, exist_ok=True)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"设备：{dev}  |  gsplat 训练步数：{args.steps}  |  SH：{args.sh_degree}")

    if not (sparse / "cameras.txt").exists():
        raise SystemExit(
            f"❌ {sparse} 里没有 TXT 模型（只有 .bin）。"
            "跑一下： colmap model_converter --input_path <sparse/0> --output_path <sparse/0> --output_type TXT"
        )
    cameras, images, pts_xyz, pts_rgb = read_colmap_txt(sparse)
    print(f"COLMAP：{len(images)} 个视角 / {len(pts_xyz)} 个稀疏点")

    # ---- 读图（降采样） ----
    views = []
    for im in images:
        img = Image.open(data / "images" / im["name"]).convert("RGB")
        w, h = img.size
        if args.down > 1:
            img = img.resize((w // args.down, h // args.down), Image.LANCZOS)
        views.append(
            {
                # 刻意留在 CPU 且用 uint8：232 张以 float32 常驻要 ~750MB，
                # uint8 只要 ~190MB（用时再转 float）。WDDM 下系统内存紧张会直接
                # 导致 GPU 分配失败，所以这里省的不只是内存。
                "image": torch.from_numpy(np.asarray(img, dtype=np.uint8)),
                "name": im["name"],
            }
        )
    H, W = views[0]["image"].shape[:2]
    print(f"训练分辨率：{W}x{H}（原图 {cameras[images[0]['cam_id']]['w']}x"
          f"{cameras[images[0]['cam_id']]['h']}，降采样 x{args.down}）")

    # ---- 相机 ----
    viewmats = []
    Ks = []
    for im, v in zip(images, views):
        cam = cameras[im["cam_id"]]
        R = qvec_to_rotmat(im["qvec"])
        t = im["tvec"].reshape(3, 1)
        vm = np.concatenate([R, t], axis=1)  # x_cam = R x_world + t
        viewmats.append(np.concatenate([vm, np.array([[0, 0, 0, 1]], np.float32)], axis=0))
        s = args.down
        Ks.append(
            np.array(
                [
                    [cam["fx"] / s, 0, cam["cx"] / s],
                    [0, cam["fy"] / s, cam["cy"] / s],
                    [0, 0, 1],
                ],
                dtype=np.float32,
            )
        )
    viewmats = torch.from_numpy(np.stack(viewmats)).to(dev).float()
    Ks = torch.from_numpy(np.stack(Ks)).to(dev).float()

    # 防御性检查：gsplat 的 CUDA 核只吃 float32，混进 double 会以一句
    # "expected scalar type Float but found Double" 结束，不给任何线索。
    for _name, _t in (("viewmats", viewmats), ("Ks", Ks)):
        if _t.dtype != torch.float32:
            raise SystemExit(f"❌ {_name} 是 {_t.dtype}，gsplat 只接受 float32")

    # ---- 场景归一化：COLMAP 的尺度是任意的，直接拿真实尺度套标准学习率会让位置几乎不动。
    # 把所有平移（点 + 相机）缩放到「场景半径 ≈ 1.5」，超参就能用通行的那套。
    cam_t = viewmats[:, :3, 3]
    pts_all = np.concatenate([pts_xyz, cam_t.cpu().numpy()])
    scene_radius = float(np.linalg.norm(pts_all - pts_all.mean(0), axis=1).max())
    scale_factor = 1.5 / max(scene_radius, 1e-6)
    viewmats[:, :3, 3] *= scale_factor
    pts_xyz = pts_xyz * scale_factor
    print(f"场景归一化：半径 {scene_radius:.2f} -> 1.5（缩放系数 {scale_factor:.4f}）")

    n_train = len(views) - args.holdout
    train_idx = list(range(n_train))
    test_idx = list(range(n_train, len(views)))
    print(f"训练视角 {len(train_idx)} / 留出评估视角 {len(test_idx)}（{[views[i]['name'] for i in test_idx]}）")

    # ---- 初始化高斯（来自稀疏点云，必要时下采样控显存） ----
    if args.max_init_points and len(pts_xyz) > args.max_init_points:
        sel = np.random.default_rng(args.seed).choice(len(pts_xyz), args.max_init_points, replace=False)
        print(f"初始点云下采样：{len(pts_xyz)} → {len(sel)}（--max-init-points）")
        pts_xyz, pts_rgb = pts_xyz[sel], pts_rgb[sel]
    means = torch.from_numpy(pts_xyz).to(dev).requires_grad_(True)
    n = means.shape[0]
    diag = float(np.linalg.norm(pts_xyz.max(0) - pts_xyz.min(0)))
    init_scale = diag / math.sqrt(max(n, 1)) * 1.5
    scales = torch.full((n, 3), math.log(init_scale), device=dev).requires_grad_(True)
    quats = torch.zeros((n, 4), device=dev)
    quats[:, 0] = 1.0
    quats.requires_grad_(True)
    # gsplat 的 rasterization 要求 opacities 形状是 (N,)，不是 (N,1)
    opac_raw = torch.full((n,), -1.0, device=dev).requires_grad_(True)  # sigmoid(-1)=0.27
    sh_dc = rgb_to_sh_dc(torch.from_numpy(pts_rgb.astype(np.float32) / 255.0).to(dev)).unsqueeze(1)
    K_sh = (args.sh_degree + 1) ** 2
    sh_rest = torch.zeros((n, K_sh - 1, 3), device=dev)
    sh = torch.cat([sh_dc, sh_rest], dim=1).requires_grad_(True)

    params = [
        {"params": [means], "lr": args.lr_pos, "name": "means"},
        {"params": [scales], "lr": 5e-3, "name": "scales"},
        {"params": [quats], "lr": 1e-3, "name": "quats"},
        {"params": [opac_raw], "lr": 5e-2, "name": "opacity"},
        {"params": [sh], "lr": 2.5e-3, "name": "sh"},
    ]
    opt = torch.optim.Adam(params, eps=1e-15, betas=(0.9, 0.999))

    grad_acc = torch.zeros(n, device=dev)
    densify_from, densify_until = 500, int(args.steps * 0.6)
    sh_deg_schedule = [(0, 1000), (3, 2000)]  # 到 1000 步升 1 阶，到 2000 步升满

    if dev == "cuda":
        torch.cuda.reset_peak_memory_stats()

    t0 = time.time()
    log = []
    for step in range(1, args.steps + 1):
        cur_deg = args.sh_degree
        for thresh, deg in sh_deg_schedule:
            if step < thresh and deg < cur_deg:
                cur_deg = deg
        idx = torch.randint(0, len(train_idx), (1,)).item()
        cam = train_idx[idx]
        gt = views[cam]["image"].permute(2, 0, 1).unsqueeze(0).to(dev).float() / 255.0

        colors = sh[:, : (cur_deg + 1) ** 2, :]
        renders, alphas, meta = rasterization(
            means, quats, scales, torch.sigmoid(opac_raw), colors,
            viewmats[cam : cam + 1], Ks[cam : cam + 1], W, H,
            sh_degree=cur_deg,
        )
        # gsplat 返回 (C, H, W, 3)；转成 (C, 3, H, W) 才能和 gt 比对
        img = renders[0].permute(2, 0, 1).unsqueeze(0)
        loss = 0.8 * F.l1_loss(img, gt) + 0.2 * (1 - ssim_simple(img, gt))
        opt.zero_grad(set_to_none=True)
        loss.backward()

        with torch.no_grad():
            if step >= densify_from:
                grad_acc[: means.shape[0]] += torch.linalg.vector_norm(means.grad, dim=-1)
            if step % 100 == 0:
                log.append({"step": step, "loss": float(loss.item()), "splats": int(means.shape[0]),
                            "psnr_train": psnr(img.detach(), gt), "sh_degree": cur_deg})
                print(f"  step {step:5d} | loss {loss.item():.4f} | splats {means.shape[0]:6d} "
                      f"| train PSNR {psnr(img.detach(), gt):5.2f} | SH{cur_deg}")

        opt.step()

        # ---- 稠密化（clone / split / prune）+ 不透明度周期重置 ----
        # 对齐 Inria 3DGS 的做法，但阈值按「归一化场景（半径≈1.5）」取：
        #   clone：梯度大的小高斯原地复制一份
        #   split：梯度大的大高斯裂成两个（位置抖动、尺度 ÷1.6）
        #   prune：不透明度 < 0.005 或尺度过大的漂浮物直接删
        # 每 3000 步把所有不透明度压回 0.01，逼着系统重新决定谁该留下。
        if step % 3000 == 0 and step < args.steps:
            with torch.no_grad():
                opac_raw.data.fill_(-4.595)  # sigmoid(-4.595) ≈ 0.01

        if densify_from <= step <= densify_until and step % 100 == 0:
            with torch.no_grad():
                grads = grad_acc / 100.0                      # 区间内平均梯度模长
                grad_acc.zero_()
                max_scale = torch.exp(scales).max(dim=-1).values
                densify_mask = grads >= 2e-4
                split_mask = densify_mask & (max_scale > 0.015)
                clone_mask = densify_mask & ~split_mask

                new_means, new_scales, new_quats, new_opac, new_sh = [], [], [], [], []
                if bool(clone_mask.any()):
                    new_means.append(means[clone_mask].detach())
                    new_scales.append(scales[clone_mask].detach())
                    new_quats.append(quats[clone_mask].detach())
                    new_opac.append(opac_raw[clone_mask].detach())
                    new_sh.append(sh[clone_mask].detach())
                if bool(split_mask.any()):
                    for _ in range(2):
                        m = means[split_mask].detach()
                        jitter = torch.randn_like(m) * torch.exp(scales[split_mask].detach())
                        new_means.append(m + jitter)
                        new_scales.append(scales[split_mask].detach() - math.log(1.6))
                        new_quats.append(quats[split_mask].detach())
                        new_opac.append(opac_raw[split_mask].detach())
                        new_sh.append(sh[split_mask].detach())

                keep = (torch.sigmoid(opac_raw) > 0.005) & (max_scale < 0.15)
                cap = args.max_splats
                idx_keep = torch.nonzero(keep).squeeze(-1)
                if idx_keep.shape[0] > cap:
                    # 超上限时按不透明度保留最"实"的那些
                    order = torch.argsort(torch.sigmoid(opac_raw[idx_keep]), descending=True)
                    idx_keep = idx_keep[order[:cap]]
                if new_means or idx_keep.shape[0] != means.shape[0]:
                    means = torch.nn.Parameter(torch.cat([means[idx_keep].detach()] + new_means))
                    scales = torch.nn.Parameter(torch.cat([scales[idx_keep].detach()] + new_scales))
                    quats = torch.nn.Parameter(torch.cat([quats[idx_keep].detach()] + new_quats))
                    opac_raw = torch.nn.Parameter(torch.cat([opac_raw[idx_keep].detach()] + new_opac))
                    sh = torch.nn.Parameter(torch.cat([sh[idx_keep].detach()] + new_sh))
                    grad_acc = torch.zeros(means.shape[0], device=dev)
                    opt = torch.optim.Adam(
                        [
                            {"params": [means], "lr": args.lr_pos},
                            {"params": [scales], "lr": 5e-3},
                            {"params": [quats], "lr": 1e-3},
                            {"params": [opac_raw], "lr": 5e-2},
                            {"params": [sh], "lr": 2.5e-3},
                        ],
                        eps=1e-15,
                        betas=(0.9, 0.999),
                    )

    train_seconds = round(time.time() - t0, 1)
    peak_mb = round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1) if dev == "cuda" else 0.0

    # ---- 留出视角评估 ----
    # 本机（WSL+WDDM）实测：训练 5 步没问题，但紧接着的评估会在 320MB 的分配上 OOM
    # （驱动报 5.1GB 空闲却分配失败，是这个组合的已知怪象）。先把训练期的缓存放掉，
    # 每个视角评估完再放一次，能显著降低评估阶段的峰值。
    torch.cuda.empty_cache()
    eval_rows = []
    with torch.no_grad():
        for cam in test_idx:
            gt = (views[cam]["image"].permute(2, 0, 1).unsqueeze(0).to(dev).float() / 255.0)
            renders, _, _ = rasterization(
                means, quats, scales, torch.sigmoid(opac_raw), sh,
                viewmats[cam : cam + 1], Ks[cam : cam + 1], W, H, sh_degree=args.sh_degree,
            )
            ev = renders[0].permute(2, 0, 1).unsqueeze(0)
            del renders
            eval_rows.append(
                {"name": views[cam]["name"], "psnr": psnr(ev, gt), "ssim": float(ssim_simple(ev, gt))}
            )
            del ev, gt
            torch.cuda.empty_cache()
    mean_psnr = float(np.mean([r["psnr"] for r in eval_rows])) if eval_rows else float("nan")
    mean_ssim = float(np.mean([r["ssim"] for r in eval_rows])) if eval_rows else float("nan")
    print(f"\n留出视角评估：PSNR {mean_psnr:.2f} dB | SSIM {mean_ssim:.4f}")

    # ---- 导出：存档用 PLY（满阶 SH）+ 上网用 .splat（每点 32B，Spark 直接可读）----
    opac_final = torch.sigmoid(opac_raw).detach()
    ply_path = out_dir / f"ckpt_{args.steps}.ply"
    export_splats(
        means=means.detach(), scales=scales.detach(), quats=quats.detach(),
        opacities=opac_final,
        sh0=sh[:, :1, :].detach(),          # (N, 1, 3)
        shN=sh[:, 1:, :].detach(),          # (N, (K-1), 3)
        format="ply", save_to=str(ply_path),
    )
    splat_path = out_dir / f"web_{args.steps}.splat"
    if args.sh_degree == 0:
        export_splats(
            means=means.detach(), scales=scales.detach(), quats=quats.detach(),
            opacities=opac_final, sh0=sh[:, :1, :].detach(), shN=sh[:, 1:, :].detach(),
            format="splat", save_to=str(splat_path),
        )
    else:
        # .splat 只有 SH0 颜色：把 DC 项拷进一个 SH0-only 张量再导
        export_splats(
            means=means.detach(), scales=scales.detach(), quats=quats.detach(),
            opacities=opac_final, sh0=sh[:, :1, :].detach(), shN=torch.zeros_like(sh[:, 1:, :]),
            format="splat", save_to=str(splat_path),
        )
    size_mb = round(ply_path.stat().st_size / 1024 / 1024, 2)
    splat_mb = round(splat_path.stat().st_size / 1024 / 1024, 2)

    metrics = {
        "steps": args.steps,
        "sh_degree": args.sh_degree,
        "splats": int(means.shape[0]),
        "train_images": len(train_idx),
        "holdout_images": len(test_idx),
        "resolution": [W, H],
        "downsample": args.down,
        "train_seconds": train_seconds,
        "gpu_mem_mb": peak_mb,
        "psnr": round(mean_psnr, 3),
        "ssim": round(mean_ssim, 4),
        "eval": eval_rows,
        "ply": str(ply_path),
        "ply_mb": size_mb,
        "splat": str(splat_path),
        "splat_mb": splat_mb,
        "loss_curve": log[:: max(1, len(log) // 20)],
        "device": torch.cuda.get_device_name(0) if dev == "cuda" else "cpu",
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"导出存档 PLY {ply_path}（{size_mb} MB）")
    print(f"导出上网用 .splat {splat_path}（{splat_mb} MB，每点 32 字节）")
    print(f"训练耗时 {train_seconds}s | 显存峰值 {peak_mb} MB | 高斯数 {int(means.shape[0])}")
    print(f"指标写入 {out_dir/'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
