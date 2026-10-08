"""把两个场景简介里的 markdown 加粗标记去掉 —— 前端不渲染 markdown，`**` 会原样显示。"""

from __future__ import annotations

import json
import urllib.request

API = "https://www.shawnlab.cn/api/scenes"

FIXES = {
    "shoe-37": (
        "把清晰度实测最低的 6 张糊片从 COLMAP 模型里剔除后（43 → 37 张，其中 27 张训练 / 8 张留出评估），"
        "同一套 gsplat 参数重训 30000 步。留出视角 PSNR 14.44 → 15.41 dB、SSIM 0.7333 → 0.7567"
        "（原版见「运动鞋（本人实拍 · 云端 3 万步）」）。渲染对照图（左=训练后渲染、右=真实照片）的判定是："
        "两点需说清：① 两版的留出视角不是同一批，渲染图不能逐张对比，能对比的是平均指标；② 两版肉眼都明显模糊。结论：剔除糊片有效、但只值约 +1 dB —— "
        "真正的瓶颈仍是拍摄（单圈、约 31 个有效视角）。"
    ),
    "shoe-clean": (
        "与「运动鞋（本人实拍 · 云端 3 万步）」是同一次训练的产物，唯一区别是导出后做了一遍后处理："
        "丢掉 alpha<0.2 的近乎全透明高斯、砍掉尺度超过 4×中位数的大团子、并把超大高斯压到 3×中位数、"
        "剔除离主体 p98.5 之外的孤立点。结果 66,904 → 49,352 个高斯（保留 74%），主体轮廓更清楚、周围杂质更少。"
        "注意：PSNR/SSIM 是对原模型在留出视角上测的，此版本未重新评估，所以这里不填指标。"
    ),
}


def main() -> int:
    for slug, summary in FIXES.items():
        body = json.dumps({"summary": summary}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{API}/{slug}", data=body, method="PATCH", headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        print(f"PATCH {slug} -> {resp.status}；简介里还有 ** 吗：{'**' in data['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
