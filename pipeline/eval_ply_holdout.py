#!/usr/bin/env python
"""独立评估：用训练导出的 PLY 复算留出视角指标（不采信训练器自报的数字）

为什么要有这个脚本
------------------
`03_train_gsplat.py` 在结尾自己算一遍 PSNR/SSIM 写进 metrics.json。那是**自报值**：
如果划分错了、指标公式有偏、或渲染调用与训练时不一致，外人看不出来。
本脚本从**导出的 PLY**（训练真正的产物）出发，独立走一遍
「读 PLY → 复现场景归一化 → 用留出视角的相机渲染 → 与原图比 PSNR/SSIM」，
并把每张的渲染图与原图并排存下来供人工复核。

口径与 `03_train_gsplat.py` 严格对齐（同一套归一化、同一个 rasterization 调用、同一个
测试集划分：按文件名排序后 index % 8 == 0），所以两边数字应当一致；
**不一致就说明其中一边有问题** —— 这正是这个脚本存在的意义。

用法：
    python pipeline/eval_ply_holdout.py --data <场景目录> --ply <导出的 ply> \
        --out <输出目录> [--holdout-every 8] [--down 1] [--sh-degree 3] [--dump]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


# --------------------------------------------------------------------------- #
# 与训练器一致的读数与度量
# --------------------------------------------------------------------------- #

def qvec_to_rotmat(qvec):
    w, x, y, z = qvec
    return np.array([
        [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * w * z, 2 * x * z + 2 * w * y],
        [2 * x * y + 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * w * x],
        [2 * x * z - 2 * w * y, 2 * y * z + 2 * w * x, 1 - 2 * x * x - 2 * y * y],
    ], dtype=np.float64)


def read_colmap_txt(sparse: Path):
    cams, imgs = {}, []
    for line in (sparse / "cameras.txt").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split()
        cid, model, w, h = int(p[0]), p[1], int(p[2]), int(p[3])
        params = [float(v) for v in p[4:]]
        if model in ("PINHOLE", "OPENCV"):
            fx, fy, cx, cy = params[0], params[1], params[2], params[3]
        elif model == "SIMPLE_PINHOLE":
            fx = fy = params[0]; cx, cy = params[1], params[2]
        else:
            raise SystemExit(f"暂不支持的相机模型：{model}")
        cams[cid] = {"w": w, "h": h, "fx": fx, "fy": fy, "cx": cx, "cy": cy}
    # images.txt 两行一条：位姿行 + 观测行（观测行要跳过）
    lines = [l for l in (sparse / "images.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
             if l.strip() and not l.startswith("#")]
    for i in range(0, len(lines), 2):
        p = lines[i].split()
        imgs.append({
            "id": int(p[0]),
            "qvec": np.array([float(v) for v in p[1:5]]),
            "tvec": np.array([float(v) for v in p[5:8]]),
            "cam_id": int(p[8]),
            "name": p[9],
        })
    pts = []
    for line in (sparse / "points3D.txt").read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split()
        pts.append([float(p[1]), float(p[2]), float(p[3])])
    return cams, imgs, np.array(pts, dtype=np.float64)


def ssim_simple(a: torch.Tensor, b: torch.Tensor, window: int = 11) -> torch.Tensor:
    """与训练器同款的简化 SSIM（高斯窗、通道平均）—— 仅用于自洽对照，不用于跨实现比较。"""
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    coords = torch.arange(window, dtype=a.dtype, device=a.device) - window // 2
    g = torch.exp(-(coords ** 2) / (2 * 1.5 ** 2))
    g = (g / g.sum())
    k = (g[:, None] * g[None, :])[None, None].repeat(a.shape[1], 1, 1, 1)
    mu_a = F.conv2d(a, k, padding=window // 2, groups=a.shape[1])
    mu_b = F.conv2d(b, k, padding=window // 2, groups=b.shape[1])
    va = F.conv2d(a * a, k, padding=window // 2, groups=a.shape[1]) - mu_a ** 2
    vb = F.conv2d(b * b, k, padding=window // 2, groups=b.shape[1]) - mu_b ** 2
    vab = F.conv2d(a * b, k, padding=window // 2, groups=a.shape[1]) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + c1) * (2 * vab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2))
    return s.mean()


def psnr(a: torch.Tensor, b: torch.Tensor) -> float:
    mse = F.mse_loss(a.clamp(0, 1), b.clamp(0, 1)).item()
    return float("inf") if mse <= 0 else float(10 * math.log10(1.0 / mse))


# --------------------------------------------------------------------------- #
# 读 3DGS 的 PLY（标准 3DGS 布局：f_dc_* + f_rest_* 需转置）
# --------------------------------------------------------------------------- #

def load_gaussian_ply(path: Path, sh_degree: int):
    from plyfile import PlyData
    ply = PlyData.read(str(path))
    el = ply["vertex"]
    names = el.data.dtype.names
    xyz = np.stack([el.data["x"], el.data["y"], el.data["z"]], axis=1).astype(np.float32)
    opac = np.asarray(el.data["opacity"], dtype=np.float32)[:, None]
    scale = np.stack([el.data[f"scale_{i}"] for i in range(3)], axis=1).astype(np.float32)
    rot = np.stack([el.data[f"rot_{i}"] for i in range(4)], axis=1).astype(np.float32)
    dc = np.stack([el.data[f"f_dc_{i}"] for i in range(3)], axis=1).astype(np.float32)
    n_rest = (sh_degree + 1) ** 2 - 1
    if n_rest and f"f_rest_0" in names:
        rest = np.stack([el.data[f"f_rest_{i}"] for i in range(n_rest * 3)], axis=1).astype(np.float32)
        # 3DGS 的 PLY 把 f_rest 按 [通道][系数] 平铺 → reshape 后要转置成 [点数][系数][通道]
        rest = rest.reshape(rest.shape[0], 3, n_rest).transpose(0, 2, 1)
        sh = np.concatenate([dc[:, None, :], rest], axis=1)
    else:
        sh = dc[:, None, :]
    return xyz, opac, scale, rot, sh, el.count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="场景目录（含 images/ 与 sparse/0/*.txt）")
    ap.add_argument("--ply", required=True, help="训练导出的 PLY（满阶 SH）")
    ap.add_argument("--out", required=True, help="输出目录（写入 eval.json 与并排图）")
    ap.add_argument("--holdout-every", type=int, default=8)
    ap.add_argument("--down", type=int, default=1)
    ap.add_argument("--sh-degree", type=int, default=3)
    ap.add_argument("--dump", action="store_true", help="写出每张的「渲染 | 原图」并排图")
    args = ap.parse_args()

    data = Path(args.data).expanduser()
    sparse = data / "sparse" / "0"
    out = Path(args.out).expanduser(); out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    cams, images, pts = read_colmap_txt(sparse)
    print(f"COLMAP：{len(images)} 视角 / {len(pts)} 稀疏点")

    # ---- 划分：与训练器完全相同的规则 ----
    order = sorted(range(len(images)), key=lambda i: images[i]["name"])
    test_idx = [i for k, i in enumerate(order) if k % args.holdout_every == 0]
    print(f"留出视角 {len(test_idx)} 张（前 3 张：{[images[i]['name'] for i in test_idx[:3]]}）")

    # ---- 相机（与训练器同样的归一化）----
    viewmats, Ks = [], []
    for im in images:
        cam = cams[im["cam_id"]]
        R = qvec_to_rotmat(im["qvec"]); t = im["tvec"].reshape(3, 1)
        vm = np.concatenate([R, t], axis=1)
        viewmats.append(np.concatenate([vm, np.array([[0, 0, 0, 1]])], axis=0))
        s = args.down
        Ks.append(np.array([[cam["fx"] / s, 0, cam["cx"] / s],
                            [0, cam["fy"] / s, cam["cy"] / s],
                            [0, 0, 1]], dtype=np.float32))
    viewmats = torch.from_numpy(np.stack(viewmats)).float()
    Ks = torch.from_numpy(np.stack(Ks)).float()

    cam_t = viewmats[:, :3, 3].numpy()
    allp = np.concatenate([pts, cam_t])
    radius = float(np.linalg.norm(allp - allp.mean(0), axis=1).max())
    factor = 1.5 / max(radius, 1e-6)
    viewmats[:, :3, 3] *= factor
    print(f"场景归一化：半径 {radius:.2f} -> 1.5（系数 {factor:.4f}）")

    # ---- 读高斯 ----
    xyz, opac, scale, rot, sh, n = load_gaussian_ply(Path(args.ply), args.sh_degree)
    print(f"PLY：{n} 个高斯，SH 形状 {sh.shape}")
    means = torch.from_numpy(xyz).to(dev).requires_grad_(False)
    quats = torch.from_numpy(rot).to(dev)
    scales = torch.from_numpy(scale).to(dev)
    opac_t = torch.from_numpy(opac).to(dev)
    sh_t = torch.from_numpy(sh).to(dev)
    viewmats = viewmats.to(dev); Ks = Ks.to(dev)

    from gsplat import rasterization
    from PIL import Image

    rows = []
    with torch.no_grad():
        for cam in test_idx:
            name = images[cam]["name"]
            gt_img = Image.open(data / "images" / name).convert("RGB")
            w, h = gt_img.size
            if args.down > 1:
                gt_img = gt_img.resize((w // args.down, h // args.down), Image.LANCZOS)
            W, H = gt_img.size
            gt = torch.from_numpy(np.asarray(gt_img, dtype=np.uint8)).to(dev)
            gt = gt.permute(2, 0, 1).unsqueeze(0).float() / 255.0
            renders, _, _ = rasterization(
                means, quats, scales, torch.sigmoid(opac_t), sh_t,
                viewmats[cam:cam + 1], Ks[cam:cam + 1], W, H, sh_degree=args.sh_degree,
            )
            ev = renders[0].permute(2, 0, 1).unsqueeze(0)
            p = psnr(ev, gt); s = float(ssim_simple(ev, gt))
            rows.append({"name": name, "psnr": p, "ssim": s})
            print(f"  {name}  PSNR {p:6.2f} dB  SSIM {s:.4f}")
            if args.dump:
                r = (ev[0].clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255).astype("uint8")
                g = (gt[0].clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255).astype("uint8")
                Image.fromarray(np.concatenate([r, g], axis=1)).save(
                    out / f"{Path(name).stem}_render_vs_gt.png")
            del ev, gt, renders
            torch.cuda.empty_cache()

    ps = [r["psnr"] for r in rows]
    ss = [r["ssim"] for r in rows]
    summary = {
        "source": "独立复算（读导出的 PLY + 与训练器同款归一化与 rasterization 调用）",
        "ply": str(Path(args.ply).name), "holdout_every": args.holdout_every,
        "test_images": len(rows), "sh_degree": args.sh_degree,
        "psnr_mean": round(float(np.mean(ps)), 3),
        "psnr_median": round(float(np.median(ps)), 3),
        "psnr_min": round(float(np.min(ps)), 3), "psnr_max": round(float(np.max(ps)), 3),
        "ssim_mean": round(float(np.mean(ss)), 4),
        "per_view": rows,
    }
    (out / "eval.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n汇总：PSNR 均值 {summary['psnr_mean']}（中位 {summary['psnr_median']}，"
          f"区间 {summary['psnr_min']}–{summary['psnr_max']}）| SSIM 均值 {summary['ssim_mean']}")
    print(f"写入 {out/'eval.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
