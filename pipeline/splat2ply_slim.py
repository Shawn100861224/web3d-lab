#!/usr/bin/env python3
"""splat2ply_slim.py —— 把 .splat 反写成标准 3DGS PLY（SH0 档，供 spark/three 直接渲染）。

用来隔离「.splat 通道」和「模型本身」：同一份权重，换个容器格式看渲染有没有变好。
.splat 里存的是线性尺度 + 0-255 不透明度；PLY 约定存 log 尺度 + logit 不透明度。
"""
from __future__ import annotations

import sys

import numpy as np

SH_C0 = 0.28209479177387814


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    b = open(src, "rb").read()
    assert len(b) % 32 == 0, "字节数不是 32 的倍数"
    rec = np.frombuffer(b, dtype=np.uint8).reshape(-1, 32)
    xyz = rec[:, 0:12].copy().view("<f4").reshape(-1, 3).astype(np.float32)
    sc = rec[:, 12:24].copy().view("<f4").reshape(-1, 3).astype(np.float32)
    col = rec[:, 24:28].astype(np.float32)
    rgb = col[:, :3] / 255.0
    alpha = np.clip(col[:, 3] / 255.0, 1e-4, 1 - 1e-4)
    rq = (rec[:, 28:32].astype(np.float32) - 128.0) / 128.0
    n = np.linalg.norm(rq, axis=1, keepdims=True); n[n == 0] = 1.0
    rq /= n

    n_splats = len(rec)
    props = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
             "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {n_splats}"]
    header += [f"property float {p}" for p in props]
    header.append("end_header")

    data = np.concatenate([
        xyz,
        (rgb - 0.5) / SH_C0,
        np.log(alpha)[:, None],
        np.log(np.clip(sc, 1e-8, None)),
        rq,
    ], axis=1).astype("<f4")
    assert data.shape[1] == len(props), data.shape
    with open(dst, "wb") as f:
        f.write(("\n".join(header) + "\n").encode("ascii"))
        f.write(data.tobytes())
    import os
    print(f"✅ {dst}：{n_splats} 点 × {data.shape[1]} 属性 | {os.path.getsize(dst)/1048576:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
