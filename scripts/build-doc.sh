#!/usr/bin/env bash
# build-doc.sh —— 重新生成《作品说明》PDF（docs/作品说明.html → docs/作品说明.pdf）
#
# 用法：
#   bash scripts/build-doc.sh                 # 覆盖 docs/作品说明.pdf
#   bash scripts/build-doc.sh /d/tmp/x.pdf    # 输出到别处（自检用，不弄脏仓库）
#
# 为什么这么写（都是踩过的）：
#   * 本机没有 LibreOffice / weasyprint / poppler，但 **Windows 自带 Edge 就能 print-to-pdf**，零依赖；
#   * Edge 是原生程序，不认 MSYS 路径，**命令行里的中文文件名也会被编码搞坏** →
#     输入传 percent-encoded 的 file:// URL，产物先写 ASCII 临时名、最后再 mv 成中文名；
#   * 不加 --no-pdf-header-footer 会带上 URL/日期的页眉页脚，给评审看很难看 ✗；
#   * 输出的 PDF 必须**自带文本层**（可搜索可复制）——脚本会顺手校验，避免退化成图片版。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/作品说明.html"
OUT="${1:-$ROOT/docs/作品说明.pdf}"
TMPOUT="$ROOT/docs/_build_$$.pdf"

command -v python >/dev/null 2>&1 || { echo "❌ 需要 python 做路径编码与校验"; exit 1; }
[ -f "$SRC" ] || { echo "❌ 找不到源文件：$SRC"; exit 1; }

# ---- 1) 找浏览器（Edge 优先，Chrome 兜底）----
BROWSER=""
for c in \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
do
  if [ -x "$c" ]; then BROWSER="$c"; break; fi
done
[ -n "$BROWSER" ] || { echo "❌ 找不到 Edge/Chrome（print-to-pdf 需要一个 Chromium 内核浏览器）"; exit 1; }

# ---- 2) 本地路径 → percent-encoded 的 file:// URL ----
WINPATH="$(cygpath -m "$SRC" 2>/dev/null || echo "$SRC")"
URL="$(python -c "import sys,urllib.parse;print('file:///'+urllib.parse.quote(sys.argv[1]))" "$WINPATH")"
# ⚠️ 输出路径也必须转成原生形式：Edge 不认识 /d/... 这样的 MSYS 路径，
#    传原样路径时它**不报错但也不产出文件**（第一次写这个脚本就这么栽的）。
TMPNATIVE="$(cygpath -m "$TMPOUT" 2>/dev/null || echo "$TMPOUT")"

echo "源文件：$SRC"
echo "浏览器：$BROWSER"
echo "导出 → $TMPOUT"

# ---- 3) 导出 ----
"$BROWSER" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$TMPNATIVE" "$URL" >/dev/null 2>&1 || true
[ -s "$TMPOUT" ] || { echo "❌ 导出失败（没有产物）"; exit 1; }

# ---- 4) 校验：PDF 结构 / 页数 / 文本层 ----
# 注意：这里也要喂**原生路径**给 python（它是 Windows 程序，不认 /d/... 这种 MSYS 路径）
python - "$TMPNATIVE" "$WINPATH" <<'PY'
import re, sys, pathlib
pdf = pathlib.Path(sys.argv[1]); src = pathlib.Path(sys.argv[2])
b = pdf.read_bytes()
ok = True
if not b.startswith(b"%PDF-"): print("  ❌ 不是合法 PDF（缺 %PDF- 头）"); ok = False
else: print(f"  ✅ PDF 头正常（{b[:8].decode('latin1')}）")
if b"%%EOF" not in b[-2048:]: print("  ❌ 缺 %%EOF 结尾（文件可能被截断）"); ok = False
else: print("  ✅ 结尾 %%EOF 正常")
pages = re.findall(rb"/Count (\d+)", b)
n = int(pages[0]) if pages else 0
print(f"  {'✅' if n > 0 else '❌'} 页数：{n}")
if b"/ToUnicode" not in b:
    print("  ❌ 没有 ToUnicode 文本层 —— PDF 里的中文将无法搜索/复制（退化成图片版）"); ok = False
else: print("  ✅ 含 ToUnicode 文本层（可搜索、可复制）")
if b"/FontFile2" not in b: print("  ⚠️ 未见内嵌字体，换个环境打开可能变字形")
print(f"  体积：{len(b)/1024:.0f} KB ｜ 源 HTML：{src.stat().st_size/1024:.0f} KB")
sys.exit(0 if ok else 1)
PY
CHECK=$?

# ---- 5) 落位（中文名只在 mv 这一层出现，绕开原生程序的编码问题）----
if [ "$CHECK" -eq 0 ]; then
  mv -f "$TMPOUT" "$OUT"
  echo "✅ 已生成：$OUT"
  echo "   提醒：正文数字若改过，先核对线上 /api/health、/api/scenes、/api/stats 与本地 pytest 结果，别照抄旧数字。"
else
  rm -f "$TMPOUT"
  echo "❌ 校验未通过，已丢弃产物（没有覆盖 $OUT）"
  exit 1
fi
