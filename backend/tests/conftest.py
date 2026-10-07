"""测试夹具：把数据库指向测试专用文件，避免污染 backend/data/web3d.db。

必须在 `app.main` 被 import 之前设置环境变量（config 在 import 时读 env），
pytest 先加载 conftest，所以放在这里最合适。
"""

from __future__ import annotations

import os
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent / "_data"
TEST_DIR.mkdir(parents=True, exist_ok=True)
os.environ["WEB3D_DATA_DIR"] = str(TEST_DIR)
os.environ["WEB3D_DB_PATH"] = str(TEST_DIR / "test.db")

# ⚠️ 强制测试与生产库隔离（血泪教训）：
# 外层 shell 里如果残留 DATABASE_URL（例如为了跑 pg_smoke.py 而 source 过 .env），
# config 会优先用它 —— 于是 pytest 直接跑在**线上 Neon 库**上，而下面的清理夹具
# 会清空各表。2026-10-07 实际发生了一次：场景元数据被清掉，只能重新灌。
# 所以这里无条件摘掉 DATABASE_URL：pytest 永远只用测试临时 SQLite。
_leaked_url = os.environ.pop("DATABASE_URL", None)
if _leaked_url:
    print(
        "\n[conftest] 已忽略外层环境里的 DATABASE_URL"
        f"（{_leaked_url.split('@')[-1].split('/')[0]}）—— 测试只用临时 SQLite，不会碰线上库\n"
    )

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, delete  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import GuestbookEntry, PageView, Scene  # noqa: E402

app = create_app()


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    with Session(engine) as session:
        session.exec(delete(Scene))
        session.exec(delete(PageView))
        session.exec(delete(GuestbookEntry))
        session.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def scene_payload() -> dict:
    return {
        "slug": "desk-chair",
        "title": "桌面椅子（小场景）",
        "summary": "手机环拍 42 张，gsplat 训练 7k 步",
        "technique": "3DGS",
        "source": "self-trained",
        "num_points": 412_345,
        "sh_degree": 3,
        "iterations": 7000,
        "train_seconds": 642,
        "gpu_mem_mb": 5120,
        "capture_device": "Redmi K60",
        "capture_views": 42,
        "psnr": 27.84,
        "ssim": 0.8742,
        "lpips": 0.2113,
        "asset_url": "/demo/desk-chair.spz",
        "asset_format": "spz",
        "thumbnail_url": "/demo/desk-chair.jpg",
        "featured": True,
    }
