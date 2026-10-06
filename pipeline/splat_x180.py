#!/usr/bin/env python3
"""splat_x180.py —— 把 .splat 里的模型整体绕 X 轴旋转 180°（y→-y, z→-z，四元数同步）。

用途：验证「COLMAP 世界系 y 向下 ↔ three.js/OpenGL y 向上」的约定错位是否就是
「训练渲染正常、网页查看器里一团碎片」的原因。若旋转后网页正常 → 导出时应统一带上这个变换。

用法： python splat_x180.py <in.splat> <out.splat>
"""
from __future__ import annotations

import sys

import numpy as np


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    b = open(src, "rb").read()
    assert len(b) % 32 == 0, "字节数不是 32 的倍数，文件不合法"
    rec = np.frombuffer(b, dtype=np.uint8).reshape(-1, 32).copy()

    xyz = rec[:, 0:12].copy().view("<f4").reshape(-1, 3)
    sc = rec[:, 12:24].copy()                                  # 线性尺度，原样保留
    col = rec[:, 24:28]                                        # RGBA
    rq = (rec[:, 28:32].astype(np.float32) - 128.0) / 128.0    # (w,x,y,z)
    n = np.linalg.norm(rq, axis=1, keepdims=True)
    n[n == 0] = 1.0
    rq = rq / n
    w, x, y, z = rq[:, 0], rq[:, 1], rq[:, 2], rq[:, 3]
    # q' = q_x180(0,1,0,0) ⊗ q  →  (w',x',y',z') = (-x, w, -z, y)
    q2 = np.stack([-x, w, -z, y], 1)
    q2b = np.clip(q2 * 128 + 128, 0, 255).astype(np.uint8)

    xyz2 = np.stack([xyz[:, 0], -xyz[:, 1], -xyz[:, 2]], 1).astype("<f4")
    out = np.concatenate([xyz2.view(np.uint8).reshape(-1, 12), sc, col, q2b], axis=1)
    open(dst, "wb").write(out.tobytes())
    print(f"✅ {dst}：{len(out)} 点 | 位置 y/z 取反 | 四元数同步变换 | "
          f"{len(out) * 32 / 1048576:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
