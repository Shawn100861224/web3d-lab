#!/usr/bin/env bash
# 构建「静态托管」版本（GitHub Pages / EdgeOne Pages 都能用）。
#
#   bash scripts/build-for-pages.sh [base路径] [后端地址] [站点根地址]
# 例：
#   bash scripts/build-for-pages.sh /web3d-lab/                       # 纯前端（无后端，走静态兜底）
#   bash scripts/build-for-pages.sh /web3d-lab/ https://api.xxx.com   # 前端 + 远端后端
#   bash scripts/build-for-pages.sh /web3d-lab/ "" https://shawn100861224.github.io/web3d-lab
#     ↑ 第三个参数是「站点根地址」，用来给每个场景深链写自己的分享卡片（og:image 必须绝对地址）。
#       不传时默认按本仓库的 GitHub Pages 地址，本地/其他部署请显式传。
#
# 三件必须做的事：
#   1. base 设成子路径，否则 GH Pages 上 JS/CSS 全 404；
#   2. 把 index.html 复制成 404.html —— GH Pages 没有 SPA 回退，
#      直接打开 /scenes/valley 会 404，靠这个文件兜住（react-router 再接管路由）；
#   3. 明确打印是否带后端，避免"发上去才发现接口是死的"。
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${1:-/}"
API="${2:-}"
# 站点根地址：给每个场景深链写自己的分享卡片（og:image 要绝对地址，爬虫不解析相对路径）
ORIGIN="${3:-https://shawn100861224.github.io/web3d-lab}"

echo "base=$BASE  API_BASE=${API:-（空：纯静态模式，前端会自动退回 scenes-fallback.json）}"
VITE_BASE="$BASE" VITE_API_BASE="$API" npm run build

cp dist/index.html dist/404.html
echo "已生成 dist/404.html（SPA 回退）"

# ---- 深链要返回 200，而不是 404 ----
# GitHub Pages 对不存在的路径一律返回 404（再用 404.html 承载 SPA）：页面能渲染，
# 但状态码难看，某些链接预览/校验会判失败。解法：为已知路由生成**真实目录**，
# 每个目录里放一份 index.html —— 这样 /scenes/ 、/scenes/fireplace/ 都是 200。
for r in scenes methods about guestbook projects; do
  mkdir -p "dist/$r"
  cp dist/index.html "dist/$r/index.html"
done
# 挑一个能用的解释器：Windows 上 python 是真的、python3 往往是商店别名占位符；
# Ubuntu CI 上反过来（只有 python3）。所以先找 python，能用再退回 python3。
PY_BIN="$(command -v python || command -v python3)"
if ! "$PY_BIN" -c "pass" >/dev/null 2>&1; then PY_BIN="$(command -v python3)"; fi
"$PY_BIN" scripts/make_deep_link_dirs.py dist --origin "$ORIGIN"

# 确认兜底数据真的进了产物（没有它，纯静态模式下场景库会是空的）
if [ -f dist/scenes-fallback.json ]; then
  echo "✅ dist/scenes-fallback.json 已打包（$(wc -c < dist/scenes-fallback.json) 字节）"
else
  echo "⚠️ 缺少 dist/scenes-fallback.json —— 纯静态模式下场景库会空"
fi
if [ -f dist/guestbook-fallback.json ]; then
  echo "✅ dist/guestbook-fallback.json 已打包（留言快照）"
else
  echo "⚠️ 缺少 dist/guestbook-fallback.json —— 静态模式下留言板会是空的"
fi

du -sh dist
echo "产物清单："
find dist -maxdepth 1 -mindepth 1 | sort
