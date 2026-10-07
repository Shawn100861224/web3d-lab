"""把本地 SQLite 里的**场景元数据**灌进目标数据库（云上用 Neon Postgres）。

只搬「内容」：场景元数据（标题/简介/技术/指标/演示地址）。
**不搬**本地测试过程中产生的访问统计与留言 —— 线上统计应当从上线那一刻起算真实数据。

用法（必须显式给 DATABASE_URL，否则拒绝执行，防误写本地库）：

    DATABASE_URL='postgresql://...' python scripts/pg_seed.py            # 真灌
    DATABASE_URL='postgresql://...' python scripts/pg_seed.py --dry-run  # 只看要写什么

幂等：按 slug 判断，已存在则更新字段，不存在则新增。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EDITABLE_FIELDS = (
    "title",
    "summary",
    "technique",
    "source",
    "asset_path",
    "ply_path",
    "splat_count",
    "psnr",
    "featured",
    "published",
    "trained_steps",
    "capture_note",
)


def _host_of(url: str) -> str:
    """只打印主机部分，避免把密码写进日志。"""
    return url.split("@")[-1] if "@" in url else url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印将写入的内容，不落库")
    args = ap.parse_args()

    from app.config import DATABASE_URL, DB_PATH, IS_SQLITE

    if IS_SQLITE:
        print("❌ 目标库是本地 SQLite —— 本脚本用于灌云端 Postgres。")
        print("   请先设置 DATABASE_URL（例如 Neon 的连接串）再运行。")
        return 2

    print(f"源库：sqlite {DB_PATH}")
    print(f"目标：{_host_of(DATABASE_URL)}")

    src = create_engine(f"sqlite:///{DB_PATH.as_posix()}", connect_args={"check_same_thread": False})

    from app.db import engine, init_db
    from app.models import Scene

    with Session(src) as s:
        source_rows = list(s.exec(select(Scene)).all())

    print(f"读到场景 {len(source_rows)} 个：")
    for r in source_rows:
        print(f"  - {r.slug:22} {r.title[:28]:30} 高斯={r.splat_count} PSNR={r.psnr} 发布={r.published}")

    if args.dry_run:
        print("\n（--dry-run：未写入任何数据）")
        return 0

    init_db()  # 在目标库建表
    added = updated = 0
    with Session(engine) as s:
        existing = {r.slug: r for r in s.exec(select(Scene)).all()}
        for src_row in source_rows:
            row = existing.get(src_row.slug)
            if row is None:
                s.add(Scene(**{f: getattr(src_row, f) for f in ("slug", *EDITABLE_FIELDS)}))
                added += 1
            else:
                for f in EDITABLE_FIELDS:
                    setattr(row, f, getattr(src_row, f))
                s.add(row)
                updated += 1
        s.commit()

        total = len(list(s.exec(select(Scene)).all()))

    print(f"\n✅ 完成：新增 {added} / 更新 {updated}；目标库现有场景 {total} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
