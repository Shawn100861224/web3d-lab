#!/usr/bin/env bash
# run_all.sh —— 一条命令跑完整条链路：采集 → COLMAP → 训练 → 导出
#
#   bash run_all.sh <data_dir> [views] [steps] [slug]
#
# 例：bash run_all.sh ~/web3d/data/toy40 40 7000 toy-capture
#
# 每一步都会打印自己的关键指标，失败即中断（set -e），不会把垃圾数据带到下一步。
set -euo pipefail

DATA="${1:?用法: run_all.sh <data_dir> [views] [steps] [slug]}"
VIEWS="${2:-40}"
STEPS="${3:-7000}"
SLUG="${4:-toy-capture}"
PIPE="/mnt/d/lab/web3d-lab/pipeline"

export PYTHONUNBUFFERED=1   # 关键：不加这个，重定向到文件时日志会一直看不到

echo "############ 1/4 合成采集 ############"
"$HOME/web3d/venv/bin/python" -u "$PIPE/01_make_synthetic_capture.py" \
  --out "$DATA" --views "$VIEWS" --save-texture

echo
echo "############ 2/4 COLMAP 稀疏重建 ############"
bash "$PIPE/02_colmap_sfm.sh" "$DATA" 0.6

echo
echo "############ 3/4 gsplat 训练 ############"
bash "$PIPE/03_train_gsplat.sh" "$DATA" "$STEPS"

echo
echo "############ 4/4 导出到前端（回写后端请在 Windows 侧跑 04）############"
"$HOME/web3d/venv/bin/python" -u "$PIPE/04_export_to_web.py" --data "$DATA" --slug "$SLUG" --no-register

echo
echo "全部完成。WSL 访问不到 Windows 的 127.0.0.1，回写后端请这样跑（在 Windows 侧）："
echo "  python pipeline/04_export_to_web.py --data .cache/<name> \\"
echo "    --metrics .cache/<name>/train/metrics.json --slug $SLUG --frontend . \\"
echo "    --asset \$PWD/frontend/public/demo/$SLUG.splat --api http://127.0.0.1:8000"
