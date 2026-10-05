#!/usr/bin/env python3
"""把一个训练好的 3DGS 场景注册/更新进后端。

为什么要在 Windows 侧跑：WSL 里的 NAT 访问不到 Windows 的 127.0.0.1:8000。

用法:
    python register_scene.py [payload.json]     # 不给文件则用它内置的 bottle 参数

行为：slug 已存在就 PATCH（训练迭代后回写指标的标准做法），否则 POST 新建。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000"

DEFAULT = {
    "slug": "bottle",
    "title": "运动水壶（本人实拍）",
    "summary": "手机环绕实拍 43 张 → COLMAP 43/43 注册（100%，调优 SIFT 后）→ gsplat 训练 12000 步导出。自训场景（画质受照片限制，未上线）。",
    "technique": "3DGS",
    "source": "self-capture",
    "num_points": 48995,
    "sh_degree": 3,
    "iterations": 12000,
    "train_seconds": 347,
    "gpu_mem_mb": 1122,
    "capture_device": "手机（实拍）",
    "capture_views": 43,
    "psnr": 10.42,
    "ssim": 0.6314,
    "asset_url": "/demo/bottle.splat",
    "asset_format": "splat",
    "license": "自有照片（本人拍摄）",
    "featured": False,
    "published": True,
}


def request(path: str, *, payload: dict | None = None, method: str = "GET"):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def main() -> int:
    payload = DEFAULT
    if len(sys.argv) > 1:
        payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
    slug = payload["slug"]

    exists = False
    try:
        status, _ = request(f"/api/scenes/{slug}")
        exists = status == 200
    except urllib.error.HTTPError as exc:
        exists = exc.code != 404
    except Exception as exc:  # noqa: BLE001
        print(f"后端不可达: {exc}")
        return 1

    try:
        if exists:
            status, body = request(f"/api/scenes/{slug}", payload=payload, method="PATCH")
            print(f"PATCH /api/scenes/{slug} -> {status}（已存在，改为更新）")
        else:
            status, body = request("/api/scenes", payload=payload, method="POST")
            print(f"POST /api/scenes -> {status}（新建）")
        print(body[:700])
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:900]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
