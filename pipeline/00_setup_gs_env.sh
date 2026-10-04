#!/usr/bin/env bash
# 00 —— 准备 3DGS 训练环境（WSL2 / Blackwell 显卡 / torch cu130）
#
#   bash 00_setup_gs_env.sh
#
# 为什么这么绕（本机实测 2026-10-05，每一步都是踩出来的）：
#   1. torch 2.14.1+cu130 装好即可用、识别 RTX 5060（sm_120），但 **gsplat 的预编译轮子只发到
#      pt24cu124**（Blackwell 之前）→ 必须 JIT 编译 CUDA 核 → 必须有 nvcc。
#   2. torch 自带的 nvidia/cu13 只有头文件与库、**没有 nvcc**；
#      pip 的 nvidia-cuda-nvcc-cu12 只带 ptxas + crt 头，**也没有 nvcc 驱动**。
#   3. Ubuntu 24.04 仓库的 nvidia-cuda-toolkit 是 CUDA 12.0，**编不出 sm_120**。
#   4. NVIDIA 官方 deb 仓库里：cuda-nvcc-13-4 有 nvcc/cudafe++/nvlink/ptxas，但**没有 cicc**；
#      CUDA 13 把 nvvm 改名成了 **libnvvm**（12.x 时叫 cuda-nvvm）——只下 cuda-nvcc 会报
#      “.../nvvm/bin/cicc: not found”。
#   → 正确组合：cuda-nvcc-13-4 + libnvvm-13-4 + cuda-crt-13-4 + cuda-cudart(-dev)-13-4，
#     用 dpkg-deb -x 解到自己的目录（不动系统、不装包、不需要 root）。
#   deb 内部是 ./usr/local/cuda-13.4/ 结构，所以 CUDA_HOME 要指向那一层。
set -euo pipefail

VENV="$HOME/web3d/venv"
RAW="$HOME/web3d/cuda-debs-extracted"
DEBS="/mnt/d/lab/web3d-lab/.cache/cuda-debs"

echo "== 1/5 python 侧依赖 =="
source "$VENV/bin/activate"
pip install -q gsplat
python - <<'PY'
import torch
print(f"torch {torch.__version__} | cuda {torch.version.cuda} | 可用 {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)} | 算力 {torch.cuda.get_device_capability(0)}")
PY

echo "== 2/5 解包 CUDA 13.4 组件 =="
[ -d "$DEBS" ] || { echo "缺少 $DEBS"; exit 2; }
rm -rf "$RAW"
mkdir -p "$RAW"
for deb in "$DEBS"/*.deb; do
  echo "  $(basename "$deb")"
  dpkg-deb -x "$deb" "$RAW"
done

CUDA_HOME="$(find "$RAW/usr/local" -maxdepth 1 -mindepth 1 -type d -name 'cuda-*' | head -1)"
[ -n "$CUDA_HOME" ] || { echo "❌ 没找到 usr/local/cuda-* 目录"; find "$RAW" -maxdepth 3 -type d | head; exit 3; }
echo "CUDA_HOME = $CUDA_HOME"

echo "== 3/5 用 pip 的头文件补齐（cudart/runtime 头不在 deb 里） =="
SP="$VENV/lib/python3.12/site-packages/nvidia"
for srcdir in "$SP"/cuda_runtime/include "$SP"/cuda_cccl/include; do
  [ -d "$srcdir" ] || continue
  cp -rn "$srcdir"/* "$CUDA_HOME/include/" 2>/dev/null || true
done
echo "  include 条目：$(ls "$CUDA_HOME/include" | wc -l)  |  nvvm：$(ls "$CUDA_HOME/nvvm/bin" 2>/dev/null | tr '\n' ' ')"

echo "== 4/5 写环境变量文件 =="
cat > "$HOME/web3d/env-gs.sh" <<EOF
# 训练 / gsplat JIT 编译前 source 一次
export CUDA_HOME="$CUDA_HOME"
export PATH="$CUDA_HOME/bin:\$PATH"
export TORCH_CUDA_ARCH_LIST="12.0"    # 只编 Blackwell，省编译时间
export MAX_JOBS=6
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$CUDA_HOME/lib:\${LD_LIBRARY_PATH:-}"
EOF
source "$HOME/web3d/env-gs.sh"
nvcc --version | tail -2

echo "== 5/5 真正编译一个 sm_120 的 kernel（这步过了才算环境就绪） =="
TMPD="$(mktemp -d)"
cat > "$TMPD/t.cu" <<'CU'
#include <cstdio>
__global__ void k(float* a) { a[threadIdx.x] = threadIdx.x * 2.0f; }
__global__ void sh(const float* __restrict__ m, float* out) {}   // 具备 #include 能力即可
int main() { printf("sm_120 compile+link OK\n"); return 0; }
CU
nvcc -arch=sm_120 -o "$TMPD/t" "$TMPD/t.cu"
"$TMPD/t"
rm -rf "$TMPD"
echo "✅ 环境就绪：$HOME/web3d/env-gs.sh"
