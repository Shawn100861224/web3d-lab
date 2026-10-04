"""留言板示例数据：让首屏不是空的，同时演示「关联场景」字段。

    cd backend && .venv/Scripts/python.exe scripts/seed_guestbook.py [--reset]

新增走真实 HTTP（/api/guestbook），不直接写库 —— 这样连限流与校验一起被验证。
每条用不同的 client_id，避免撞上 10 分钟 3 条的限流。
`--reset` 先清空留言表（直接写库，仅本地开发用），再灌示例。
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"

SAMPLES: list[dict] = [
    {
        "name": "实验室学长",
        "message": "加载速度和漫游手感都不错。建议再补一个「训练指标对比」，把自训场景和官方示例放一起看。",
        "scene_slug": None,
        "client_id": "seed-guest-0001",
    },
    {
        "name": "室友",
        "message": "手机上也能转，60 帧不掉——就是 8GB 显存的机器跑训练应该挺吃力吧？",
        "scene_slug": "robot-head",
        "client_id": "seed-guest-0002",
    },
    {
        "name": "同学",
        "message": "场景级那个点云密度看着很舒服，希望能加个「只看点云 / 只看球谐颜色」的开关。",
        "scene_slug": "valley",
        "client_id": "seed-guest-0003",
    },
]


def main() -> int:
    if "--reset" in sys.argv:
        from sqlmodel import Session, delete

        from app.db import engine, init_db
        from app.models import GuestbookEntry

        init_db()
        with Session(engine) as session:
            session.exec(delete(GuestbookEntry))
            session.commit()
        print("已清空留言表")

    with httpx.Client(base_url=BASE, timeout=15.0) as c:
        for spec in SAMPLES:
            r = c.post("/api/guestbook", json=spec)
            mark = "✓" if r.status_code == 201 else "✗"
            print(f"{mark} {spec['name']}: HTTP {r.status_code} {r.text[:100]}")
        doc = c.get("/api/guestbook").json()
        print(f"当前留言总数：{doc['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
