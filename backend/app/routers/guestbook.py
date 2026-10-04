"""留言板：POST /api/guestbook 写、GET /api/guestbook 读。

三个要点：
1. **存原文、渲染层转义**。后端不预先 HTML 转义（否则「<」会被存成「&lt;」，
   数据就脏了）；前端用 React 默认转义输出，模块 9 的 Playwright 会断言
   `<script>` 注入只以文本形式出现、DOM 里不存在可执行的 script 节点。
2. **限流**：滑动窗口，同一 client_id 10 分钟 3 条、1 小时 10 条，超了返回 429 +
   `retry_after_seconds`，让前端能提示「多久后再来」。
3. **不回传 client_id**：响应模型 `GuestbookPublic` 里没有这个字段，避免把访客标识散出去。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import Session, func, select

from ..db import engine
from ..models import GuestbookEntry, GuestbookIn, GuestbookList, GuestbookPublic

router = APIRouter(prefix="/api/guestbook", tags=["guestbook"])

RATE_WINDOWS: tuple[tuple[int, int], ...] = ((10, 3), (60, 10))  # (分钟, 条数上限)


def _too_many(session: Session, client_id: str) -> int | None:
    """返回还需等待的秒数；没超限返回 None。"""
    now = datetime.now(timezone.utc)
    for minutes, limit in RATE_WINDOWS:
        window_start = now - timedelta(minutes=minutes)
        count = session.exec(
            select(func.count())
            .select_from(GuestbookEntry)
            .where(GuestbookEntry.client_id == client_id)
            .where(GuestbookEntry.created_at >= window_start)
        ).one()
        if count >= limit:
            oldest = session.exec(
                select(GuestbookEntry.created_at)
                .where(GuestbookEntry.client_id == client_id)
                .where(GuestbookEntry.created_at >= window_start)
                .order_by(GuestbookEntry.created_at)
            ).first()
            if oldest is None:
                return minutes * 60
            stamp = oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc)
            retry = int((stamp + timedelta(minutes=minutes) - now).total_seconds()) + 1
            return max(retry, 1)
    return None


@router.get("", response_model=GuestbookList)
def list_entries(
    scene_slug: str | None = Query(default=None, description="只看某个场景下的留言"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> GuestbookList:
    filters = [GuestbookEntry.hidden == False]  # noqa: E712 — SQLModel 需要显式比较
    if scene_slug:
        filters.append(GuestbookEntry.scene_slug == scene_slug)

    with Session(engine) as session:
        total = session.exec(
            select(func.count()).select_from(GuestbookEntry).where(*filters)
        ).one()
        rows = session.exec(
            select(GuestbookEntry)
            .where(*filters)
            .order_by(GuestbookEntry.created_at.desc(), GuestbookEntry.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    return GuestbookList(total=total, items=[GuestbookPublic.model_validate(r) for r in rows])


@router.post("", response_model=GuestbookPublic, status_code=status.HTTP_201_CREATED)
def create_entry(payload: GuestbookIn, response: Response) -> GuestbookPublic:
    with Session(engine) as session:
        retry_after = _too_many(session, payload.client_id)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"留言太频繁，请 {retry_after} 秒后再试",
                headers={"Retry-After": str(retry_after)},
            )
        row = GuestbookEntry(
            name=payload.name.strip(),
            message=payload.message.strip(),
            scene_slug=payload.scene_slug,
            client_id=payload.client_id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return GuestbookPublic.model_validate(row)
