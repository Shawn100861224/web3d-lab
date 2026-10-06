#!/usr/bin/env python3
"""03_train_gsplat_v2.py —— 用 gsplat 官方 DefaultStrategy 的训练循环（标准配方）

与原 03_train_gsplat.py 的关键区别（原版自训全部糊成一片灰雾）：
  1. 稠密化 / 剪枝 / 不透明度周期重置 → 全部交给 gsplat 手写的 DefaultStrategy（官方实现）
  2. 参数按官方约定拆成 dict：means / scales / quats / opacities / sh0 / shN，
     每项一个独立 Adam（strategy 的接口要求 params 和 optimizers 都是 dict）
  3. 初始化对齐官方：opacity = logit(0.1)、scale = log(最近邻距离)、quats = 单位四元数
  4. 不再每 100 步重建优化器（原版会把 Adam 动量清零）

COLMAP 解析、相机（viewmat/K）、场景归一化、SSIM/PSNR 直接复用原脚本的函数。
本版先只验证「loss 是否真的下降」，导出随后加。
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

_PIPE = Path(__file__).resolve().parent
_spec = spec_from_file_location("t03", _PIPE / "03_train_gsplat.py")
t03 = module_from_spec(_spec)
_spec.loader.exec_module(t03)          # 只拿到函数定义，main() 有 __main__ 守卫

from gsplat import rasterization                    # noqa: E402
from gsplat.strategy import DefaultStrategy          # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"


def build_params(pts_xyz, pts_rgb, sh_degree=3, scene_scale=1.5, max_scale_frac=0.02):
    """按 gsplat 官方约定初始化参数（opacity=logit(0.1)、scale=log(NN 距离)）。

    注意：官方那套「初始尺度 = 最近邻距离」是为几十万点的稠密稠密点云设计的。
    本项目的 COLMAP 稀疏云只有 ~3000 点、且铺满整个房间尺度（跨度 ~8，相对场景半径 1.5），
    最近邻距离约 0.145 = 场景的 10% —— 2977 个这么大的团子互相重叠近 20 层，
    渲染结果必然是「均匀半透明雾」（实测 std=0、alpha 100%），且与归一化尺度无关
    （缩放是等比的，相对大小不变）。因此这里给初始尺度加上限。
    """
    means = torch.tensor(pts_xyz, dtype=torch.float32, device=DEV)

    # 最近邻距离
    n = means.shape[0]
    chunk = 4096
    nn = torch.full((n,), float("inf"), device=DEV)
    for i in range(0, n, chunk):
        d = torch.cdist(means[i:i + chunk], means)
        d[torch.arange(d.shape[0], device=DEV), torch.arange(i, min(i + chunk, n), device=DEV)] = float("inf")
        nn[i:i + chunk] = d.min(dim=1).values
    nn = nn.clamp_min(1e-6)
    cap = max_scale_frac * scene_scale
    n_capped = int((nn > cap).sum())
    nn = nn.clamp_max(cap)
    scales = torch.log(nn).unsqueeze(-1).repeat(1, 3)          # 官方：log(sqrt(dist2))
    print(f"初始尺度：NN 距离上限 {cap:.4f}（场景 {scene_scale}），被截断 {n_capped}/{n} 个")
    quats = torch.zeros(n, 4, device=DEV)
    quats[:, 0] = 1.0                                          # (w,x,y,z) 单位四元数
    opacities = torch.logit(torch.full((n, 1), 0.1, device=DEV))

    rgb = torch.tensor(pts_rgb.astype(np.float32) / 255.0, device=DEV)
    sh0 = ((rgb - 0.5) / 0.28209479177387814).unsqueeze(1)     # (N,1,3) DC 项
    K = (sh_degree + 1) ** 2 - 1
    shN = torch.zeros(n, K, 3, device=DEV)                     # (N,K,3) 高阶项

    params = {
        "means": torch.nn.Parameter(means.requires_grad_(True)),
        "scales": torch.nn.Parameter(scales.requires_grad_(True)),
        "quats": torch.nn.Parameter(quats.requires_grad_(True)),
        "opacities": torch.nn.Parameter(opacities.requires_grad_(True)),
        "sh0": torch.nn.Parameter(sh0.requires_grad_(True)),
        "shN": torch.nn.Parameter(shN.requires_grad_(True)),
    }
    return params


def make_optimizers(params, lr_pos=1.6e-4):
    lrs = {"means": lr_pos, "scales": 5e-3, "quats": 1e-3,
           "opacities": 5e-2, "sh0": 2.5e-3, "shN": 2.5e-3 / 20}
    return {k: torch.optim.Adam([{"params": [v], "lr": lrs[k]}], eps=1e-15, betas=(0.9, 0.999))
            for k, v in params.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--sh-degree", type=int, default=3)
    ap.add_argument("--holdout", type=int, default=4)
    ap.add_argument("--down", type=int, default=4)
    ap.add_argument("--scene-scale", type=float, default=1.5)
    ap.add_argument("--keep-radius-frac", type=float, default=0.35,
                    help="只保留「相机群半径 × 该比例」内的稀疏点，把房间背景裁掉（主体总在相机壳内部）")
    ap.add_argument("--log-every", type=int, default=100)
    ap.add_argument("--flip-yz", action="store_true",
                    help="给 viewmat 左乘 diag(1,-1,-1,1)：OpenCV(y下,z前) ↔ OpenGL(y上,z后) 相机坐标约定转换")
    ap.add_argument("--grow-grad2d", type=float, default=2e-4,
                    help="稠密化触发阈值（DefaultStrategy 默认 2e-4）。实测本数据 means2d 梯度约 2e-7、"
                         "经 width/2 缩放后仍低于门槛 → 高斯永不增长，需调低。")
    args = ap.parse_args()

    data = Path(args.data).expanduser()
    sparse = data / "sparse" / "0"
    cameras, images, pts_xyz, pts_rgb = t03.read_colmap_txt(sparse)
    print(f"COLMAP：{len(images)} 视角 / {len(pts_xyz)} 稀疏点 | 设备 {DEV}")

    views = []
    for im in images:
        img = Image.open(data / "images" / im["name"]).convert("RGB")
        w, h = img.size
        if args.down > 1:
            img = img.resize((w // args.down, h // args.down), Image.LANCZOS)
        views.append(torch.from_numpy(np.asarray(img, dtype=np.uint8)))
    H, W = views[0].shape[:2]
    # 背景色：gsplat 默认把未覆盖区域渲染成黑色 ✗。实拍照片里主体只占一部分、
    # 其余是桌面/房间（亮色）→ 优化器唯一能降 loss 的手段会变成「让高斯膨胀盖满整幅图」，
    # 这正是初始尺度爆炸、渲染成均匀雾的机制。官方 3DGS 对实拍数据用背景色/掩码处理。
    bg_colors = torch.stack([v.float().reshape(-1, 3).mean(0) for v in views]).to(DEV) / 255.0
    print(f"背景色（逐图均值）范围 {bg_colors.min().item():.3f}~{bg_colors.max().item():.3f}")
    print(f"训练分辨率 {W}x{H}（降采样 x{args.down}）")

    viewmats, Ks = [], []
    for im in images:
        cam = cameras[im["cam_id"]]
        R = t03.qvec_to_rotmat(im["qvec"]).astype(np.float32)
        t = im["tvec"].reshape(3, 1).astype(np.float32)
        vm = np.concatenate([R, t], axis=1)
        viewmats.append(np.concatenate([vm, np.array([[0, 0, 0, 1]], np.float32)], axis=0))
        s = args.down
        Ks.append(np.array([[cam["fx"] / s, 0, cam["cx"] / s],
                            [0, cam["fy"] / s, cam["cy"] / s], [0, 0, 1]], np.float32))
    viewmats = torch.tensor(np.stack(viewmats), device=DEV)
    Ks = torch.tensor(np.stack(Ks), device=DEV)

    if args.flip_yz:
        FLIP = torch.diag(torch.tensor([1.0, -1.0, -1.0, 1.0], device=DEV))
        viewmats = torch.einsum("ij,cjk->cik", FLIP, viewmats)
        print("相机约定：已应用 diag(1,-1,-1,1)（OpenGL 风格）")

    # 场景归一化：尺度必须由「相机群半径」决定（官方 3DGS 的 getNerfppNorm 做法）。
    # 原版用点云最远距离定尺度，会被 COLMAP 的离群稀疏点带偏（实测半径 37.2 而相机只跨 11.9），
    # 导致物体被压成中心小团、相机"埋进"物体内部 —— 渲染出来就是一片均匀灰雾。
    R_all = viewmats[:, :3, :3]
    t_all = viewmats[:, :3, 3:4]
    cam_c = (-R_all.transpose(1, 2) @ t_all).squeeze(-1)      # 相机中心 C = -R^T t
    c0 = cam_c.mean(0, keepdim=True)                          # 相机群中心（新原点）
    cam_radius = float((cam_c - c0).norm(dim=-1).max())
    s = args.scene_scale / max(cam_radius, 1e-6)

    # 只保留相机壳内部的点（房间背景/远处杂点在壳外，正是把尺度带偏的元凶）
    c0_np = c0.cpu().numpy().reshape(-1)
    d = np.linalg.norm(pts_xyz - c0_np, axis=1)
    keep = d <= args.keep_radius_frac * cam_radius
    if int(keep.sum()) < 200:
        keep = d <= cam_radius                     # 兜底：太狠就放宽到整个相机壳
        print(f"  （保留点不足 200，放宽到相机群半径 {cam_radius:.2f}）")
    if int(keep.sum()) < max(50, 0.02 * len(pts_xyz)):
        keep = np.ones_like(keep, dtype=bool)
        print("  （放宽后仍太少，取消裁剪）")
    n_drop = int((~keep).sum())
    pts_xyz, pts_rgb = pts_xyz[keep], pts_rgb[keep]

    # 平移+缩放：x_cam 不变式要求 t' = (t + R·c0)·s
    viewmats[:, :3, 3] = ((t_all + (R_all @ c0.unsqueeze(-1))).squeeze(-1)) * s
    pts_xyz = (pts_xyz - c0_np) * s
    print(f"场景归一化：相机群半径 {cam_radius:.2f} -> {args.scene_scale}（系数 {s:.4f}）"
          f" | 剔除离群点 {n_drop}/{n_drop + len(pts_xyz)} | 剩余点 {len(pts_xyz)}")
    _cc = (-viewmats[:, :3, :3].transpose(1, 2) @ viewmats[:, :3, 3:4]).cpu().numpy().reshape(-1, 3)
    _pn = np.linalg.norm(pts_xyz.max(0) - pts_xyz.min(0))
    print(f"  校验：点云跨度 {_pn:.3f} | 相机中心到原点中位距离 "
          f"{np.median(np.linalg.norm(_cc, axis=1)):.3f}（应 > 点云跨度的一半）")

    n_train = len(views) - args.holdout
    train_idx, test_idx = list(range(n_train)), list(range(n_train, len(views)))

    params = build_params(pts_xyz, pts_rgb, scene_scale=args.scene_scale)
    optimizers = make_optimizers(params)
    strategy = DefaultStrategy(verbose=False, grow_grad2d=args.grow_grad2d)
    strategy.check_sanity(params, optimizers)
    state = strategy.initialize_state(scene_scale=args.scene_scale)

    torch.manual_seed(0)
    log, t0 = [], time.time()
    print(f"初始高斯数 {params['means'].shape[0]}")
    for step in range(1, args.steps + 1):
        cam = train_idx[torch.randint(0, len(train_idx), (1,)).item()]
        gt = views[cam].permute(2, 0, 1).unsqueeze(0).to(DEV).float() / 255.0

        colors = torch.cat([params["sh0"], params["shN"]], dim=1)
        renders, alphas, info = rasterization(
            params["means"], params["quats"], params["scales"],
            torch.sigmoid(params["opacities"]).squeeze(-1), colors,
            viewmats[cam:cam + 1], Ks[cam:cam + 1], W, H, sh_degree=args.sh_degree,
            backgrounds=bg_colors[cam:cam + 1],
            packed=False,   # 必须与 DefaultStrategy 的约定一致：非打包 (C,N,2)
        )
        img = renders[0].permute(2, 0, 1).unsqueeze(0)
        loss = 0.8 * F.l1_loss(img, gt) + 0.2 * (1 - t03.ssim_simple(img, gt))

        strategy.step_pre_backward(params, optimizers, state, step, info)
        loss.backward()

        if getattr(args, "debug_grad", False) and step <= 3:
            def _n(t):
                return "None" if t is None else f"{float(t.norm()):.3e}"
            print(f"  [DEBUG step {step}] info 键={sorted(info.keys())}")
            print(f"  [DEBUG] means2d shape={tuple(info['means2d'].shape)}"
                  f" grad={_n(info['means2d'].grad)}"
                  f" absgrad={_n(getattr(info['means2d'], 'absgrad', None))}"
                  f" requires_grad={info['means2d'].requires_grad}")
            print(f"  [DEBUG] means.grad={_n(params['means'].grad)}"
                  f" scales.grad={_n(params['scales'].grad)}"
                  f" quats.grad={_n(params['quats'].grad)}"
                  f" opac.grad={_n(params['opacities'].grad)}"
                  f" sh0.grad={_n(params['sh0'].grad)}")
        strategy.step_post_backward(params, optimizers, state, step, info)
        for o in optimizers.values():
            o.step()
            o.zero_grad(set_to_none=True)

        if step % args.log_every == 0 or step == 1:
            with torch.no_grad():
                p = t03.psnr(img.detach(), gt)
            log.append(dict(step=step, loss=float(loss.item()), psnr=p,
                            splats=int(params["means"].shape[0])))
            print(f"  step {step:5d} | loss {loss.item():.4f} | PSNR {p:5.2f} "
                  f"| splats {params['means'].shape[0]:6d} | {time.time()-t0:6.1f}s", flush=True)

    print(f"\n训练完成 {time.time()-t0:.1f}s")
    print("\n=== loss 曲线（判据：应当持续下降）===")
    for r in log:
        print(f"  step {r['step']:5d}  loss {r['loss']:.4f}  psnr {r['psnr']:5.2f}  splats {r['splats']}")

    # 留出视角评估
    with torch.no_grad():
        ps = []
        for cam in test_idx:
            gt = views[cam].permute(2, 0, 1).unsqueeze(0).to(DEV).float() / 255.0
            colors = torch.cat([params["sh0"], params["shN"]], dim=1)
            r, _, _ = rasterization(
                params["means"], params["quats"], params["scales"],
                torch.sigmoid(params["opacities"]).squeeze(-1), colors,
                viewmats[cam:cam + 1], Ks[cam:cam + 1], W, H, sh_degree=args.sh_degree)
            ev = r[0].permute(2, 0, 1).unsqueeze(0)
            ps.append(t03.psnr(ev, gt))
            torch.cuda.empty_cache()
        print(f"\n留出视角 PSNR 均值 {np.mean(ps):.2f} dB  （原脚本同类数据约 11.8）")

        # 存「训练后渲染 vs 原图」对照图 + 统计（std=0 即还是均匀雾）
        from PIL import Image as _I
        out_dir = Path("/mnt/d/lab/web3d-lab/work/v2_last")
        out_dir.mkdir(parents=True, exist_ok=True)
        cam = test_idx[0]
        gt = views[cam].permute(2, 0, 1).unsqueeze(0).to(DEV).float() / 255.0
        colors = torch.cat([params["sh0"], params["shN"]], dim=1)
        r, a, _ = rasterization(
            params["means"], params["quats"], params["scales"],
            torch.sigmoid(params["opacities"]).squeeze(-1), colors,
            viewmats[cam:cam + 1], Ks[cam:cam + 1], W, H,
            sh_degree=args.sh_degree, packed=False)
        im = (r[0].clamp(0, 1) * 255).byte().cpu().numpy()
        g = (gt[0].permute(1, 2, 0).clamp(0, 1) * 255).byte().cpu().numpy()
        _I.fromarray(np.concatenate([im, g], axis=1)).save(out_dir / "trained_vs_gt.png")
        print(f"  渲染 std={im.reshape(-1,3).std(0).round(1)} | 原图 std={g.reshape(-1,3).std(0).round(1)}"
              f" | alpha>0.5 占 {(a[0, ..., 0] > 0.5).float().mean().item()*100:.1f}%")
        print(f"  对照图：{out_dir}/trained_vs_gt.png（左=训练后渲染 右=原图）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
