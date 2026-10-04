"""集中配置：从环境变量读取，带合理默认值（本地开发零配置可跑）。"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = Path(os.environ.get("WEB3D_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("WEB3D_DB_PATH", DATA_DIR / "web3d.db"))
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

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
