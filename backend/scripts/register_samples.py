"""批量登记示例场景（HTTP POST，走真实接口而不是直接写库）。

    cd backend && .venv/Scripts/python.exe scripts/register_samples.py valley fireplace painted-bedroom
"""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000"

SAMPLES: dict[str, dict] = {
    "valley": {"title": "山谷（spark 官方示例，场景级）", "points": 500_000},
    "fireplace": {"title": "壁炉（spark 官方示例，室内场景）", "points": 301_000},
    "painted-bedroom": {"title": "彩绘卧室（forge 示例，场景级）", "points": 500_000},
}


def main() -> int:
    slugs = sys.argv[1:] or list(SAMPLES)
    with httpx.Client(base_url=BASE, timeout=15.0) as c:
        for slug in slugs:
            spec = SAMPLES.get(slug)
            if spec is None:
                print(f"未知 slug：{slug}")
                continue
            payload = {
                "slug": slug,
                "title": spec["title"],
                "summary": "示例资产，用于验证查看器在不同规模点云下的表现。",
                "technique": "3DGS",
                "source": "sample",
                "asset_url": f"/demo/{slug}.spz",
                "asset_format": "spz",
                "sh_degree": 3,
                "num_points": spec["points"],
                "license": "上游示例资产（sparkjs.dev/examples/assets.json），仅用于链路验证",
                "featured": False,
            }
            r = c.post("/api/scenes", json=payload)
            print(f"{slug}: HTTP {r.status_code} {r.text[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
