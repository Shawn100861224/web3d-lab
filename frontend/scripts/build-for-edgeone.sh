#!/usr/bin/env bash
# 构建 EdgeOne Pages 版本（站点挂在子域名根目录，base 用 /）。
#
#   bash scripts/build-for-edgeone.sh [后端地址]
#
# 与 GitHub Pages 版的区别（EdgeOne 官方文档要求）：
#   * base 是 /，不是 /<repo>/；
#   * **不要**在输出根目录放 404.html —— 官方说明它会干扰 SPA 的客户端路由，
#     SPA 的 404 交给 react-router 的通配路由（我们已经加了 path="*"）。
set -euo pipefail
cd "$(dirname "$0")/.."

API="${1:-}"
rm -rf dist-edgeone
echo "API_BASE=${API:-（空：纯静态模式，前端自动退回 scenes-fallback.json）}"
VITE_BASE=/ VITE_API_BASE="$API" ./node_modules/.bin/vite build --outDir dist-edgeone

rm -f dist-edgeone/404.html   # 明确不放
echo "--- 产物 ---"
ls dist-edgeone
[ -f dist-edgeone/scenes-fallback.json ] && echo "✅ 兜底数据已打包" || echo "⚠️ 缺兜底数据"
du -sh dist-edgeone
