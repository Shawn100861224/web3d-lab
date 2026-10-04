#!/usr/bin/env python3
"""04 —— 把训练产物变成网页能用的资产，并把指标回写到后端。

    python 04_export_to_web.py --data ~/web3d/data/toy40 --slug toy-capture \
        --frontend /mnt/d/lab/web3d-lab/frontend --api http://127.0.0.1:8000

两条分支：
  * 训练时若导出了 `web_<steps>.splat`（每点 32 字节，SH0 颜色）→ 直接拷进前端 public/demo/，
    这是上网首选：本机实测 1.8 万点的 .splat 只有 ~0.6 MB，而满阶 PLY 是几十 MB。
  * 否则退回「读满阶 PLY、丢掉 SH 高阶项、重写成 SH0 PLY」的老路（不需要 gsplat）。
最后 POST /api/scenes 把 PSNR/SSIM/点数/训练耗时/显存写进数据库 —— 网页上的指标面板显示的就是这些。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

PLY_TYPES = {"float": 4, "float32": 4, "double": 8, "uchar": 1, "uint8": 1, "int": 4, "uint": 4}
KEEP = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
        "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]


def read_ply(path: Path) -> tuple[list[str], np.ndarray]:
    with path.open("rb") as f:
        header: list[str] = []
        while True:
            line = f.readline().decode("ascii").strip()
            header.append(line)
            if line == "end_header":
                break
        props = [l.split()[-1] for l in header if l.startswith("property")]
        n = next((int(l.split()[-1]) for l in header if l.startswith("element vertex")), 0)
        data = np.frombuffer(f.read(), dtype=np.float32, count=n * len(props))
    return props, data.reshape(n, len(props))


def write_web_ply(dest: Path, props: list[str], arr: np.ndarray, mask: np.ndarray) -> None:
    cols = {p: arr[:, i][mask] for i, p in enumerate(props)}
    keep = [p for p in KEEP if p in cols]
    n = int(mask.sum())
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {n}"]
    header += [f"property float {p}" for p in keep]
    header.append("end_header")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        f.write(("\n".join(header) + "\n").encode("ascii"))
        buf = np.empty((n, len(keep)), dtype=np.float32)
        for i, p in enumerate(keep):
            buf[:, i] = cols[p]
        f.write(buf.tobytes())


def register(args, metrics: dict, dest: Path, fmt: str, size_mb: float, points: int, extra: dict) -> int:
    if args.no_register:
        print("（--no-register：跳过回写后端）")
        return 0
    try:
        import httpx
    except ImportError:
        print("缺少 httpx，跳过回写：pip install httpx")
        return 0

    payload = {
        "slug": args.slug,
        "title": args.title,
        "summary": f"Voronoi 纹理球 + 地面平板；{metrics['train_images']} 视角训练、"
                   f"{metrics['holdout_images']} 视角留出评估，COLMAP + gsplat 全流程本机跑通。",
        "technique": "3DGS",
        "source": "self-trained",
        "num_points": points,
        "sh_degree": extra.get("sh_degree", 0),
        "iterations": metrics["steps"],
        "train_seconds": int(metrics["train_seconds"]),
        "gpu_mem_mb": int(metrics["gpu_mem_mb"]),
        "capture_device": "合成采集（pipeline/01_make_synthetic_capture.py）",
        "capture_views": metrics["train_images"] + metrics["holdout_images"],
        "psnr": metrics.get("psnr"),
        "ssim": metrics.get("ssim"),
        "lpips": None,
        "asset_url": f"/demo/{dest.name}",
        "asset_format": fmt,
        "thumbnail_url": None,
        "license": "自产数据（本机训练）",
        "featured": False,
    }
    with httpx.Client(base_url=args.api, timeout=20.0) as c:
        r = c.post("/api/scenes", json=payload)
        if r.status_code == 201:
            print(f"✅ 已回写后端：GET {args.api}/api/scenes/{args.slug}")
        elif r.status_code == 409:
            print("⚠️ 场景已存在（409）：资产已就位，指标需 PATCH 或先清库重灌")
        else:
            print(f"⚠️ 回写失败 HTTP {r.status_code}: {r.text[:200]}")
    print(f"\n网页验证：http://127.0.0.1:5173/scenes/{args.slug}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--slug", default="toy-capture")
    ap.add_argument("--title", default="合成采集（链路验证场景）")
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--frontend", default="/mnt/d/lab/web3d-lab/frontend")
    ap.add_argument("--min-opacity", type=float, default=0.02)
    ap.add_argument("--no-register", action="store_true")
    ap.add_argument("--metrics", default=None,
                    help="显式指定 metrics.json（WSL 与 Windows 之间靠共享盘传递）")
    ap.add_argument("--asset", default=None,
                    help="资产已就位时直接用它（如 toy-capture.splat），跳过拷贝")
    args = ap.parse_args()

    data = Path(args.data).expanduser()
    metrics_path = Path(args.metrics).expanduser() if args.metrics else data / "train" / "metrics.json"
    if not metrics_path.exists():
        print(f"❌ 找不到 {metrics_path}，先跑 03")
        return 2
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    print(f"训练指标：PSNR {metrics.get('psnr')} dB / SSIM {metrics.get('ssim')} / "
          f"{metrics['splats']} 个高斯 / {metrics['train_seconds']}s / {metrics['gpu_mem_mb']} MB 显存")

    dest_dir = Path(args.frontend) / "public" / "demo"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if args.asset:
        dest = Path(args.asset)
        if not dest.is_absolute():
            dest = dest_dir / dest.name
        if not dest.exists():
            print(f"❌ --asset 指定的文件不存在：{dest}")
            return 2
        mb = round(dest.stat().st_size / 1024 / 1024, 3)
        print(f"资产已就位：{dest.name}（{mb} MB）")
        return register(args, metrics, dest, dest.suffix.lstrip("."), mb,
                        metrics["splats"], {"sh_degree": 0})

    splat = metrics.get("splat")
    if splat and Path(splat).exists():
        dest = dest_dir / f"{args.slug}.splat"
        shutil.copy2(splat, dest)
        mb = round(dest.stat().st_size / 1024 / 1024, 3)
        print(f"用训练导出的 .splat：{dest.name}（{mb} MB，SH0 颜色，每点 32 字节）")
        return register(args, metrics, dest, "splat", mb, metrics["splats"], {"sh_degree": 0})

    src = Path(metrics["ply"])
    if not src.is_absolute():
        src = data / "train" / src.name
    if not src.exists():
        print(f"❌ 既没有 .splat 也没有 PLY：{src}")
        return 2
    print(f"退回 PLY 瘦身路径：{src}（{src.stat().st_size / 1024 / 1024:.1f} MB）")
    props, arr = read_ply(src)
    opac = 1.0 / (1.0 + np.exp(-arr[:, props.index("opacity")]))
    mask = opac >= args.min_opacity
    dest = dest_dir / f"{args.slug}.ply"
    write_web_ply(dest, props, arr, mask)
    mb = round(dest.stat().st_size / 1024 / 1024, 3)
    print(f"写出 SH0 PLY：{dest}（{mb} MB，{int(mask.sum())}/{arr.shape[0]} 个点）")
    return register(args, metrics, dest, "ply", mb, int(mask.sum()), {"sh_degree": 0})


if __name__ == "__main__":
    raise SystemExit(main())
