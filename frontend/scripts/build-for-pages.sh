#!/usr/bin/env bash
# 构建「静态托管」版本（GitHub Pages / EdgeOne Pages 都能用）。
#
#   bash scripts/build-for-pages.sh [base路径] [后端地址]
# 例：
#   bash scripts/build-for-pages.sh /web3d-lab/                       # 纯前端（无后端，走静态兜底）
#   bash scripts/build-for-pages.sh /web3d-lab/ https://api.xxx.com   # 前端 + 远端后端
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

echo "base=$BASE  API_BASE=${API:-（空：纯静态模式，前端会自动退回 scenes-fallback.json）}"
VITE_BASE="$BASE" VITE_API_BASE="$API" npm run build

cp dist/index.html dist/404.html
echo "已生成 dist/404.html（SPA 回退）"

# 确认兜底数据真的进了产物（没有它，纯静态模式下场景库会是空的）
if [ -f dist/scenes-fallback.json ]; then
  echo "✅ dist/scenes-fallback.json 已打包（$(wc -c < dist/scenes-fallback.json) 字节）"
else
  echo "⚠️ 缺少 dist/scenes-fallback.json —— 纯静态模式下场景库会空"
fi

du -sh dist
echo "产物清单："
find dist -maxdepth 1 -mindepth 1 | sort
