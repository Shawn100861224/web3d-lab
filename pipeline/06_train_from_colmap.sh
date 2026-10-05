#!/usr/bin/env bash
# 06 —— 用「自带位姿」的数据集直接训练（跳过 COLMAP）
#
#   bash 06_train_from_colmap.sh <场景目录> [步数] [高斯上限]
#   例：bash 06_train_from_colmap.sh ~/web3d/data/mipnerf360-counter/counter 30000 800000
#
# 适用场景：数据集/自己上次解算的结果里已经有 `sparse/0/*.bin`（COLMAP 模型），
# 这时没必要再跑一遍 SfM（240 张真实照片在 CPU 上要跑很久，而且有失败风险）。
#
# 两件事：
#   1. `.bin` → `.txt`（训练器读 TXT，COLMAP 的 model_converter 负责转换）；
#   2. 调用训练器：半分辨率、SH3、留出若干视角做评估、限制高斯上限（8GB 显存）。
set -euo pipefail

DATA_ARG="${1:?用法: 06_train_from_colmap.sh <场景目录> [步数] [高斯上限]}"
DATA="$(cd "$DATA_ARG" && pwd)"
STEPS="${2:-30000}"
# 8GB 显存实测：80 万高斯上限会在 648×420 渲染时 OOM（要 948MB 但只剩 3.6GB）。
# 30 万上限在本机跑得动；显存更小就再降分辨率和上限。
MAX_SPLATS="${3:-300000}"
DOWN="${4:-8}"          # 降采样：本机 WSL 下 GPU 分配上限远低于标称（实测约 1.5–2.7 GiB，
                        # 且与宿主可用内存相关），所以分辨率和高斯数都要压着来
INIT_POINTS="${5:-30000}"
PIPE="/mnt/d/lab/web3d-lab/pipeline"

[ -d "$DATA/images" ] || { echo "❌ $DATA/images 不存在"; exit 2; }
[ -d "$DATA/sparse/0" ] || { echo "❌ $DATA/sparse/0 不存在（没有自带位姿就跑 02_colmap_sfm.sh）"; exit 2; }
N_IMG=$(find "$DATA/images" -maxdepth 1 -type f \( -name '*.jpg' -o -name '*.JPG' -o -name '*.png' \) | wc -l)
echo "图像 $N_IMG 张 | 步数 $STEPS | 高斯上限 $MAX_SPLATS | 降采样 x$DOWN"

echo "① COLMAP 模型 .bin → .txt"
colmap model_converter --input_path "$DATA/sparse/0" --output_path "$DATA/sparse/0" --output_type TXT >/dev/null 2>&1
ls -la "$DATA/sparse/0"/*.txt | awk '{print "   ", $5, $9}'

echo "② 训练（半分辨率，日志实时输出）"
source "$HOME/web3d/env-gs.sh"
source "$HOME/web3d/venv/bin/activate"
# ⚠️ 不要在这里设 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True！
# 本机实测（WSL2 + WDDM 驱动）：该模式走 CUDA VMM 接口，会报
#   "expandable_segments: memory mapping failed with OOM on device 0"
# 而且是在「还剩 5.83 GiB 空闲」的情况下连 20 MB 都映射不了 —— 是分配器与 WSL 不兼容，
# 不是真的显存不足。默认分配器（不设这个变量）反而正常。
unset PYTORCH_CUDA_ALLOC_CONF 2>/dev/null || true
python -u "$PIPE/03_train_gsplat.py" \
  --data "$DATA" \
  --steps "$STEPS" \
  --sh-degree 3 \
  --holdout 8 \
  --down "$DOWN" \
  --max-splats "$MAX_SPLATS" \
  --max-init-points "$INIT_POINTS"
