#!/usr/bin/env python3
"""为静态托管产物生成「真实目录」，让深链返回 200，并写入该页自己的分享卡片。

    python scripts/make_deep_link_dirs.py dist
    python scripts/make_deep_link_dirs.py dist --origin https://www.shawnlab.cn

两件事：

1. **深链返回 200 而不是 404**（原有功能）
   GitHub Pages 对不存在的路径一律 404，再拿 404.html 承载 SPA：页面能渲染，但状态码难看，
   某些链接预览/校验会判失败。做法很土但有效 —— 把 index.html 复制进每个已知路由的目录里，
   这些路径就成了真实文件。

2. **每个页面的分享卡片（--origin 时启用）**
   原先每个深链都是 index.html 的副本，于是 `<title>` / `og:title` / `og:image` 全是站点级的值 ——
   在微信/QQ 里发 `/scenes/shoe-37/`，显示的是站点名和通用封面，而不是这个场景。
   现在会按 `scenes-fallback.json` 把该场景的标题/简介/缩略图写进那一份 HTML。
   （EdgeOne 主站靠平台 SPA 兜底，本来也能返回 200，所以历史上没生成目录；
   但**兜底返回的是站点 index.html** → 分享卡片永远不区分场景。所以主站也要装这一份。）

   `--origin` 必须是该部署的**站点根地址**（og:image 要绝对地址，爬虫不解析相对路径）：
   主站 `https://www.shawnlab.cn`、镜像 `https://shawn100861224.github.io/web3d-lab`。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

TOP_ROUTES = ("scenes", "methods", "about", "guestbook", "projects")
SITE_TITLE = "web3d-lab · 3DGS 在线重建查看器"
DEFAULT_IMAGE = "/og-cover.jpg"


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _swap(doc: str, pattern: str, replacement: str) -> str:
    """替换匹配到的标签；若页面里没有这个标签，则在 </head> 前插入。

    用 DOTALL + 非贪婪：源文件里的标签可能跨行（例如 name="description" 与 content 分行）。
    """
    new_doc, n = re.subn(pattern, replacement, doc, count=1, flags=re.S | re.I)
    if n:
        return new_doc
    return doc.replace("</head>", f"    {replacement}\n  </head>", 1)


def with_page_meta(doc: str, *, title: str, description: str, url: str, image: str) -> str:
    t, d, u, i = _esc(title), _esc(description), _esc(url), _esc(image)
    doc = _swap(doc, r"<title>.*?</title>", f"<title>{t}</title>")
    doc = _swap(doc, r'<meta[^>]*name="description"[^>]*>', f'<meta name="description" content="{d}" />')
    doc = _swap(doc, r'<meta[^>]*property="og:title"[^>]*>', f'<meta property="og:title" content="{t}" />')
    doc = _swap(doc, r'<meta[^>]*property="og:description"[^>]*>', f'<meta property="og:description" content="{d}" />')
    doc = _swap(doc, r'<meta[^>]*property="og:url"[^>]*>', f'<meta property="og:url" content="{u}" />')
    doc = _swap(doc, r'<meta[^>]*property="og:image"[^>]*>', f'<meta property="og:image" content="{i}" />')
    doc = _swap(doc, r'<meta[^>]*name="twitter:title"[^>]*>', f'<meta name="twitter:title" content="{t}" />')
    doc = _swap(doc, r'<meta[^>]*name="twitter:description"[^>]*>', f'<meta name="twitter:description" content="{d}" />')
    doc = _swap(doc, r'<meta[^>]*name="twitter:image"[^>]*>', f'<meta name="twitter:image" content="{i}" />')
    # og:image:width/height 只对站点封面成立，换图时删掉，免得声明与实际不符
    doc = re.sub(r'<meta[^>]*property="og:image:(width|height)"[^>]*>\s*', "", doc, flags=re.I)
    return doc


def one_line(text: str, limit: int = 118) -> str:
    """简介压成一行、截断到 limit —— 分享卡片里换行会被吞，太长会被截。"""
    s = re.sub(r"\s+", " ", (text or "").replace("**", "")).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def abs_url(origin: str, path: str) -> str:
    if not path:
        path = DEFAULT_IMAGE
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return origin.rstrip("/") + "/" + path.lstrip("/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="dist", help="构建产物目录")
    ap.add_argument("--origin", default="", help="站点根地址（给定时才写每页自己的分享卡片）")
    args = ap.parse_args()

    root = Path(args.root)
    index = root / "index.html"
    if not index.exists():
        print(f"⚠️ {index} 不存在，先构建")
        return 1
    index_html = index.read_text(encoding="utf-8")

    # ---- 场景列表（兜底数据）----
    scenes: list[dict] = []
    fb = root / "scenes-fallback.json"
    if fb.exists():
        try:
            scenes = json.loads(fb.read_text(encoding="utf-8"))["items"]
        except Exception as exc:  # 兜底数据坏了不该让整次构建失败
            print(f"⚠️ 读取 scenes-fallback.json 失败：{exc}")
    slugs = [it["slug"] for it in scenes]

    def write(dir_path: Path, doc: str) -> None:
        dir_path.mkdir(parents=True, exist_ok=True)
        (dir_path / "index.html").write_text(doc, encoding="utf-8")

    made = 0
    # ---- 顶层路由：/scenes/ 单独写更好的卡片，其余沿用站点卡片 ----
    for route in TOP_ROUTES:
        if route == "scenes" and args.origin and scenes:
            doc = with_page_meta(
                index_html,
                title=f"场景库 · web3d-lab（{len(scenes)} 个）",
                description=f"{len(scenes)} 个 3DGS 场景，可在浏览器里实时旋转查看："
                            + "、".join(one_line(it.get("title", ""), 22) for it in scenes[:6]),
                url=f"{args.origin.rstrip('/')}/scenes/",
                image=abs_url(args.origin, scenes[0].get("thumbnail_url") or DEFAULT_IMAGE),
            )
            write(root / route, doc)
        else:
            write(root / route, index_html)
        made += 1

    # ---- 每个场景：自己的分享卡片 ----
    per_scene = 0
    for it in scenes:
        slug = it["slug"]
        if args.origin:
            doc = with_page_meta(
                index_html,
                title=f"{it.get('title', slug)} · web3d-lab",
                description=one_line(it.get("summary", "")),
                url=f"{args.origin.rstrip('/')}/scenes/{slug}/",
                image=abs_url(args.origin, it.get("thumbnail_url") or DEFAULT_IMAGE),
            )
            per_scene += 1
        else:
            doc = index_html
        write(root / "scenes" / slug, doc)

    # ---- 项目详情深链：/projects/<owner>/<name>/（数据来自 radar.json）----
    projects = 0
    project_paths: list[tuple[str, str]] = []
    radar = root / "radar.json"
    if radar.exists():
        try:
            items = json.loads(radar.read_text(encoding="utf-8"))["items"]
        except Exception as exc:
            print(f"⚠️ 读取 radar.json 失败：{exc}")
            items = []
        for it in items:
            d = root / "projects" / it["owner"] / it["name"]
            d.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(index, d / "index.html")
            project_paths.append((it["owner"], it["name"]))
            projects += 1

    # ---- sitemap.xml：给爬虫一份完整入口清单（只在给了 --origin 时写 —— 里面必须是绝对地址）----
    if args.origin:
        base = args.origin.rstrip("/")
        locs = [f"{base}/"] + [f"{base}/{r}/" for r in TOP_ROUTES]
        locs += [f"{base}/scenes/{it['slug']}/" for it in scenes]
        locs += [f"{base}/projects/{o}/{n}/" for o, n in project_paths]
        xml = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        xml += [f"  <url><loc>{u}</loc></url>" for u in locs]
        xml.append("</urlset>")
        (root / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
        print(f"已写 sitemap.xml（{len(locs)} 条：首页 + {len(TOP_ROUTES)} 路由 + {len(scenes)} 场景 + {len(project_paths)} 项目）")

    card_note = f"，其中 {per_scene} 个场景写了自己的分享卡片" if args.origin else "（未给 --origin，分享卡片仍是站点级）"
    print(
        f"已生成 {made + len(slugs) + projects} 个深链目录"
        f"（{len(TOP_ROUTES)} 个顶层路由 + {len(slugs)} 个场景 + {projects} 个项目）{card_note}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
