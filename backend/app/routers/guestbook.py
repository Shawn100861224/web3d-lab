"""留言板：POST /api/guestbook 写、GET /api/guestbook 读。

四个要点：
1. **存原文、渲染层转义**。后端不预先 HTML 转义（否则「<」会被存成「&lt;」，
   数据就脏了）；前端用 React 默认转义输出，模块 9 的 Playwright 会断言
   `<script>` 注入只以文本形式出现、DOM 里不存在可执行的 script 节点。
2. **限流**：滑动窗口，同一 client_id 10 分钟 3 条、1 小时 10 条，超了返回 429 +
   `retry_after_seconds`，让前端能提示「多久后再来」。
3. **反垃圾：不收带链接的留言**（见下方说明）。限流挡不住换浏览器/换网络的刷子，
   而这个留言板是公开可见的、目前又没有后台审核界面，一旦被灌链接就只能由维护者
   手工删库。所以规则做成「宁可误杀」：各种形式的链接一律拒收，并在提示里给出
   替代联系方式；但**邮箱地址照收**（同学留联系方式是正常需求）。
4. **不回传 client_id**：响应模型 `GuestbookPublic` 里没有这个字段，避免把访客标识散出去。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import Session, func, select

from ..config import API_PREFIX
from ..db import engine
from ..models import GuestbookEntry, GuestbookIn, GuestbookList, GuestbookPublic

router = APIRouter(prefix=f"{API_PREFIX}/guestbook", tags=["guestbook"])

RATE_WINDOWS: tuple[tuple[int, int], ...] = ((10, 3), (60, 10))  # (分钟, 条数上限)

CONTACT_EMAIL = "18711505157@163.com"

# 先把邮箱挖掉再判链接：避免把「留个邮箱」这种正常留言当成垃圾。
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# 链接的变体都要覆盖：http(s)://、www.、裸域名，以及用空格或全角点（。．）拆开的写法。
_LINK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"https?\s*[:：]\s*/{2}", re.IGNORECASE),
    re.compile(r"\bwww\s*[.。．]\s*\w", re.IGNORECASE),
    re.compile(
        r"\b[\w-]+\s*[.。．]\s*"
        r"(?:com|cn|net|org|xyz|top|info|io|me|cc|tv|vip|shop|site|online|app|dev|ru|tk|ml|ga|link)\b",
        re.IGNORECASE,
    ),
)


def contains_link(text: str) -> bool:
    """判定文本里是否含链接（邮箱不算）。"""
    probe = _EMAIL_RE.sub(" ", text)
    return any(p.search(probe) for p in _LINK_PATTERNS)


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
    # 反垃圾先判（纯字符串、不碰数据库）：带链接的留言直接拒收
    if contains_link(f"{payload.name} {payload.message}"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"留言里暂时不能带链接（防刷）。想分享链接可以直接发我邮箱：{CONTACT_EMAIL}",
        )

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
