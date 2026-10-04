#!/usr/bin/env bash
# 03 —— 训练包装脚本：先 source 工具链环境，再调 python 训练器
#
#   bash 03_train_gsplat.sh <data_dir> [steps]
set -euo pipefail

DATA="${1:?用法: 03_train_gsplat.sh <data_dir> [steps]}"
STEPS="${2:-7000}"
PIPE_DIR="/mnt/d/lab/web3d-lab/pipeline"

source "$HOME/web3d/env-gs.sh"      # CUDA_HOME / TORCH_CUDA_ARCH_LIST=12.0 / MAX_JOBS
source "$HOME/web3d/venv/bin/activate"

echo "CUDA_HOME=$CUDA_HOME"
echo "nvcc: $(command -v nvcc || echo '未找到')  |  编译目标: $TORCH_CUDA_ARCH_LIST"

# 首次运行会 JIT 编译 gsplat 的 CUDA 核（3~8 分钟，只发生一次；缓存在 ~/.cache/torch_extensions）
# -u（无缓冲）：输出重定向到文件时 Python 默认块缓冲，日志会一直看不到，
# 只有进程结束才刷出来 —— 用 `| tee` 或 -u 才能实时观察训练进度。
python -u "$PIPE_DIR/03_train_gsplat.py" \
  --data "$DATA" \
  --steps "$STEPS" \
  --sh-degree 3 \
  --holdout 4 \
  --down 2
