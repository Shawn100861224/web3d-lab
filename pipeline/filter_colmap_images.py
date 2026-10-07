#!/usr/bin/env python3
"""把指定的图片从 COLMAP 文本模型里剔除，让训练器不再枚举它们。

用途：拍糊的照片会拖累重建质量，但直接删文件不行 —— 训练器按 `sparse/0/images.txt`
枚举图片（见 `03_train_gsplat_v2.py` 的 `read_colmap_txt`），文件没了会直接 FileNotFoundError。
所以要从模型里同步剔除。

COLMAP images.txt 的格式：
  * 文件开头是若干 `# ...` 注释行；
  * 之后每张图占 **两行**：第一行 `IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME`，
    第二行是该图上的 2D 观测（`x y POINT3D_ID` 三元组，可能为空行）。
所以删一张图要同时删这两行，且**不能把注释行算进配对**（否则会错位，静默删错东西）。

用法：
    python pipeline/filter_colmap_images.py <sparse/0 目录> --drop 032.jpg 035.jpg ...
备份会写成 images.txt.bak（只在第一次运行时生成，避免二次运行把已过滤版盖成备份）。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sparse_dir", type=Path, help="COLMAP 文本模型目录（含 images.txt）")
    ap.add_argument("--drop", nargs="+", required=True, help="要剔除的图片文件名")
    ap.add_argument("--images-dir", type=Path, default=None, help="图片目录（默认 <模型>/../../images）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    drop = set(args.drop)
    images_txt = args.sparse_dir / "images.txt"
    lines = images_txt.read_text().splitlines()

    # 注释头（# 开头）原样保留，剩下的按「两行一条记录」配对
    comments = [l for l in lines if l.lstrip().startswith("#")]
    body = [l for l in lines if not l.lstrip().startswith("#")]
    if len(body) % 2:
        raise SystemExit(f"{images_txt} 非注释行数 {len(body)} 不是偶数，格式不符合预期")

    kept: list[str] = []
    dropped: list[str] = []
    for i in range(0, len(body), 2):
        header, points = body[i], body[i + 1]
        name = header.split()[-1]
        if name in drop:
            dropped.append(name)
        else:
            kept.extend((header, points))

    kept_names = [kept[i].split()[-1] for i in range(0, len(kept), 2)]
    images_dir = args.images_dir or (args.sparse_dir.parents[1] / "images")
    on_disk = sorted(p.name for p in images_dir.glob("*.jpg"))

    print(f"剔除 {len(dropped)} 张：{sorted(dropped)}")
    print(f"模型保留 {len(kept_names)} 张 / 磁盘 {len(on_disk)} 张")
    missing_in_model = sorted(set(on_disk) - set(kept_names))
    missing_on_disk = sorted(set(kept_names) - set(on_disk))
    if missing_in_model or missing_on_disk:
        print(f"⚠️ 不一致：磁盘有但模型没写 {missing_in_model}；模型写了但磁盘没有 {missing_on_disk}")
        return 1
    print("✅ 模型与磁盘完全一致")

    if args.dry_run:
        print("（--dry-run：未写回）")
        return 0

    backup = args.sparse_dir / "images.txt.bak"
    if not backup.exists():
        shutil.copy2(images_txt, backup)
        print(f"已备份原文件 → {backup.name}")
    images_txt.write_text("\n".join(comments + kept) + "\n")
    print(f"已写回 {images_txt}（{len(kept_names)} 张）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
