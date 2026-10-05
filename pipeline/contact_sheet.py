#!/usr/bin/env python3
"""把一组图片拼成一张联系表（contact sheet），用于一次性人眼核查内容。"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CELL = 512
COLS = 4


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python contact_sheet.py <图片目录> <输出png> [每格像素]")
        return 2
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    cell = int(sys.argv[3]) if len(sys.argv) > 3 else CELL

    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXTS)
    if not files:
        print("没有图片")
        return 1
    # 均匀抽样，最多 12 张
    step = max(1, len(files) // 12)
    picks = files[::step][:12]

    rows = (len(picks) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * cell, rows * cell), (20, 22, 28))
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(picks):
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((cell, cell))
            x = (i % COLS) * cell + (cell - im.width) // 2
            y = (i // COLS) * cell + (cell - im.height) // 2
            sheet.paste(im, (x, y))
            with Image.open(p) as im2:
                w, h = ImageOps.exif_transpose(im2).size
            draw.text(((i % COLS) * cell + 6, (i // COLS) * cell + 6),
                      f"[{i}] {p.name[:8]} {w}x{h}", fill=(255, 220, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"已生成 {out}  尺寸 {sheet.size}  共 {len(picks)} 格（来自 {len(files)} 张）")
    for i, p in enumerate(picks):
        print(f"  [{i}] {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
