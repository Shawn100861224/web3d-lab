"""从浏览器截图里裁出场景缩略图（场景库卡片用）。

用法：
    python scripts/make_thumbnails.py <slug>=<截图路径> [<slug>=<路径> ...]

截图来自 browser 工具对 `/?scene=<slug>` 的抓取，画布固定在 (41, 162, 912, 468)（1352×692 视口）。
裁完统一压成 640 宽的 jpg，落在 public/demo/<slug>.jpg。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

CANVAS_RECT = (41, 162, 41 + 912, 162 + 468)
OUT_WIDTH = 640
OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "demo"


def main() -> int:
    pairs = sys.argv[1:]
    if not pairs:
        print(__doc__)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        slug, _, src = pair.partition("=")
        if not src:
            print(f"跳过（格式应为 slug=path）：{pair}")
            continue
        img = Image.open(src)
        crop = img.crop(CANVAS_RECT).convert("RGB")
        height = round(crop.height * OUT_WIDTH / crop.width)
        resized = crop.resize((OUT_WIDTH, height), Image.LANCZOS)
        out = OUT_DIR / f"{slug}.jpg"
        resized.save(out, "JPEG", quality=82, optimize=True)
        print(f"{slug}: {src} -> {out} ({resized.width}x{resized.height}, {out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
