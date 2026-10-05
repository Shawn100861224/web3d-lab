"""把 public/covers/*.png 压成 WebP（960×480，质量 85），删掉 PNG。

OG 卡原图 1200×600 的 PNG 每张 ~65 KB；站上卡片显示宽 ~536 px（高分屏 ~1072 px），
所以 960×480 既够清晰又能把 116 张的体积从 ~7.6 MB 压到 ~3.5 MB。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

COVERS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "covers"
TARGET_W = 960
QUALITY = 85


def main() -> int:
    pngs = sorted(COVERS.glob("*.png"))
    if not pngs:
        print("没有 PNG 需要压缩")
        return 0

    before = sum(p.stat().st_size for p in pngs)
    after = 0
    for p in pngs:
        dest = p.with_suffix(".webp")
        with Image.open(p) as im:
            im = im.convert("RGB")
            if im.width > TARGET_W:
                h = round(im.height * TARGET_W / im.width)
                im = im.resize((TARGET_W, h), Image.LANCZOS)
            im.save(dest, "WEBP", quality=QUALITY, method=6)
        after += dest.stat().st_size
        p.unlink()

    print(f"压缩 {len(pngs)} 张：{before/1048576:.1f} MB → {after/1048576:.1f} MB"
          f"（省 {(1-after/before)*100:.0f}%）")
    print(f"平均每张 {after/len(pngs)/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
