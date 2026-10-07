"""EdgeOne 云函数入口（唯一入口）。

文件系统路由：本文件位于 `cloud-functions/api/index.py` → 承接 `/api/*`。
平台会**先剥掉 `/api` 前缀**再交给 FastAPI（已实测），所以云端需要把
`WEB3D_API_PREFIX` 设为空串 —— 这样 FastAPI 内部的 `/scenes` 正好匹配
浏览器请求的 `/api/scenes`。

⚠️ 整个部署包里只有这一个文件创建 FastAPI 实例。后端代码（web3d_app/）
作为辅助模块随包上传：实测辅助目录里若出现 `app = FastAPI(...)` 会被平台
注册成一个公开路由（`/web3d_app/main/...` 可直连），所以 `create_app()` 工厂
是必需的，不是风格问题。
"""

import sys
from pathlib import Path

# 部署包根目录（cloud-functions/api/index.py → 上三级）加入模块搜索路径，
# 才能 import 到随包上传的 web3d_app 包。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from web3d_app.main import create_app  # noqa: E402

app = create_app()
