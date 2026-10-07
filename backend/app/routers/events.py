"""访问统计：POST /api/events 写事件，GET /api/stats 读汇总。

设计取舍：
- 只存「浏览器族 + 访客随机 ID」，不留 IP、不留完整 UA —— 统计够用，隐私面最小。
- 同一 (client_id, event, path) 在 30 秒内重复上报视为同一次（前端 StrictMode 双挂载、
  刷新、快速来回切页都会重复触发），返回 202 + deduped=true，不入库。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Request, Response
from sqlmodel import Session, func, select

from ..config import API_PREFIX
from ..db import engine
from ..models import DailyStat, EventAck, EventIn, PageView, Scene, SceneStat, StatsOut

router = APIRouter(prefix=f"{API_PREFIX}", tags=["stats"])

DEDUPE_WINDOW_SECONDS = 30
DAILY_WINDOW_DAYS = 14

# 日桶按「显示时区」切天。存的是 UTC，但如果直接按 UTC 分桶，国内凌晨 0–8 点的访问
# 会落到前一天那根柱子上，看起来像统计坏了。固定 +8 够用且不引入 tzdata 依赖。
DISPLAY_TZ = timezone(timedelta(hours=8))


def ua_family(user_agent: str) -> str:
    """把 UA 收敛成浏览器族，避免存整串指纹。"""
    ua = user_agent or ""
    family = "other"
    for marker, name in (
        ("Edg/", "Edge"),
        ("OPR/", "Opera"),
        ("Chrome/", "Chrome"),
        ("Firefox/", "Firefox"),
        ("Safari/", "Safari"),
        ("curl/", "curl"),
        ("python-httpx", "httpx"),
        ("node", "node"),
    ):
        if marker in ua:
            family = name
            break
    if "Mobile" in ua or "Android" in ua:
        family += " Mobile"
    return family


@router.post("/events", response_model=EventAck)
def create_event(payload: EventIn, request: Request, response: Response) -> EventAck:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        since = now - timedelta(seconds=DEDUPE_WINDOW_SECONDS)
        recent = session.exec(
            select(PageView)
            .where(PageView.client_id == payload.client_id)
            .where(PageView.event == payload.event)
            .where(PageView.path == payload.path)
            .where(PageView.created_at >= since)
        ).first()
        if recent is not None:
            # 已记过：202 Accepted，不入库（前端 StrictMode 双挂载会重复触发）
            response.status_code = 202
            return EventAck(ok=True, id=recent.id, deduped=True)

        row = PageView(
            event=payload.event,
            path=payload.path,
            scene_slug=payload.scene_slug,
            client_id=payload.client_id,
            referrer=payload.referrer,
            ua_family=ua_family(request.headers.get("user-agent", "")),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        response.status_code = 201
        return EventAck(ok=True, id=row.id, deduped=False)


@router.get("/stats", response_model=StatsOut)
def stats(days: int = Query(default=DAILY_WINDOW_DAYS, ge=1, le=90)) -> StatsOut:
    now = datetime.now(timezone.utc)
    today_local = now.astimezone(DISPLAY_TZ).date()
    window_start = datetime.combine(
        today_local - timedelta(days=days - 1), datetime.min.time(), tzinfo=DISPLAY_TZ
    )

    with Session(engine) as session:
        total_views = session.exec(
            select(func.count()).select_from(PageView).where(PageView.event == "view")
        ).one()
        splat_loads = session.exec(
            select(func.count()).select_from(PageView).where(PageView.event == "splat_load")
        ).one()
        unique_clients = session.exec(
            select(func.count(func.distinct(PageView.client_id))).select_from(PageView)
        ).one()

        per_scene_rows = session.exec(
            select(PageView.scene_slug, func.count())
            .where(PageView.event == "view")
            .where(PageView.scene_slug.is_not(None))
            .group_by(PageView.scene_slug)
            .order_by(func.count().desc())
        ).all()
        titles = {
            slug: title
            for slug, title in session.exec(select(Scene.slug, Scene.title)).all()
        }

        window_rows = session.exec(
            select(PageView.created_at).where(PageView.event == "view").where(
                PageView.created_at >= window_start.astimezone(timezone.utc)
            )
        ).all()

    buckets: dict[str, int] = {}
    for created_at in window_rows:
        # SQLite 取回的 datetime 可能不带 tzinfo（SQLModel 存的是 naive UTC），补上再换算
        stamp = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        key = stamp.astimezone(DISPLAY_TZ).strftime("%Y-%m-%d")
        buckets[key] = buckets.get(key, 0) + 1

    daily = []
    for offset in range(days):
        day = (window_start + timedelta(days=offset)).strftime("%Y-%m-%d")
        daily.append(DailyStat(date=day, views=buckets.get(day, 0)))

    return StatsOut(
        total_views=total_views,
        unique_clients=unique_clients,
        splat_loads=splat_loads,
        per_scene=[
            SceneStat(slug=slug, title=titles.get(slug), views=views)
            for slug, views in per_scene_rows
            if slug is not None
        ],
        daily=daily,
        generated_at=now,
    )
