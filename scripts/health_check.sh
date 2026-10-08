#!/usr/bin/env bash
# 站点健康看门狗：一切正常时**不输出任何内容**（配合 Hermes 的 no_agent 定时任务 =
# 正常时静默、异常时才提醒），出问题就打印一段可读的告警。
#
#   bash scripts/health_check.sh          # 手动跑：一切正常则无事发生
#
# 检查项（主站，EdgeOne 全球可用区）：
#   1. 首页可访问且是 HTML（不是错误页）
#   2. /api/health 返回 ok 且 db 是 postgres（后端 + 数据库都活着）
#   3. /api/scenes 场景数 > 0（Neon 没被清空 / 数据还在）
#   4. 一个真实资产可下载且字节数合理（CDN 上的 .splat 没坏）
#   5. 首页引用的 JS 资源可下载（部署产物完整，不是半包）
#
# 注意：**镜像（GitHub Pages）不在此检查** —— 从国内直连它本来就不稳，
# 放进来自动检查会产生假警报。需要时手动验：
#   curl -s --proxy http://127.0.0.1:7897 -o /dev/null -w '%{http_code}' \
#     https://shawn100861224.github.io/web3d-lab/
set -uo pipefail

SITE="${1:-https://www.shawnlab.cn}"
PROBLEMS=()

code_of() { curl -s --ssl-no-revoke -m 25 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }
body_of() { curl -s --ssl-no-revoke -m 25 "$1" 2>/dev/null; }

# 1) 首页
home_code="$(code_of "$SITE/")"
if [ "$home_code" != "200" ]; then
  PROBLEMS+=("首页返回 $home_code（期望 200）：$SITE/")
elif ! body_of "$SITE/" | grep -q "<!doctype html"; then
  PROBLEMS+=("首页返回了 200，但内容不是 HTML（可能是错误页或空包）")
fi

# 2) 后端健康 + 数据库
health="$(body_of "$SITE/api/health")"
if ! printf '%s' "$health" | grep -q '"status":"ok"'; then
  PROBLEMS+=("/api/health 异常：${health:0:160}")
elif ! printf '%s' "$health" | grep -q '"db":"postgres'; then
  PROBLEMS+=("/api/health 里数据库不是 postgres（可能退回了本地 SQLite）：${health:0:160}")
fi

# 3) 场景数（数据库内容还在）
scenes="$(body_of "$SITE/api/scenes?limit=100")"
total="$(printf '%s' "$scenes" | python -c 'import json,sys
try:
    print(json.load(sys.stdin).get("total", 0))
except Exception:
    print(-1)' 2>/dev/null)"
if [ "${total:-0}" -le 0 ] 2>/dev/null; then
  PROBLEMS+=("/api/scenes 场景数为 ${total:-(取不到)}（期望 >0）")
fi

# 4) 资产可下载且字节数合理
#    路径坑（本项目因此误判过两次）：curl 是**原生 Windows 程序**，认不出 MSYS 路径 ——
#    `/dev/null`、MSYS bash 里的 `TEMP=/tmp` 都会让它写不进去，而 %{size_download} 会**静默**变成 0
#    （看起来像 404，其实文件是好的）。修法：有 cygpath 就把它转成 Windows 路径。
asset="$SITE/demo/shoe-37.splat"
tmp_dir="${TEMP:-${TMPDIR:-.}}"
command -v cygpath >/dev/null 2>&1 && tmp_dir="$(cygpath -w "$tmp_dir")"
tmp_asset="$tmp_dir/health_asset_$$.bin"
asset_bytes="$(curl -s --ssl-no-revoke -m 60 -o "$tmp_asset" -w '%{size_download}' "$asset" 2>/dev/null)"
rm -f "$tmp_asset"
if [ "${asset_bytes:-0}" -lt 500000 ] 2>/dev/null; then
  PROBLEMS+=("资产 $asset 只有 ${asset_bytes:-0} 字节（期望 >500KB，可能 404/被截断）")
fi

# 5) 首页引用的第一个 JS 产物存在（部署包完整）
js_path="$(body_of "$SITE/" | grep -oE 'src="/assets/[^"]+\.js"' | head -1 | sed 's/src="//; s/"$//')"
if [ -n "$js_path" ]; then
  js_code="$(code_of "$SITE$js_path")"
  [ "$js_code" != "200" ] && PROBLEMS+=("首页引用的 JS $js_path 返回 $js_code（部署包不完整？）")
fi

if [ "${#PROBLEMS[@]}" -eq 0 ]; then
  exit 0   # 一切正常：静默
fi

echo "⚠️ 站点健康检查发现问题（$(date '+%Y-%m-%d %H:%M')）："
for p in "${PROBLEMS[@]}"; do echo "  · $p"; done
echo
echo "排查建议：先看 https://www.shawnlab.cn/ 与 /api/health；"
echo "后端在 EdgeOne Cloud Functions + Neon Postgres，"
echo "最近一次部署可用 edgeone makers deploy ./deploy/cloud -n web3d-lab 重发。"
exit 1
