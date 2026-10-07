"""数据库会话与建表。模块 2 起在这里追加 SQLModel 表。"""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL, IS_SQLITE

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # 云函数是短生命周期实例：小连接池 + 用前探活（对 Neon 这类会休眠的库尤其重要）
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=2,
        pool_recycle=300,
    )


def init_db() -> None:
    # 导入模型模块以注册元数据（SQLModel.metadata 需要被 import 过才认识表）
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
