#!/usr/bin/env bash
# 重新拉取 frontend/public/demo/ 下的示例 .spz 资产。
#
# 为什么需要它：示例资产来自 sparkjs.dev 的公开示例仓库（examples/assets.json），
# 体积 1–10MB，不进 git 也不便于手传；这份脚本是可复现的来源说明。
#
# 注意（本机实测 2026-10-05）：sparkjs.dev 直连速度为 0，必须走本地代理；
# 而 npmmirror/GitHub 那类国内可达的源反过来要关代理。所以这里显式只给这一条
# 命令加代理，不污染全局环境。
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p public/demo
cd public/demo

export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7897}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7897}"

fetch() {
  local name="$1" url="$2"
  echo "==> $name"
  curl -sL --retry 3 -o "$name.spz" "$url"
  ls -la "$name.spz"
}

# 能正常渲染的（已在浏览器里逐个验证过 status=ready + 画面非空）
fetch robot-head https://sparkjs.dev/assets/splats/robot-head.spz

# 其余候选（备查，未全部验证）
# fetch penguin    https://sparkjs.dev/assets/splats/penguin.spz
# fetch cat        https://sparkjs.dev/assets/splats/cat.spz
# fetch fireplace  https://sparkjs.dev/assets/splats/fireplace.spz
# fetch valley     https://sparkjs.dev/assets/splats/valley.spz

echo
echo "校验（解压后应看到 NGSP 头）："
for f in *.spz; do printf '  %-24s ' "$f"; gzip -dc "$f" 2>/dev/null | head -c 4; echo; done
