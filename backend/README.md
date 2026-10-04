# backend —— web3d-lab API

FastAPI + SQLModel + SQLite。当前只有模块 1 的脚手架（健康检查）。

## 起服务（一条命令）

```bash
cd D:/lab/web3d-lab/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- 健康检查：http://127.0.0.1:8000/api/health
- 交互式文档：http://127.0.0.1:8000/docs
- SQLite 落在 `backend/data/web3d.db`（`data/` 已在 .gitignore 里）

## 跑测试

```bash
cd D:/lab/web3d-lab/backend
.venv/Scripts/python.exe -m pytest tests -q
```

## 重建虚拟环境

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe --native-tls \
  --index-url https://mirrors.aliyun.com/pypi/simple/ \
  fastapi "uvicorn[standard]" sqlmodel httpx pytest
```

> 本机必须 `--native-tls` + 国内镜像，否则 uv 的 TLS 握手会失败（Clash 代理变量在场）。
