#!/usr/bin/env bash
# 组装 EdgeOne 云函数部署包 = 前端静态产物 + cloud-functions/（云函数入口）+ 后端包
#
# 为什么需要这一步：
#   1) 云函数要跟静态站同一个项目同一个域（同源免 CORS）；
#   2) EdgeOne 会扫描部署包里所有含 `app = FastAPI(...)` 的 .py 并注册成公开路由，
#      所以后端包以「辅助模块」身份随包上传（web3d_app/），全包只有入口文件创建实例；
#   3) deploy/ 是构建产物，不进 git（cloud/ 与 backend/app 才是源码）。
#
# 用法：bash scripts/build-cloud-bundle.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/deploy/cloud"

rm -rf "$OUT"
mkdir -p "$OUT"

cp -r "$ROOT/frontend/dist-edgeone/." "$OUT/"
cp -r "$ROOT/cloud/cloud-functions" "$OUT/cloud-functions"
cp -r "$ROOT/backend/app" "$OUT/web3d_app"
find "$OUT" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# 自检：包里除入口文件外，不允许出现模块级的 `app = FastAPI(` 写法
LEAKS="$(grep -rn "^app = FastAPI\|^app = " "$OUT" --include=*.py | grep -v "cloud-functions/api/index.py" || true)"
if [ -n "$LEAKS" ]; then
  echo "❌ 部署包里发现会被误注册成路由的模块级 app 赋值：" >&2
  echo "$LEAKS" >&2
  exit 1
fi

echo "✅ 部署包就绪：$OUT"
echo "   入口：cloud-functions/api/index.py  依赖：cloud-functions/requirements.txt"
du -sh "$OUT" | sed 's/^/   体积：/'
