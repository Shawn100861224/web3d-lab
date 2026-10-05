#!/usr/bin/env python3
"""SfM 注册失败诊断：哪几张没注册进去、失败的有什么共同特征。

为什么需要：注册率不达标时，只说"重拍"没有信息量。真正有用的是
"失败的这 28 张里，有 12 张分辨率和其他不一样"这种可指认的规律 ——
那样用户只需要补/改那一小部分，不用全重拍。

用法: python sfm_diagnose.py <dataset_dir>       # 该目录下应有 images/ 与 sparse/0/images.txt
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def parse_registered(images_txt: Path) -> set[str]:
    """COLMAP images.txt 的偶数行是图像记录：ID QW QX QY QZ TX TY TZ CAMERA NAME"""
    names: set[str] = set()
    for i, line in enumerate(images_txt.read_text(encoding="utf-8", errors="ignore").splitlines()):
        if i % 2 != 0:
            continue  # 奇数行是 2D 点
        parts = line.strip().split()
        if len(parts) >= 10 and parts[0].isdigit():
            names.add(parts[9])
    return names


def laplacian_var(gray: np.ndarray) -> float:
    g = gray.astype(np.float32)
    lap = 4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python sfm_diagnose.py <dataset_dir>")
        return 2
    data = Path(sys.argv[1])
    images_dir = data / "images"
    images_txt = data / "sparse" / "0" / "images.txt"
    if not images_txt.is_file():
        print(f"找不到 {images_txt}（还没成功建图？）")
        return 2

    registered = parse_registered(images_txt)
    files = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    print(f"=== SfM 注册诊断：{data} ===")
    print(f"输入 {len(files)} 张，注册 {len(registered)} 张，注册率 {len(registered)/max(len(files),1):.3f}\n")

    rows = []
    for p in files:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            w, h = im.size
            gray = np.asarray(im.convert("L"), dtype=np.uint8)
        rows.append({
            "name": p.name,
            "size": (w, h),
            "ok": p.name in registered,
            "bright": float(gray.mean()),
            "sharp": laplacian_var(gray),
        })

    # 按分辨率分组，看注册率差异 —— 这是"单一相机"假设被破坏的典型症状
    by_size: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in rows:
        by_size[r["size"]].append(r)
    print("--- 按分辨率分组 ---")
    for size, group in sorted(by_size.items(), key=lambda kv: -len(kv[1])):
        ok = sum(1 for r in group if r["ok"])
        print(f"  {size[0]}x{size[1]}: {ok}/{len(group)} 张注册  ({ok/len(group):.0%})")

    # 按亮度分位看注册率（暴露"光照不一致"的影响）
    print("\n--- 按亮度四分位 ---")
    rows_sorted = sorted(rows, key=lambda r: r["bright"])
    q = max(1, len(rows_sorted) // 4)
    for i in range(4):
        chunk = rows_sorted[i * q:(i + 1) * q] if i < 3 else rows_sorted[3 * q:]
        if not chunk:
            continue
        ok = sum(1 for r in chunk if r["ok"])
        print(f"  亮度 {chunk[0]['bright']:.0f}–{chunk[-1]['bright']:.0f}: {ok}/{len(chunk)} 注册")

    # 按清晰度四分位
    print("\n--- 按清晰度四分位 ---")
    rows_sharp = sorted(rows, key=lambda r: r["sharp"])
    for i in range(4):
        chunk = rows_sharp[i * q:(i + 1) * q] if i < 3 else rows_sharp[3 * q:]
        if not chunk:
            continue
        ok = sum(1 for r in chunk if r["ok"])
        print(f"  sharp {chunk[0]['sharp']:.0f}–{chunk[-1]['sharp']:.0f}: {ok}/{len(chunk)} 注册")

    failed = [r for r in rows if not r["ok"]]
    print(f"\n--- 失败的 {len(failed)} 张（按文件名）---")
    for r in failed:
        print(f"  {r['name']}  {r['size'][0]}x{r['size'][1]}  bright={r['bright']:.0f}  sharp={r['sharp']:.0f}")

    print("\n--- 结论提示 ---")
    mixed = len(by_size) > 1
    if mixed:
        print("  ⚠ 存在多种分辨率：COLMAP 以 single_camera 假设运行，内参被强制共享，")
        print("    分辨率不同的那批会系统性失配 → 建议全部重采样到同一尺寸后重跑。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
