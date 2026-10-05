#!/usr/bin/env python3
"""05 —— 拉取公开数据集（真实照片链路验证用）。

    python 05_fetch_public_dataset.py --scene counter [--dest ~/web3d/data/mipnerf360-counter]

**为什么用它**：本机还没照片时，合成采集只能证明"链路通"，证明不了"真实照片能跑"。
Mip-NeRF 360（Google Research）是三维重建领域的标准公开数据集：真实相机拍摄、视角多、
**并且自带你解算好的 COLMAP 位姿**（`sparse/0/*.bin`），可以直接跳过 COLMAP 这一步。

**来源与许可（页面与元数据必须如实标注）**：
  * 数据集：Mip-NeRF 360（Google Research / UC Berkeley / 田纳西大学）
  * 上游：https://jonbarron.info/mipnerf360/
  * 本项目经 HuggingFace 镜像 `nvs-bench/mipnerf360` 获取（镜像标注 MIT；上游为 CC BY 4.0）
  * 用途：**仅作为「公开数据集」来源的方法验证**，页面上与「本人拍摄 / 本机自训」明确区分

为什么不用 huggingface_hub：本机实测它在本镜像上会卡在元数据交互阶段（5 分钟 0 字节），
而镜像的 tree API 与 resolve 地址直连很快（实测首字节 0.5s）。所以这里自己列目录 + 并发下载，
带断点续传（已存在且大小一致的文件直接跳过），少一个依赖也少一个失败点。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (web3d-lab pipeline)"}


def list_dir(endpoint: str, dataset: str, sub: str) -> list[dict]:
    url = f"{endpoint}/api/datasets/{dataset}/tree/main/{urllib.parse.quote(sub)}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect(endpoint: str, dataset: str, scene: str) -> list[tuple[str, int]]:
    """返回 [(仓库内相对路径, 字节数)]。"""
    out: list[tuple[str, int]] = []
    for sub in (f"{scene}/images", f"{scene}/sparse/0"):
        try:
            items = list_dir(endpoint, dataset, sub)
        except Exception as exc:
            print(f"  列目录 {sub} 失败：{exc}")
            continue
        for it in items:
            if it.get("type") == "file":
                out.append((it["path"], int(it.get("size") or 0)))
    return out


def download(endpoint: str, dataset: str, rel: str, dest: Path, size: int) -> tuple[str, str]:
    target = dest / rel
    if target.exists() and (size == 0 or target.stat().st_size == size):
        return rel, "skip"
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{endpoint}/datasets/{dataset}/resolve/main/{urllib.parse.quote(rel)}"
    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)
    tmp.replace(target)
    return rel, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="nvs-bench/mipnerf360")
    ap.add_argument("--scene", default="counter")
    ap.add_argument("--endpoint", default="https://hf-mirror.com", help="HF 镜像（国内必用）")
    ap.add_argument("--dest", default=None)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    dest = Path(args.dest).expanduser() if args.dest else Path.home() / "web3d" / "data" / f"{args.dataset.split('/')[-1]}-{args.scene}"
    print(f"镜像 {args.endpoint} → {dest}")
    files = collect(args.endpoint, args.dataset, args.scene)
    imgs = [f for f in files if "/images/" in f[0]]
    sparse = [f for f in files if "/sparse/" in f[0]]
    total = sum(s for _, s in files)
    print(f"清单：图像 {len(imgs)} 个 / 位姿 {len(sparse)} 个，共 {total/1024/1024:.1f} MB")

    t0 = time.time()
    done = skipped = failed = 0
    got = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(download, args.endpoint, args.dataset, rel, dest, size): rel for rel, size in files}
        for fut in as_completed(futs):
            rel = futs[fut]
            try:
                _, st = fut.result()
                done += 1
                if st == "skip":
                    skipped += 1
                else:
                    got += 1
            except Exception as exc:
                failed += 1
                print(f"  ✗ {rel}: {str(exc)[:70]}")
            if (done + failed) % 40 == 0:
                el = time.time() - t0
                print(f"  进度 {done + failed}/{len(files)}（新下 {got}，跳过 {skipped}，失败 {failed}）已用 {el:.0f}s")

    img_dir = dest / args.scene / "images"
    n_img = len([p for p in img_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    mb = sum(p.stat().st_size for p in img_dir.glob("*")) / 1024 / 1024 if img_dir.exists() else 0
    print(f"\n✅ 完成：{n_img} 张图像（{mb:.1f} MB），用时 {time.time() - t0:.0f}s")
    sp = dest / args.scene / "sparse" / "0"
    if sp.exists():
        print(f"✅ 自带位姿：{[p.name for p in sorted(sp.iterdir())]}")
    else:
        print("⚠️ 没有 sparse/0，需要自己跑 COLMAP（用 pipeline/02）")
    print(f"数据目录：{dest}")
    print("来源：Mip-NeRF 360（公开数据集，非本人拍摄）")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
