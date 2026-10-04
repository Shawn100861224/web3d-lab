"""种子数据：往库里塞几条场景记录，方便前端/接口联调。

    cd backend && .venv/Scripts/python.exe scripts/seed_scenes.py          # 幂等新增
    cd backend && .venv/Scripts/python.exe scripts/seed_scenes.py --reset  # 清空后重建（仅本地开发）

注意：`asset_url` 指向的 .spz 需要真的存在于 `frontend/public/demo/` 下，
否则查看器页会 404 —— 资产的来源与校验见模块 3。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, delete, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import Scene  # noqa: E402

SEEDS: list[dict] = [
    {
        "slug": "garden-sample",
        "title": "花园小径（spark 官方示例）",
        "summary": "链路验证用：官方示例资产，用来先把「加载 → 渲染 → 指标面板」跑通。",
        "technique": "3DGS",
        "source": "sample",
        "asset_url": "/demo/garden.spz",
        "asset_format": "spz",
        "thumbnail_url": None,
        "license": "见上游 sparkjs.dev 示例说明",
        "featured": True,
    },
    {
        "slug": "desk-chair",
        "title": "桌面椅子（本机自训，待替换为真实训练结果）",
        "summary": "占位记录：等模块 8 用手机环拍照片训练完再回写真实指标。",
        "technique": "3DGS",
        "source": "self-trained",
        "num_points": None,
        "sh_degree": 3,
        "iterations": 7000,
        "train_seconds": None,
        "gpu_mem_mb": None,
        "capture_device": "Redmi K60",
        "capture_views": 42,
        "psnr": None,
        "ssim": None,
        "lpips": None,
        "asset_url": "/demo/desk-chair.spz",
        "asset_format": "spz",
        "featured": False,
    },
]


def main() -> int:
    init_db()
    reset = "--reset" in sys.argv
    with Session(engine) as session:
        if reset:
            session.exec(delete(Scene))
            session.commit()
            print("[seed] 已清空 scenes 表")
        for spec in SEEDS:
            exists = session.exec(select(Scene).where(Scene.slug == spec["slug"])).first()
            if exists:
                print(f"[seed] 跳过已存在：{spec['slug']}")
                continue
            session.add(Scene.model_validate(spec))
            print(f"[seed] 新增：{spec['slug']}")
        session.commit()
        total = len(session.exec(select(Scene)).all())
    print(f"[seed] 完成，库中场景数 = {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
