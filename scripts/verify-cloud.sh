#!/usr/bin/env bash
# 验证 EdgeOne 线上后端 + 静态站。可重复运行：
#
#   bash scripts/verify-cloud.sh                        # 默认验 https://www.shawnlab.cn
#   bash scripts/verify-cloud.sh https://xxx.edgeone.dev  # 验预览域名
#
# 三条设计要点（都是踩过坑才有的）：
#   1) **必须看 Content-Type**：静态站对未知路径做 SPA 兜底，返回 200 + HTML，
#      只看状态码会把"路由泄漏"和"正常兜底"混淆（本项目真踩过一次）。
#   2) **必带缓存破坏参数**：CDN 可能缓存 GET 响应。
#   3) **带一条随机路径做对照**：没有对照组，就无法区分"接口存在"与"兜底返回"。
set -uo pipefail

DOMAIN="${1:-https://www.shawnlab.cn}"
T="${LOCALAPPDATA:-/tmp}/Temp/w3d-verify"; mkdir -p "$T"
PASS=0; FAIL=0

get() {  # get <path> ; 打印 "状态码|Content-Type|正文前 90 字符"
  local code ct body
  code=$(curl -s --ssl-no-revoke -m 40 -D "$T/h" -o "$T/b" -w '%{http_code}' "$DOMAIN$1")
  ct=$(grep -i '^content-type' "$T/h" | tr -d '\r' | awk '{print $2}' | cut -d';' -f1)
  body=$(head -c 90 "$T/b" | tr -d '\n')
  echo "$code|${ct:-none}|$body"
}

check() {  # check <名称> <路径> <期望: json|html|notjson> <要包含的字符串(可空)>
  local name="$1" path="$2" kind="$3" needle="${4:-}"
  local out code ct body
  out=$(get "$path"); code="${out%%|*}"; ct="$(echo "$out" | cut -d'|' -f2)"; body="$(echo "$out" | cut -d'|' -f3-)"
  local ok=1 why=""
  case "$kind" in
    json)    [[ "$ct" == application/json ]] || { ok=0; why="Content-Type 应为 json，实为 $ct"; } ;;
    html)    [[ "$ct" == text/html ]] || { ok=0; why="Content-Type 应为 html，实为 $ct"; } ;;
    notjson) [[ "$ct" != application/json ]] || { ok=0; why="竟然返回了 JSON —— 辅助包被注册成了公开路由！"; } ;;
  esac
  # 正文断言看完整正文，不要只看前 90 字符（首页前 90 字符全是 meta 标签，曾误判为失败）
  if [ -n "$needle" ] && ! grep -qF -- "$needle" "$T/b"; then ok=0; why="正文缺少 '$needle'"; fi
  if [ "$ok" = 1 ]; then PASS=$((PASS+1)); printf '  ✅ %-28s %s  %s\n' "$name" "$code" "$body"
  else FAIL=$((FAIL+1)); printf '  ❌ %-28s %s  %s\n     原因：%s\n' "$name" "$code" "$body" "$why"; fi
}

CB="cb=$RANDOM$RANDOM"
echo "目标：$DOMAIN"
echo "── 后端接口（云函数，应返回 JSON）──"
check "健康检查"        "/api/health?$CB"            json "web3d-lab API"
# 场景数不写死：站点会加场景，写死数字会让验收脚本自己变成假警报（这里只断言字段在）。
check "场景列表"        "/api/scenes?limit=100&$CB"  json '"total":'
check "留言板列表"      "/api/guestbook?limit=5&$CB" json '"items"'
check "访问统计"        "/api/stats?days=14&$CB"     json '"per_scene"'
echo "── 对照组与泄漏检查 ──"
check "随机路径(应兜底为 html)" "/zz-nope-$RANDOM"    html
# 泄漏检查要打在 /api 之外：/api/* 现在本来就该由函数处理（返回 JSON 是正常的）。
check "辅助包是否泄漏为公开路由" "/web3d_app/main/api/health" notjson
echo "── 静态站 ──"
check "首页"            "/?$CB"                      html "web3d-lab"

echo
echo "结果：通过 $PASS 项，失败 $FAIL 项"
[ "$FAIL" = 0 ] || exit 1
