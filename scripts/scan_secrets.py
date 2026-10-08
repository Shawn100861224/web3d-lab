#!/usr/bin/env python3
"""scan_secrets.py —— 公开仓库里不该出现的内容扫描。

用途：这个仓库是公开的（GitHub Pages 需要），所以「个人财务数字、代理/翻墙工具名、
密钥、身份证/学号」这类东西不能进去。README/HANDOFF 会被评审直接看到。

用法：python scripts/scan_secrets.py [仓库根目录]
"""
from __future__ import annotations

import os
import re
import sys

PATTERNS = {
    "疑似 API Key": re.compile(r"sk-[A-Za-z0-9]{16,}"),
    "密码/密钥赋值": re.compile(r"(password|passwd|api[_-]?key|secret)\s*[:=]\s*['\"][^'\"]{6,}"),
    "邮箱": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "手机号": re.compile(r"1[3-9]\d{9}"),
    "长数字（疑似学号/身份证）": re.compile(r"\b(?:19|20)\d{2}\d{6,}\b"),
    "代理/翻墙工具名": re.compile(r"clash|v2ray|shadowsocks|clash verge", re.I),
    "余额金额": re.compile(r"余额\s*\*{0,2}[¥$]"),
}

SKIP_DIRS = {"node_modules", ".venv", ".git", "__pycache__", "dist", "assets"}
# 注意：这里按「路径前缀」判断，不能写成 "work/" —— 目录本身的 relpath 没有结尾斜杠，
# 用带斜杠的串会漏掉直接放在该目录下的文件（第一版就漏了 work/shoe-cloud-metrics.json）。
SKIP_PATH_PREFIXES = ("deploy/cloud/assets", "work", ".cache", ".devloop")
EXTS = (".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".txt", ".sh", ".html", ".css")


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    hits: dict[str, list[tuple[str, int, str]]] = {k: [] for k in PATTERNS}
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(cur, root).replace(os.sep, "/")
        if any(rel_dir == p or rel_dir.startswith(p + "/") for p in SKIP_PATH_PREFIXES):
            continue
        for f in files:
            if not f.endswith(EXTS):
                continue
            fp = os.path.join(cur, f)
            try:
                text = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for name, rx in PATTERNS.items():
                    m = rx.search(line)
                    if m:
                        rel = os.path.relpath(fp, root).replace(os.sep, "/")
                        hits[name].append((rel, i, m.group(0)[:70]))

    total = 0
    for name, items in PATTERNS.items():
        found = hits[name]
        total += len(found)
        flag = "  " if not found else "⚠️"
        print(f"{flag} 【{name}】{len(found)} 处")
        for rel, ln, s in found[:12]:
            print(f"      {rel}:{ln}  {s}")
        if len(found) > 12:
            print(f"      …还有 {len(found) - 12} 处")
    print(f"\n合计 {total} 处命中 —— 逐条判断是否该出现在公开仓库里。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
