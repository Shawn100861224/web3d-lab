#!/usr/bin/env bash
# 从一组照片跑 COLMAP 稀疏重建。
#
# 用法（在 WSL 里）:
#   bash run_from_photos.sh <照片目录> <数据集名> [最低注册率，默认 0.6]
# 例:
#   bash run_from_photos.sh /mnt/d/3D建模 bottle
#
# 为什么要复制并重命名：COLMAP 按文件名排序挑初始像对，哈希文件名顺序随机；
# 统一成 001.jpg 顺序更可控，也避免中文路径在各工具间出问题。
set -euo pipefail

SRC="$1"
NAME="$2"
MIN_RATE="${3:-0.6}"
DATA="$HOME/web3d/data/$NAME"

if [ ! -d "$SRC" ]; then
  echo "照片目录不存在: $SRC" >&2
  exit 2
fi

rm -rf "$DATA/images" "$DATA/sparse"
mkdir -p "$DATA/images"

i=0
for f in "$SRC"/*.jpg "$SRC"/*.jpeg "$SRC"/*.JPEG "$SRC"/*.JPG "$SRC"/*.png "$SRC"/*.PNG; do
  [ -e "$f" ] || continue
  i=$((i + 1))
  printf -v n "%03d" "$i"
  cp "$f" "$DATA/images/${n}.jpg"
done

if [ "$i" -lt 20 ]; then
  echo "只找到 $i 张照片（<$i 张基本无望，至少 20 张）" >&2
  exit 1
fi
echo "==== 已复制 $i 张照片 -> $DATA/images ===="

bash /mnt/d/lab/web3d-lab/pipeline/02_colmap_sfm.sh "$DATA" "$MIN_RATE"
