#!/usr/bin/env bash
# refresh-readme-shots.sh —— 重新生成 README 里的两张线上截图（docs/screenshots/01-home.png、02-scenes.png）
#
# 为什么需要它：README 顶上那两张图是**线上站的实拍**，站点一改（新场景、改版、换文案）它们就过时，
# 而这一步没有任何构建流程会替你做。上线之后顺手跑一遍即可，所以把它做成一条命令。
#
# 用法：
#   bash scripts/refresh-readme-shots.sh            # 覆盖 docs/screenshots/ 里的两张图
#   bash scripts/refresh-readme-shots.sh /tmp/out   # 输出到别处（自检用，不弄脏仓库）
#
# 踩过的坑（别改回去）：
#   * 免安装的无头 Edge 就能截图，不必装 Playwright；但 **不加 --disable-gpu 时 WebGL 会走软件渲染**，
#     截 3D 查看器页会得到空白/半渲染画布 ✗ —— 所以本脚本只截「首页」与「场景库」这类非 WebGL 页面。
#     真要截查看器页，得用真机浏览器（或直接用 GPU 渲染图，见 docs/screenshots/03-render-vs-photo.jpg）。
#   * Edge 是原生程序：**必须给原生路径**（`D:/...`），且命令行里的中文会被编码搞坏 ✗（本脚本里没有中文路径）。
#   * `--virtual-time-budget` 要够长，否则首页的访问统计/场景卡片还没拉到接口就截图了。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/docs/screenshots}"
SITE="${SITE:-https://www.shawnlab.cn}"
SIZE="${SIZE:-1600,1000}"
WAIT="${WAIT:-18000}"

BROWSER=""
for c in \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "$(command -v msedge || true)" "$(command -v google-chrome || true)"
do
  [ -n "$c" ] && [ -x "$c" ] && { BROWSER="$c"; break; }
done
[ -n "$BROWSER" ] || { echo "❌ 没找到 Edge/Chrome，装一个或改本脚本里的路径"; exit 1; }
mkdir -p "$OUT"
echo "浏览器：$BROWSER"
echo "站点：$SITE  ·  视口：$SIZE  ·  等待：${WAIT}ms  ·  输出：$OUT"

shoot() {  # shoot <文件名> <路径>
  local name="$1" path="$2"
  "$BROWSER" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="$SIZE" --virtual-time-budget="$WAIT" \
    --screenshot="$(cygpath -w "$OUT/$name" 2>/dev/null || echo "$OUT/$name")" \
    "$SITE$path" >/dev/null 2>&1
  local kb=$(( $(stat -c%s "$OUT/$name") / 1024 ))
  echo "  ✅ $name（${kb} KB）  ← $SITE$path"
  # 注意：别写成 `[ ... ] && echo` —— 条件为假时整条命令返回非零，配合 set -e 会让脚本静默退出（踩过）
  if [ "$kb" -lt 60 ]; then
    echo "  ⚠️ 只有 ${kb} KB，可能截到了空页/加载中，请打开图片确认"
  fi
}

shoot "01-home.png"   "/"
shoot "02-scenes.png" "/scenes"

echo
echo "提示：改完记得顺手看一眼的三件事（都属于「GitHub 页面同步」）——"
echo "  1) README 里的场景数/资产表是否还准（本站场景数从 /api/scenes 实时取，但 README 是写死的）"
echo "  2) docs/作品说明.html 的数字（改过就用 bash scripts/build-doc.sh 重导 PDF）"
echo "  3) 仓库 About / Social preview（只能在网页 Settings 里改，没有 API）"
