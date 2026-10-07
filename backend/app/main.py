"""web3d-lab 后端应用工厂。

模块 1（脚手架）只要求：一条命令起服务，`/api/health` 返回预期 JSON。

⚠️ 这里**刻意没有模块级的 `app = FastAPI(...)`**：EdgeOne 云函数会扫描部署包里
所有含该写法的 .py 文件并把它们各注册成一个公开路由（已实测：放在辅助目录里也会
被注册，`/web3d_app/main/...` 能直接访问）。改成工厂函数后，整个部署包里只有入口
文件 `cloud-functions/api/index.py` 会创建实例，后端代码才能安全地随包上传。
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import API_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS, DB_PATH
from .db import init_db
from .routers import events, guestbook, scenes

STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# 元信息路由（健康检查等）。用 API_PREFIX 拼路径：本地是 /api/health，
# 云上被云函数剥掉 /api 后为 /health。
meta = APIRouter(tags=["meta"])


@meta.get(f"{API_PREFIX}/health")
def health() -> dict:
    """存活探针：前端启动时拿它证明链路通了。"""
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "db": DB_PATH.name,
        "uptime_seconds": round(time.time() - STARTED_AT, 3),
    }


@meta.get(f"{API_PREFIX}/")
def api_index() -> dict:
    return {"service": APP_NAME, "version": APP_VERSION, "docs": "/docs"}


@meta.get("/")
def root() -> JSONResponse:
    return JSONResponse({"service": APP_NAME, "version": APP_VERSION, "health": f"{API_PREFIX}/health"})


def create_app() -> FastAPI:
    """构造 FastAPI 应用（本地 uvicorn、pytest、云函数入口都走这里）。"""
    service = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

    service.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    service.include_router(scenes.router)
    service.include_router(events.router)
    service.include_router(guestbook.router)
    service.include_router(meta)

    return service
