"""构建云端训练包（AutoDL/Colab 用）：
  1) 校验 2016px 与 4032px 两套图是同一批照片（按名字对齐，缩略图比对）
  2) 拷 2016px 图 + COLMAP 模型（相机内参按 0.5 缩放，因为图缩了一半）
  3) 附训练脚本与一键运行脚本，打成 zip
产物：D:\\lab\\web3d-lab\\work\\cloud-kit-shoe.zip
"""
import os, shutil, zipfile, numpy as np
from PIL import Image

IMG2016 = r"D:\lab\web3d-lab\work\shoes2016"
IMG4032 = r"\\wsl.localhost\Ubuntu-24.04\home\shawn\web3d\data\shoe\images"
SPARSE = r"\\wsl.localhost\Ubuntu-24.04\home\shawn\web3d\data\shoe\sparse\0"
OUT = r"D:\lab\web3d-lab\work\cloud-kit"
KIT = os.path.join(OUT, "shoe")
PIPE = r"D:\lab\web3d-lab\pipeline"

# ---- 1) 校验两套图对应 ----
names16 = sorted(f for f in os.listdir(IMG2016) if f.endswith(".jpg"))
names43 = sorted(f for f in os.listdir(IMG4032) if f.endswith(".jpg"))
print("2016px: %d 张 | 4032px: %d 张" % (len(names16), len(names43)))
assert names16 == names43, "文件名不一致！"
# 严格校验：每张 2016px 图与全部 43 张 4032px 图比对，同名的那张必须是"最像的"
thumbs16 = {}
thumbs43 = {}
for n in names16:
    a = np.asarray(Image.open(os.path.join(IMG2016, n)).convert("L").resize((32, 32)), dtype=float)
    thumbs16[n] = a - a.mean()
for n in names43:
    b = np.asarray(Image.open(os.path.join(IMG4032, n)).convert("L").resize((32, 32)), dtype=float)
    thumbs43[n] = b - b.mean()

bad = []
diag_vals = []
for n in names16:
    ds = {m: float(np.abs(thumbs16[n] - thumbs43[m]).mean()) for m in names43}
    best = min(ds, key=ds.get)
    diag_vals.append(ds[n])
    if best != n:
        bad.append((n, best, ds[n], ds[best]))
print("对角线（同名配对）结构差：最大 %.2f / 中位 %.2f" % (max(diag_vals), sorted(diag_vals)[len(diag_vals) // 2]))
if bad:
    print("❌ 有 %d 张配不上对：" % len(bad))
    for n, b2, dv, bv in bad[:6]:
        print("   %s 最像的是 %s（同名差 %.1f，最像差 %.1f）" % (n, b2, dv, bv))
    raise SystemExit("两套图对应关系有问题，别继续！")
print("✅ 43 张全部一一对应（每张的同名原图就是它最像的那张）")

# ---- 2) 拷贝 ----
if os.path.exists(KIT):
    shutil.rmtree(KIT)
os.makedirs(os.path.join(KIT, "images"))
os.makedirs(os.path.join(KIT, "sparse", "0"))
for n in names16:
    shutil.copy2(os.path.join(IMG2016, n), os.path.join(KIT, "images", n))
print("图片已拷 ->", os.path.join(KIT, "images"))

for f in ("images.txt", "points3D.txt"):
    shutil.copy2(os.path.join(SPARSE, f), os.path.join(KIT, "sparse", "0", f))

# 相机内参：图缩了一半 → fx/fy/cx/cy 与 W/H 全部减半（畸变系数是无量纲的，不变）
lines = open(os.path.join(SPARSE, "cameras.txt"), encoding="utf-8").read().splitlines()
out_lines = []
for ln in lines:
    if ln.strip() and not ln.startswith("#"):
        p = ln.split()
        w, h = int(p[2]) // 2, int(p[3]) // 2
        fx, fy, cx, cy = (float(p[4]) / 2, float(p[5]) / 2, float(p[6]) / 2, float(p[7]) / 2)
        new = "%s %s %d %d %.6f %.6f %.4f %.4f %s" % (p[0], p[1], w, h, fx, fy, cx, cy, " ".join(p[8:]))
        print("cameras.txt:\n  旧 %s\n  新 %s" % (ln.strip(), new))
        out_lines.append(new)
    else:
        out_lines.append(ln)
open(os.path.join(KIT, "sparse", "0", "cameras.txt"), "w", encoding="utf-8").write("\n".join(out_lines) + "\n")

# 训练脚本（与本机同一份，保证行为一致）
shutil.copy2(os.path.join(PIPE, "03_train_gsplat.py"), os.path.join(OUT, "train_gsplat.py"))

open(os.path.join(OUT, "run_on_cloud.sh"), "w", encoding="utf-8", newline="\n").write("""#!/usr/bin/env bash
# 云端一键训练（AutoDL / Colab 通用）。用法： bash run_on_cloud.sh
set -uo pipefail
cd "$(dirname "$0")"
echo "== 环境自检 =="
python -c "import torch, gsplat; print('torch', torch.__version__, '| cuda', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0)); print('gsplat ok')" 2>/dev/null \\
  || { echo "缺 gsplat，开始安装（首次约 2-5 分钟）"; pip install -q gsplat; }
echo "== 开始训练：30000 步 / 1008x756 / 上限 80 万高斯 =="
python -u train_gsplat.py --data ./shoe --steps 30000 --sh-degree 3 --holdout 8 \\
  --down 2 --max-splats 800000 --densify-grad 2e-4
echo "== 产物 =="
ls -la ./shoe/train/
echo "== 下载这个文件即可： ./shoe/train/web_30000.splat =="
""")

with zipfile.ZipFile(os.path.join(OUT, "..", "cloud-kit-shoe.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(OUT):
        for f in files:
            fp = os.path.join(root, f)
            z.write(fp, os.path.relpath(fp, OUT))

zp = os.path.join(OUT, "..", "cloud-kit-shoe.zip")
print("\n✅ 训练包:", os.path.abspath(zp), "%.1f MB" % (os.path.getsize(zp) / 1048576))
print("内容:", sorted(os.listdir(OUT)))
