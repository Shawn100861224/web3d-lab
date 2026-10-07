"""Postgres 集成冒烟测试：写 → 读 → 聚合 → 清理。

为什么需要它：pytest 那 36 项跑在 SQLite 上，而线上是 Postgres。迁移里最容易翻车的是
SQLite 与 Postgres 的差异（时区感知的 datetime、按天聚合、count 语法），所以上线上线前
必须用**真实目标库**跑一遍同样的写读链路。

用法（必须显式给 DATABASE_URL，避免误写本地 SQLite）：

    set -a; . ./.env; set +a
    python scripts/pg_smoke.py

脚本自己清理产生的测试数据（按固定署名标记删除），跑完不该留下任何记录。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MARK = "冒烟测试（脚本自动清理）"
CLIENT_ID = "pg-smoke-client"


def main() -> int:
    if not os.environ.get("DATABASE_URL", "").strip():
        print("❌ 未设置 DATABASE_URL：本脚本只用于真实 Postgres，避免误写本地库。")
        return 2

    from fastapi.testclient import TestClient

    from app.config import DATABASE_URL, IS_SQLITE
    from app.db import engine
    from app.main import create_app

    if IS_SQLITE:
        print("❌ DATABASE_URL 指向 SQLite，本脚本要求 Postgres。")
        return 2

    print(f"目标：{DATABASE_URL.split('@')[-1]}")
    failures: list[str] = []

    with TestClient(create_app()) as c:
        # ① 健康检查
        r = c.get("/api/health")
        print(f"① GET  /api/health        {r.status_code} {r.text[:70]}")
        if r.status_code != 200:
            failures.append("health 非 200")

        # ② 读场景（应能看到灌进去的 7 个已发布场景）
        r = c.get("/api/scenes?limit=100")
        total = r.json().get("total") if r.status_code == 200 else None
        print(f"② GET  /api/scenes        {r.status_code} total={total}")
        if not (isinstance(total, int) and total >= 7):
            failures.append(f"场景数异常：{total}")

        # ③ 写留言（Postgres 上的时间戳写入是最容易翻车的一步）
        r = c.post(
            "/api/guestbook",
            json={
                "name": MARK,
                "message": "Postgres 写路径冒烟：写入应能被读回。",
                "client_id": CLIENT_ID,
            },
        )
        print(f"③ POST /api/guestbook     {r.status_code} {r.text[:80]}")
        if r.status_code != 201:
            failures.append(f"留言写入失败：{r.status_code}")
        new_id = r.json().get("id") if r.status_code == 201 else None

        # ④ 读回列表
        r = c.get("/api/guestbook?limit=100")
        got = [i for i in r.json().get("items", []) if i.get("name") == MARK] if r.status_code == 200 else []
        print(f"④ GET  /api/guestbook     {r.status_code} 找到测试留言 {len(got)} 条")
        if len(got) != 1:
            failures.append("写进去的留言没读回来")

        # ⑤ 事件上报 + 按天聚合（聚合逻辑在 Python 里，但日期字段类型是 Postgres 决定的）
        r = c.post("/api/events", json={"event_type": "page_view", "path": "/", "client_id": CLIENT_ID})
        print(f"⑤ POST /api/events        {r.status_code} {r.text[:60]}")
        if r.status_code not in (200, 201, 202):
            failures.append(f"事件上报失败：{r.status_code}")

        r = c.get("/api/stats?days=14")
        body = r.json() if r.status_code == 200 else {}
        days = len(body.get("daily", [])) if isinstance(body.get("daily"), list) else "n/a"
        print(f"⑥ GET  /api/stats?days=14 {r.status_code} 合计浏览={body.get('total_views')} 按天条目={days}")
        if r.status_code != 200:
            failures.append(f"统计接口失败：{r.status_code}")

    # ⑦ 清理：删掉本次产生的测试数据（留言 + 事件）
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM guestbookentry WHERE name = :m"), {"m": MARK})
        conn.execute(text("DELETE FROM pageview WHERE client_id = :c"), {"c": CLIENT_ID})
        conn.commit()
        left = conn.execute(text("select count(*) from guestbookentry where name = :m"), {"m": MARK}).scalar()
        left_events = conn.execute(text("select count(*) from pageview where client_id = :c"), {"c": CLIENT_ID}).scalar()
    print(f"⑦ 清理完成：残留测试留言 {left} 条 / 测试事件 {left_events} 条（都应为 0）")
    if left or left_events:
        failures.append("测试数据未清理干净")

    print("\n" + ("❌ 失败：" + "；".join(failures) if failures else "✅ 全部通过（写 / 读 / 聚合 / 清理）"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
