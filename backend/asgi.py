"""本地/常规部署的 ASGI 入口：`uvicorn asgi:app`。

云上（EdgeOne 云函数）用的是 `deploy/cloud/cloud-functions/api/index.py`。
这个文件不在部署包里，所以这里的模块级 `app` 不会被云函数扫描到。
"""

from app.main import create_app

app = create_app()
