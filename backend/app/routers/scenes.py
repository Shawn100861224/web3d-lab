"""GET/POST /api/scenes —— 场景库的元数据接口。

模块 2 的验收就落在这里：空库要返回 200 + `{"total":0,"items":[]}`（不是 404），
有数据时返回预期 JSON；列表支持 technique / featured / 分页过滤。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session, func, select

from ..db import engine
from ..models import Scene, SceneCreate, SceneList, ScenePublic

router = APIRouter(prefix="/api/scenes", tags=["scenes"])


@router.get("", response_model=SceneList)
def list_scenes(
    technique: str | None = Query(default=None, description="按方法过滤，如 3DGS / 2DGS"),
    featured: bool | None = Query(default=None, description="只看首页精选"),
    published: bool = Query(default=True, description="默认只返回已发布场景"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SceneList:
    filters = [Scene.published == published]
    if technique:
        filters.append(Scene.technique == technique)
    if featured is not None:
        filters.append(Scene.featured == featured)

    with Session(engine) as session:
        total = session.exec(select(func.count()).select_from(Scene).where(*filters)).one()
        rows = session.exec(
            select(Scene)
            .where(*filters)
            .order_by(Scene.featured.desc(), Scene.created_at.desc(), Scene.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    return SceneList(total=total, items=[ScenePublic.model_validate(r) for r in rows])


@router.get("/{slug}", response_model=ScenePublic)
def get_scene(slug: str) -> ScenePublic:
    with Session(engine) as session:
        row = session.exec(select(Scene).where(Scene.slug == slug)).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"scene '{slug}' not found")
    return ScenePublic.model_validate(row)


@router.post("", response_model=ScenePublic, status_code=status.HTTP_201_CREATED)
def create_scene(payload: SceneCreate) -> ScenePublic:
    with Session(engine) as session:
        clash = session.exec(select(Scene).where(Scene.slug == payload.slug)).first()
        if clash is not None:
            raise HTTPException(status_code=409, detail=f"slug '{payload.slug}' already exists")
        row = Scene.model_validate(payload)
        session.add(row)
        session.commit()
        session.refresh(row)
    return ScenePublic.model_validate(row)
