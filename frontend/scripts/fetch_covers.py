"""下载 116 个仓库的 GitHub 官方 OG 卡（social preview）到 frontend/public/covers/。

为什么本地缓存而不是热链：
  - 热链 opengraph.githubassets.com 在国内访问很慢、还可能直接裂图（评审打开一片灰）
  - GitHub 对该接口有 429 限流，所以串行 + 退避重试

失败/超时的仓库不写文件 → 前端自动回退到程序化封面（绝不裂图）。
用法：python frontend/scripts/fetch_covers.py [--limit N] [--force]
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RADAR = ROOT / "frontend" / "public" / "radar.json"
COVERS = ROOT / "frontend" / "public" / "covers"
PROXY = "http://127.0.0.1:7897"  # 本地代理；直连 GitHub 会被限速到百 KB/s
MIN_BYTES = 5000  # 小于这个值说明是错误页/占位，不算成功


def fetch(url: str, dest: Path, timeout: int = 30) -> tuple[bool, str]:
    """返回 (是否成功, 说明)。"""
    for attempt in range(3):
        proc = subprocess.run(
            [
                "curl", "-sSL", "-x", PROXY, "--max-time", str(timeout),
                "-o", str(dest), "-w", "%{http_code}",
                url,
            ],
            capture_output=True,
            text=True,
        )
        code = (proc.stdout or "").strip()
        ok = code == "200" and dest.exists() and dest.stat().st_size >= MIN_BYTES
        if ok:
            return True, f"200 {dest.stat().st_size // 1024}KB"
        if code == "429":  # 限流：等久一点再试
            time.sleep(6 + attempt * 6)
            continue
        time.sleep(2 + attempt * 3)
    if dest.exists():
        dest.unlink(missing_ok=True)
    return False, code or "失败"


def main() -> int:
    limit = None
    force = "--force" in sys.argv
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    # --slice 2/3 → 只处理下标 2,5,8… 的条目；并行跑 3 个 worker 时用
    slice_idx = slice_n = None
    if "--slice" in sys.argv:
        a, b = sys.argv[sys.argv.index("--slice") + 1].split("/")
        slice_idx, slice_n = int(a), int(b)

    items = json.loads(RADAR.read_text(encoding="utf-8"))["items"]
    if slice_n:
        items = [it for i, it in enumerate(items) if i % slice_n == slice_idx]
    COVERS.mkdir(parents=True, exist_ok=True)

    done = skipped = failed = 0
    failures: list[str] = []

    for i, item in enumerate(items, 1):
        if limit and done + failed >= limit:
            break
        slug = f"{item['owner']}-{item['name']}".replace("/", "-")
        dest = COVERS / f"{slug}.png"
        # 压成 WebP 后 PNG 会被删掉，所以两种都算「已有」，避免重复下载
        if not force and (
            (dest.exists() and dest.stat().st_size >= MIN_BYTES) or (COVERS / f"{slug}.webp").exists()
        ):
            skipped += 1
            continue
        url = f"https://opengraph.githubassets.com/1/{item['owner']}/{item['name']}"
        ok, note = fetch(url, dest)
        if ok:
            done += 1
            print(f"[{i}/{len(items)}] ✅ {item['full_name']}  {note}", flush=True)
        else:
            failed += 1
            failures.append(item["full_name"])
            print(f"[{i}/{len(items)}] ❌ {item['full_name']}  {note}", flush=True)
        time.sleep(1.2)  # 串行节流，避免 429

    print(f"\n完成：新下载 {done} · 已存在跳过 {skipped} · 失败 {failed}", flush=True)
    if failures:
        print("失败清单（这些会用程序化封面兜底）：", flush=True)
        for f in failures:
            print("  -", f, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
