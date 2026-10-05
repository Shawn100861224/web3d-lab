#!/usr/bin/env python3
"""为静态托管产物生成「真实目录」，让深链返回 200 而不是 404。

    python scripts/make_deep_link_dirs.py dist

背景：GitHub Pages 对不存在的路径会返回 404，再拿 404.html 承载 SPA。页面能渲染，
但状态码是 404 —— 某些链接预览、URL 校验器、监控会判失败。
做法很土但有效：把 index.html 复制进每个已知路由的目录里（/scenes/、/scenes/<slug>/ …），
这些路径就成了真实存在的文件，返回 200，客户端路由照常接管。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

TOP_ROUTES = ("scenes", "methods", "about", "guestbook")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    index = root / "index.html"
    if not index.exists():
        print(f"⚠️ {index} 不存在，先构建")
        return 1

    made = 0
    for route in TOP_ROUTES:
        d = root / route
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(index, d / "index.html")
        made += 1

    fb = root / "scenes-fallback.json"
    slugs: list[str] = []
    if fb.exists():
        try:
            slugs = [it["slug"] for it in json.loads(fb.read_text(encoding="utf-8"))["items"]]
        except Exception as exc:  # 兜底数据坏了不该让整次构建失败
            print(f"⚠️ 读取 scenes-fallback.json 失败：{exc}")
    for slug in slugs:
        d = root / "scenes" / slug
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(index, d / "index.html")
        made += 1

    print(f"已生成 {made} 个深链目录（{len(TOP_ROUTES)} 个顶层路由 + {len(slugs)} 个场景），这些路径将返回 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
