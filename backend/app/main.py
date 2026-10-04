"""web3d-lab 后端入口。

模块 1（脚手架）只要求：一条命令起服务，`/api/health` 返回预期 JSON。
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import APP_NAME, APP_VERSION, CORS_ORIGINS, DB_PATH
from .db import init_db

STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """存活探针：前端启动时拿它证明链路通了。"""
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "db": DB_PATH.name,
        "uptime_seconds": round(time.time() - STARTED_AT, 3),
    }


@app.get("/api/")
def api_index() -> dict:
    return {"service": APP_NAME, "version": APP_VERSION, "docs": "/docs"}


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({"service": APP_NAME, "version": APP_VERSION, "health": "/api/health"})
