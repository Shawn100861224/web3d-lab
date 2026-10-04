"""模块 5 验收测试：事件写入、30 秒去重、统计汇总与空库路径。"""

from __future__ import annotations


def _event(**over):
    base = {
        "event": "view",
        "path": "/scenes/robot-head",
        "scene_slug": "robot-head",
        "client_id": "client-12345678",
    }
    base.update(over)
    return base


def test_event_then_stats_change(client):
    empty = client.get("/api/stats").json()
    assert empty["total_views"] == 0
    assert empty["unique_clients"] == 0
    assert len(empty["daily"]) == 14
    assert empty["per_scene"] == []

    r = client.post("/api/events", json=_event())
    assert r.status_code == 201, r.text
    assert r.json()["deduped"] is False

    after = client.get("/api/stats").json()
    assert after["total_views"] == 1
    assert after["unique_clients"] == 1
    assert after["per_scene"] == [{"slug": "robot-head", "title": None, "views": 1}]
    assert after["daily"][-1]["views"] == 1


def test_duplicate_event_within_window_is_deduped(client):
    assert client.post("/api/events", json=_event()).status_code == 201
    again = client.post("/api/events", json=_event())
    assert again.status_code == 202
    assert again.json()["deduped"] is True
    assert client.get("/api/stats").json()["total_views"] == 1


def test_same_client_different_path_not_deduped(client):
    client.post("/api/events", json=_event())
    r = client.post("/api/events", json=_event(path="/scenes/valley", scene_slug="valley"))
    assert r.status_code == 201
    assert client.get("/api/stats").json()["total_views"] == 2


def test_splat_load_counted_separately(client):
    client.post("/api/events", json=_event(event="splat_load"))
    doc = client.get("/api/stats").json()
    assert doc["splat_loads"] == 1
    assert doc["total_views"] == 0


def test_unique_clients_counts_distinct(client):
    client.post("/api/events", json=_event())
    client.post("/api/events", json=_event(path="/", scene_slug=None, client_id="other-client-99"))
    assert client.get("/api/stats").json()["unique_clients"] == 2


def test_bad_payload_is_422(client):
    assert client.post("/api/events", json={"path": "/", "client_id": "short"}).status_code == 422
    assert client.post("/api/events", json=_event(client_id="")).status_code == 422


def test_stats_days_param_bounds(client):
    assert len(client.get("/api/stats", params={"days": 3}).json()["daily"]) == 3
    assert client.get("/api/stats", params={"days": 0}).status_code == 422
    assert client.get("/api/stats", params={"days": 999}).status_code == 422


def test_daily_bucket_uses_display_timezone(client):
    """UTC 深夜的记录必须落在 +08 的「今天」，不能算到昨天。"""
    from datetime import datetime, timedelta, timezone

    from sqlmodel import Session

    from app.db import engine
    from app.models import PageView
    from app.routers.events import DISPLAY_TZ

    local_today = datetime.now(timezone.utc).astimezone(DISPLAY_TZ).date()
    # 本地今天 01:30 == UTC 昨天 17:30
    local_stamp = datetime.combine(local_today, datetime.min.time(), tzinfo=DISPLAY_TZ) + timedelta(
        hours=1, minutes=30
    )
    with Session(engine) as session:
        session.add(
            PageView(
                event="view",
                path="/scenes/robot-head",
                scene_slug="robot-head",
                client_id="tz-client-0001",
                created_at=local_stamp.astimezone(timezone.utc),
            )
        )
        session.commit()

    doc = client.get("/api/stats", params={"days": 3}).json()
    assert doc["daily"][-1]["date"] == local_today.isoformat()
    assert doc["daily"][-1]["views"] == 1
