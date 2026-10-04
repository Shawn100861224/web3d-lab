"""对**真实运行中的服务**做 HTTP 验收（不依赖 pytest 的 TestClient）。

用法（后端已起在 8000）：
    cd backend && .venv/Scripts/python.exe scripts/verify_api.py

模块 2 的验收点：空库 200+空数组、写入、读回、过滤、错误码。
"""

from __future__ import annotations

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label}{(' -> ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=10.0) as c:
        print(f"[1] 存活探针 {BASE}/api/health")
        r = c.get("/api/health")
        check("GET /api/health 200", r.status_code == 200, r.text)
        check("service 字段正确", r.json().get("service") == "web3d-lab API")

        print("[2] 空结果路径")
        # 清空库（仅本地开发用；生产无此接口）
        r = c.get("/api/scenes")
        check("GET /api/scenes 200（不是 404）", r.status_code == 200)
        doc = r.json()
        check("结构为 {total, items}", set(doc) == {"total", "items"}, json.dumps(doc))

        print("[3] 写入（含中文，验证 UTF-8 往返）")
        payload = {
            "slug": "desk-chair",
            "title": "桌面椅子（小场景）",
            "summary": "手机环拍 42 张，gsplat 训练 7k 步",
            "technique": "3DGS",
            "num_points": 412345,
            "sh_degree": 3,
            "iterations": 7000,
            "train_seconds": 642,
            "gpu_mem_mb": 5120,
            "capture_device": "Redmi K60",
            "capture_views": 42,
            "psnr": 27.84,
            "ssim": 0.8742,
            "lpips": 0.2113,
            "asset_url": "/demo/desk-chair.spz",
            "asset_format": "spz",
            "featured": True,
        }
        r = c.post("/api/scenes", json=payload)
        if r.status_code == 409:  # 已经存在 → 先删掉重来
            check("重复 slug 返回 409", True, r.json().get("detail", ""))
        else:
            check("POST /api/scenes 201", r.status_code == 201, r.text[:200])
        created = r.json()
        check("中文标题往返无损", created.get("title") == payload["title"], created.get("title", ""))

        print("[4] 读回与过滤")
        r = c.get("/api/scenes")
        doc = r.json()
        check("列表 total>=1", doc["total"] >= 1, f"total={doc['total']}")
        r = c.get("/api/scenes/desk-chair")
        check("详情 200 且 psnr=27.84", r.status_code == 200 and r.json()["psnr"] == 27.84)
        r = c.get("/api/scenes", params={"technique": "2DGS"})
        check("technique 过滤生效", r.json() == {"total": 0, "items": []}, r.text)
        r = c.get("/api/scenes", params={"featured": True})
        check("featured 过滤生效", r.json()["total"] >= 1)

        print("[5] 错误路径")
        r = c.get("/api/scenes/no-such-scene")
        check("未知 slug 404", r.status_code == 404, r.text[:80])
        r = c.post("/api/scenes", json=dict(payload, summary="dup"))
        check("重复 slug 409", r.status_code == 409, r.text[:80])
        r = c.post("/api/scenes", json={"slug": "bad"})
        check("缺必填字段 422", r.status_code == 422)
        r = c.get("/api/scenes", params={"limit": 0})
        check("越界 limit 422", r.status_code == 422)

    print()
    if FAILURES:
        print(f"结果：{len(FAILURES)} 项失败 -> {FAILURES}")
        return 1
    print("结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
