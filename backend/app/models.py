"""数据模型：3DGS 场景的元数据 + 训练指标。

字段都对得上真实训练产物（gsplat/nerfstudio 的 eval 输出），不是拍脑袋造的：
`psnr/ssim/lpips` 来自测试集评估，`train_seconds/gpu_mem_mb` 来自训练日志，
`num_points/sh_degree` 来自导出的 .spz/.ply 头部。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SceneBase(SQLModel):
    slug: str = Field(index=True, unique=True, max_length=80)
    title: str = Field(max_length=120)
    summary: str = Field(default="", max_length=400)

    # 方法（模块 7 的方法对比页按这个字段分组）
    technique: str = Field(default="3DGS", max_length=40)
    # 来源：self-trained（自己训的）/ sample（官方示例，用于先打通链路）
    source: str = Field(default="self-trained", max_length=40)

    # 几何/训练参数
    num_points: int | None = Field(default=None, ge=0)
    sh_degree: int | None = Field(default=None, ge=0, le=4)
    iterations: int | None = Field(default=None, ge=0)
    train_seconds: int | None = Field(default=None, ge=0)
    gpu_mem_mb: int | None = Field(default=None, ge=0)
    capture_device: str | None = Field(default=None, max_length=80)
    capture_views: int | None = Field(default=None, ge=0)

    # 测试集指标
    psnr: float | None = None
    ssim: float | None = None
    lpips: float | None = None

    # 资产
    asset_url: str = Field(max_length=400)
    asset_format: str = Field(default="spz", max_length=10)
    thumbnail_url: str | None = Field(default=None, max_length=400)

    license: str = Field(default="CC BY-NC 4.0", max_length=80)
    featured: bool = Field(default=False)
    published: bool = Field(default=True)


class Scene(SceneBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class SceneCreate(SceneBase):
    """POST /api/scenes 的入参（训练管线模块 8 回写指标时也用它）。"""


class ScenePublic(SceneBase):
    id: int
    created_at: datetime
    updated_at: datetime


class SceneList(SQLModel):
    total: int
    items: list[ScenePublic]
