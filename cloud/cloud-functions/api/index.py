"""EdgeOne 云函数入口（唯一入口）。

文件系统路由：本文件位于 `cloud-functions/api/index.py` → 承接 `/api/*`。
平台会**先剥掉 `/api` 前缀**再交给 FastAPI（已实测），所以云端需要把
`WEB3D_API_PREFIX` 设为空串（控制台/CLI 不接受空值，故设 `"/"`，config 里会 rstrip 掉）
—— 这样 FastAPI 内部的 `/scenes` 正好匹配浏览器请求的 `/api/scenes`。

⚠️ 布局约束（实测踩坑，别再动）：
  1. 后端的 `web3d_app/` 包必须放在 `cloud-functions/` **里面**。平台构建器只把
     `cloud-functions/` 打进函数包；放在部署包根目录时运行时报
     `No module named 'web3d_app'`，而平台对外返回的是 **404 而不是 500**，极难定位。
  2. 包内不能出现模块级的 `app = FastAPI(...)`；只有本文件创建实例。
     （注：经 Content-Type 判定，平台只注册 `cloud-functions/` 下的入口文件，
     根目录的辅助模块不会被注册；但保持"唯一入口"仍是更安全的写法。）
"""

import sys
from pathlib import Path

# 把包含 web3d_app 包的目录加入搜索路径。不同构建阶段目录层级会变，
# 所以按「往上找带 web3d_app 的目录」来定位，而不是写死 parents[N]。
_HERE = Path(__file__).resolve()
for _cand in (*_HERE.parents, Path.cwd()):
    if (_cand / "web3d_app").is_dir():
        sys.path.insert(0, str(_cand))
        break

from web3d_app.main import create_app  # noqa: E402

app = create_app()
