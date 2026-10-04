#!/usr/bin/env python3
"""模拟 GitHub Pages / EdgeOne Pages 的静态托管行为，用于本地验收。

    python scripts/static-server.py <目录> [端口]

与 python 自带 http.server 的唯一区别（也正是要验证的那一点）：
**找不到的路径返回 404.html 的内容、状态码 404** —— 这是 GH Pages 的 SPA 回退机制，
没有它，直接打开 /scenes/xxx 会是白页 404；前端就是把 index.html 复制成 404.html 来兜的。
"""

from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PagesHandler(SimpleHTTPRequestHandler):
    fallback: Path | None = None

    def send_error(self, code, message=None, explain=None):  # type: ignore[override]
        # 只对 GET 且非 API 的 404 做回退，其余保持原样
        if code == 404 and self.fallback and self.command == "GET":
            body = self.fallback.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):  # 静音，避免刷屏
        pass


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4174
    fb = root / "404.html"
    PagesHandler.fallback = fb if fb.exists() else None
    print(f"静态托管模拟：root={root} port={port} 404回退={'开' if PagesHandler.fallback else '关（缺 404.html）'}")

    handler = partial(PagesHandler, directory=str(root))
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
