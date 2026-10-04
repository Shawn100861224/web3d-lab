#!/usr/bin/env bash
# 构建到指定输出目录（绕开 dist/ 被外部进程占用的问题）
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-dist2}"
BASE="${2:-/web3d-lab/}"
rm -rf "$OUT"
VITE_BASE="$BASE" ./node_modules/.bin/vite build --outDir "$OUT"
cp "$OUT/index.html" "$OUT/404.html"
echo "--- $OUT 内容 ---"
ls "$OUT"
echo "--- index.html 里的资源路径（应为 $BASE 前缀）---"
grep -o '\(src\|href\)="[^"]*assets[^"]*"' "$OUT/index.html" | head -3
