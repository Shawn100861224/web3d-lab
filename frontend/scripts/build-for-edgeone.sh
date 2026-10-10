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
# 删除旧产物。**必须确认真的删掉了**：如果有进程正占用 dist-edgeone（典型：
# 本地 `python -m http.server` 从它提供文件），Windows 上 rm 会报 Device or resource busy
# 并且**静默继续**（rm -rf 对部分失败往往仍返回 0），结果是「带着旧文件构建 + 部署残缺产物」，
# 线上表现是整站 404。血泪一次，所以这里显式检查。
rm -rf dist-edgeone 2>/dev/null || true
if [ -e dist-edgeone ]; then
  echo "❌ 删不掉 dist-edgeone —— 多半有进程正在占用它（比如本地 python -m http.server）" >&2
  echo "   先停掉占用进程再重跑： taskkill //F //IM python.exe   或关掉那个终端" >&2
  exit 1
fi
echo "API_BASE=${API:-（空：纯静态模式，前端自动退回 scenes-fallback.json）}"
VITE_BASE=/ VITE_API_BASE="$API" ./node_modules/.bin/vite build --outDir dist-edgeone

rm -f dist-edgeone/404.html   # 明确不放

# 深链目录 + 每个场景自己的分享卡片。
# 注意：EdgeOne 靠平台 SPA 兜底也能让 /scenes/x/ 返回 200，但**兜底返回的是站点 index.html**
# → 分享卡片永远不区分场景。所以要显式生成真实目录（真实文件优先于兜底）。
# ubuntu 上只有 python3、Windows 上 python 才是真的，两个都试。
PY_BIN="$(command -v python || command -v python3)"
if ! "$PY_BIN" -c "pass" >/dev/null 2>&1; then PY_BIN="$(command -v python3)"; fi
"$PY_BIN" scripts/make_deep_link_dirs.py dist-edgeone --origin "https://www.shawnlab.cn"

echo "--- 产物 ---"
ls dist-edgeone
[ -f dist-edgeone/scenes-fallback.json ] && echo "✅ 兜底数据已打包" || echo "⚠️ 缺兜底数据"
du -sh dist-edgeone

# 产物自检：入口与 assets 必须都在且非空，避免交出空壳（空壳部署上线就是整站 404）
for f in dist-edgeone/index.html dist-edgeone/assets; do
  [ -e "$f" ] || { echo "❌ 构建产物缺失：$f" >&2; exit 1; }
done
if [ -z "$(ls -A dist-edgeone/assets 2>/dev/null)" ]; then
  echo "❌ dist-edgeone/assets 是空的（构建没产出）」" >&2
  exit 1
fi
echo "✅ 产物自检通过（index.html 存在、assets 非空）"
