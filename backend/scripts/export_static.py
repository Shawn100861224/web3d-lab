"""把「已发布场景」导出成前端打包用的静态兜底 JSON。

为什么需要它：线上静态托管（GitHub Pages / EdgeOne）没有后端时，场景库和查看器页仍然要能打开。
前端启动先探测 /api/health：通了走真接口，不通就退回这份随包发布的 JSON ——
「链接永远可用」比「后端一定在线」重要。

    cd backend && .venv/Scripts/python.exe scripts/export_static.py
    # 从运行中的服务导出（推荐，走真实接口）
    .venv/Scripts/python.exe scripts/export_static.py --from-http

产物：frontend/public/scenes-fallback.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUT = BACKEND_DIR.parent / "frontend" / "public" / "scenes-fallback.json"
GOUT = BACKEND_DIR.parent / "frontend" / "public" / "guestbook-fallback.json"
PUBLIC_FIELDS = (
    "slug",
    "title",
    "summary",
    "technique",
    "source",
    "num_points",
    "sh_degree",
    "iterations",
    "train_seconds",
    "gpu_mem_mb",
    "capture_device",
    "capture_views",
    "psnr",
    "ssim",
    "lpips",
    "asset_url",
    "asset_format",
    "thumbnail_url",
    "license",
    "featured",
    "published",
)


def from_http() -> dict:
    import httpx

    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0) as c:
        items = c.get("/api/scenes", params={"limit": 200}).json()["items"]
    return {"generated_from": "http", "items": items}


def from_db() -> dict:
    sys.path.insert(0, str(BACKEND_DIR))
    from sqlmodel import Session, select

    from app.db import engine, init_db
    from app.models import Scene

    init_db()
    with Session(engine) as session:
        rows = session.exec(select(Scene).where(Scene.published == True)).all()  # noqa: E712
    items = []
    for row in rows:
        d = row.model_dump()
        d["created_at"] = str(d.get("created_at"))
        d["updated_at"] = str(d.get("updated_at"))
        items.append({k: d.get(k) for k in ("id", *PUBLIC_FIELDS, "created_at", "updated_at")})
    return {"generated_from": "db", "items": items}


def guestbook_from_http() -> dict:
    import httpx

    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0) as c:
        doc = c.get("/api/guestbook", params={"limit": 20}).json()
    return {"generated_from": "http", "total": doc["total"], "items": doc["items"]}


def guestbook_from_db() -> dict:
    sys.path.insert(0, str(BACKEND_DIR))
    from sqlmodel import Session, select

    from app.db import engine, init_db
    from app.models import GuestbookEntry

    init_db()
    with Session(engine) as session:
        rows = session.exec(
            select(GuestbookEntry).where(GuestbookEntry.hidden == False)  # noqa: E712
            .order_by(GuestbookEntry.created_at.desc()).limit(20)
        ).all()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "message": r.message,
            "scene_slug": r.scene_slug,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]
    return {"generated_from": "db", "total": len(items), "items": items}


def main() -> int:
    use_http = "--from-http" in sys.argv
    payload = from_http() if use_http else from_db()
    payload["note"] = "静态兜底数据：后端不可达时前端读取它；由 backend/scripts/export_static.py 生成"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写出 {OUT}（{len(payload['items'])} 个场景，来源 {payload['generated_from']}）")

    # 留言板离线快照：让静态部署下的留言板不是一片空白，而是"示例留言 + 说明"
    gb = guestbook_from_http() if use_http else guestbook_from_db()
    gb["note"] = "静态部署下的留言快照（只读）：线上写入需要后端服务，本地/容器环境已实现"
    GOUT.parent.mkdir(parents=True, exist_ok=True)
    GOUT.write_text(json.dumps(gb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写出 {GOUT}（{len(gb['items'])} 条留言快照，来源 {gb['generated_from']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
