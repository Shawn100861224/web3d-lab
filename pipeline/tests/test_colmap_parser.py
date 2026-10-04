#!/usr/bin/env python3
"""COLMAP TXT 解析器自测（不依赖真实数据，用最小 fixture 验证格式假设）。

    python tests/test_colmap_parser.py

为什么需要它：03_train_gsplat.py 直接读 COLMAP 的 TXT 模型，格式细节（images.txt 每两张
行一条记录、qvec 是 wxyz、点的颜色是 0-255）错了不会报错、只会训练出垃圾。所以先用
一个手写的最小 fixture 把假设钉住。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("train03", HERE.parent / "03_train_gsplat.py")
train03 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(train03)  # type: ignore[union-attr]

CAMERAS = """# Camera list
1 OPENCV 900 675 800.0 800.0 450.0 337.5 0.0 0.0 0.0 0.0
"""
IMAGES = """# Image list
1 1.0 0.0 0.0 0.0 0.0 0.0 3.1 1 000.png
0.5 0.5 1
2 0.7071 0.0 0.7071 0.0 3.1 0.0 0.0 1 001.png
0.5 0.5 1
"""
POINTS = """# 3D points
1 0.0 0.0 0.0 255 0 0 0.5 1 0 0.5
2 1.0 0.5 -0.2 0 255 0 0.4 1 0 0.5 1 1 0.3
3 -1.0 0.3 0.1 0 0 255 0.6 1 0 0.5
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "sparse" / "0"
        d.mkdir(parents=True)
        (d / "cameras.txt").write_text(CAMERAS)
        (d / "images.txt").write_text(IMAGES)
        (d / "points3D.txt").write_text(POINTS)

        cams, imgs, xyz, rgb = train03.read_colmap_txt(d)

        assert 1 in cams, "相机没解析出来"
        cam = cams[1]
        assert (cam["w"], cam["h"]) == (900, 675), cam
        assert abs(cam["fx"] - 800.0) < 1e-6 and abs(cam["cx"] - 450.0) < 1e-6, cam

        assert len(imgs) == 2, f"images.txt 每两张行一条记录，应解析出 2 条，得到 {len(imgs)}"
        assert imgs[0]["name"] == "000.png"
        assert imgs[0]["cam_id"] == 1
        assert list(imgs[0]["tvec"]) == [0.0, 0.0, 3.1]

        # 四元数是 wxyz：单位四元数应给单位矩阵
        ident = train03.qvec_to_rotmat(imgs[0]["qvec"])
        assert abs(ident[0, 0] - 1) < 1e-6 and abs(ident[2, 2] - 1) < 1e-6, ident

        assert xyz.shape == (3, 3), xyz.shape
        assert rgb.shape == (3, 3) and rgb[0].tolist() == [255, 0, 0], rgb

    print("✅ COLMAP 解析器自测通过（相机/位姿/点云/颜色）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
