"""种子数据：往库里塞几条场景记录，方便前端/接口联调。

    cd backend && .venv/Scripts/python.exe scripts/seed_scenes.py          # 幂等新增
    cd backend && .venv/Scripts/python.exe scripts/seed_scenes.py --reset  # 清空后重建（仅本地开发）

注意：`asset_url` 指向的 .spz 必须真的存在于 `frontend/public/demo/` 下，否则查看器会
走到「资产加载失败」分支。资产的来源、下载方式与「哪些能正常渲染」的实测结论见
`frontend/scripts/fetch-demo-assets.sh` 与 README 的「示例资产」小节。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, delete, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import Scene  # noqa: E402

SAMPLE_LICENSE = "上游示例资产（sparkjs.dev/examples/assets.json），仅用于链路验证"

SEEDS: list[dict] = [
    {
        "slug": "robot-head",
        "title": "人形机器人头部（spark 官方示例）",
        "summary": "单物体尺度：约 4.5 万高斯点，用来先把「浏览器加载 → 实时旋转 → 指标面板」跑通。",
        "technique": "3DGS",
        "source": "sample",
        "asset_url": "/demo/robot-head.spz",
        "asset_format": "spz",
        "num_points": 45401,
        "sh_degree": 3,
        "license": SAMPLE_LICENSE,
        "featured": True,
    },
    {
        "slug": "fireplace",
        "title": "壁炉（spark 官方示例，室内）",
        "summary": "室内尺度：约 30 万高斯点，包围盒 8×7×7 世界单位，观察近景漫游手感。",
        "technique": "3DGS",
        "source": "sample",
        "asset_url": "/demo/fireplace.spz",
        "asset_format": "spz",
        "num_points": 301000,
        "sh_degree": 3,
        "license": SAMPLE_LICENSE,
        "featured": True,
    },
    {
        "slug": "painted-bedroom",
        "title": "彩绘卧室（forge 官方示例，室内）",
        "summary": "房间尺度：约 50 万高斯点，包围盒 10×7×12，验证大点的场景也能保持帧率。",
        "technique": "3DGS",
        "source": "sample",
        "asset_url": "/demo/painted-bedroom.spz",
        "asset_format": "spz",
        "num_points": 500000,
        "sh_degree": 3,
        "license": SAMPLE_LICENSE,
        "featured": False,
    },
    {
        "slug": "valley",
        "title": "山谷（spark 官方示例，室外大场景）",
        "summary": "室外尺度：约 50 万高斯点，包围盒 916×342×415——相机自动取景与近远裁剪面的压力测试。",
        "technique": "3DGS",
        "source": "sample",
        "asset_url": "/demo/valley.spz",
        "asset_format": "spz",
        "num_points": 500000,
        "sh_degree": 3,
        "license": SAMPLE_LICENSE,
        "featured": False,
    },
    {
        "slug": "desk-chair",
        "title": "桌面椅子（本机自训，尚未训练）",
        "summary": "占位草稿：等模块 8 用手机环拍照片训练完，再把真实 PSNR/SSIM 与 .spz 回写进来。",
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
        "published": False,
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
