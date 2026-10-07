"""集中配置：从环境变量读取，带合理默认值（本地开发零配置可跑）。"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = Path(os.environ.get("WEB3D_DATA_DIR", BASE_DIR / "data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # 云函数文件系统是**只读**的（EdgeOne 实测：/var/user 只读，导入时建目录会直接
    # OSError 让整个应用起不来，而平台对外只回 404）。只有本地 SQLite 才需要这个目录，
    # 云端走 Postgres 用不到它，所以静默跳过。
    pass

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

# pg8000 是纯 Python 驱动（云端构建机装不了编译型驱动，见 cloud-functions/requirements.txt）：
# 它不认 sslmode 查询参数，SSL 要传 ssl_context（在 db.py 里加），所以这里先把查询串去掉。
PG_USES_SSL_CONTEXT = "+pg8000" in DATABASE_URL
if PG_USES_SSL_CONTEXT and "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

# 给 /api/health 用的可读标识：云上别再显示 "web3d.db"（那会让人以为还在用 SQLite）
if IS_SQLITE:
    DB_LABEL = f"sqlite:{DB_PATH.name}"
else:
    DB_LABEL = "postgres:" + DATABASE_URL.split("@")[-1].split("/")[0].split("?")[0]

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
