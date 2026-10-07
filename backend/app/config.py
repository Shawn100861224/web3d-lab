"""集中配置：从环境变量读取，带合理默认值（本地开发零配置可跑）。"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = Path(os.environ.get("WEB3D_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("WEB3D_DB_PATH", DATA_DIR / "web3d.db"))

# —— 数据库：云上用外部 Postgres（EdgeOne 云函数的文件系统不持久，SQLite 存不住）；
# 本地/测试不给 DATABASE_URL 就落回 SQLite 文件，零配置可跑。
_RAW_DB_URL = os.environ.get("DATABASE_URL", "").strip()
if _RAW_DB_URL:
    # SQLAlchemy 需要一个具体驱动：把裸的 postgres(ql):// 指到 psycopg2
    if _RAW_DB_URL.startswith("postgres://"):
        _RAW_DB_URL = _RAW_DB_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif _RAW_DB_URL.startswith("postgresql://"):
        _RAW_DB_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL = _RAW_DB_URL
else:
    DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# —— API 前缀：常规部署是 /api；EdgeOne 云函数会先把文件系统路由前缀（/api）剥掉
# 再交给 FastAPI，所以云上设 WEB3D_API_PREFIX=""（空串）。
API_PREFIX = os.environ.get("WEB3D_API_PREFIX", "/api").rstrip("/")

# 前端 dev server 端口，CORS 白名单
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "WEB3D_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

APP_NAME = "web3d-lab API"
APP_VERSION = "0.1.0"
