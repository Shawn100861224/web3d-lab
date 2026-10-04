#!/usr/bin/env bash
# 02 —— COLMAP 稀疏重建（SfM）：从 images/ 解出相机内参、外参与稀疏点云。
#
#   bash 02_colmap_sfm.sh ~/web3d/data/toy40
#
# 产出 <data>/sparse/0/{cameras,images,points3D}.bin + database.db + sfm_summary.json
# 这一份就是 3DGS 训练要吃的标准 COLMAP 数据集格式。
#
# 本机实测（2026-10-05，WSL2 / COLMAP 3.9.1 apt 版 / 无 CUDA）：
#   900x675 的 40 张图：特征提取+穷举匹配+建图约 6 分钟（CPU SIFT）。
#   apt 版没有 CUDA → 必须显式 --SiftExtraction.use_gpu 0 / --SiftMatching.use_gpu 0，
#   否则 COLMAP 找不到 CUDA 会直接报错退出。
#
# 两个踩过的坑，写在这里省下一次重踩：
#   1. **COLMAP 的日志走 stderr**，解析它的输出必须 `2>&1`，否则拿到空字符串（会误判成 0 张注册）。
#   2. 建图质量必须**硬门槛**：注册率低于阈值就报错退出，不能让后面的训练吃一份垃圾数据。
set -euo pipefail

DATA="${1:?用法: 02_colmap_sfm.sh <data_dir>（该目录下应有 images/）}"
MIN_RATE="${2:-0.6}"   # 注册率下限，低于它直接判失败
DATA="$(cd "$DATA" && pwd)"
IMAGES="$DATA/images"
DB="$DATA/database.db"
SPARSE="$DATA/sparse"
LOG="$DATA/colmap.log"

[ -d "$IMAGES" ] || { echo "找不到 $IMAGES"; exit 2; }
N_IMG=$(find "$IMAGES" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.JPG' \) | wc -l)
echo "输入图像：$N_IMG 张（$IMAGES）"
[ "$N_IMG" -ge 5 ] || { echo "❌ images/ 里只有 $N_IMG 张图，先修采集（01）再来跑 SfM"; exit 2; }

mkdir -p "$SPARSE"
rm -f "$DB"
rm -rf "$SPARSE"/*

{
  echo "== 1/4 特征提取 =="
  colmap feature_extractor \
    --database_path "$DB" \
    --image_path "$IMAGES" \
    --ImageReader.single_camera 1 \
    --ImageReader.camera_model OPENCV \
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.max_image_size 1600

  echo "== 2/4 特征匹配（穷举；图少时最稳） =="
  colmap exhaustive_matcher --database_path "$DB" --SiftMatching.use_gpu 0

  echo "== 3/4 增量式建图 =="
  colmap mapper --database_path "$DB" --image_path "$IMAGES" --output_path "$SPARSE"
} 2>&1 | tee "$LOG" | grep -E '^(==|Processed|Registering|Elapsed)' | tail -20

echo "== 4/4 挑选注册图像最多的子模型 =="
BEST=""
BEST_N=-1
for d in "$SPARSE"/*/; do
  [ -d "$d" ] || continue
  # 注意 2>&1：COLMAP 把统计信息打在 stderr
  REPORT=$(colmap model_analyzer --path "$d" 2>&1 || true)
  # 注意：COLMAP 的统计行带 glog 前缀（I20261005 ... model.cc:431] Registered images: 2），
  # 直接 grep 第一个数字会抓到日期。必须取冒号后面的那个数。
  REG=$(echo "$REPORT" | sed -n 's/.*Registered images:[[:space:]]*\([0-9]\+\).*/\1/p' | head -1)
  PTS=$(echo "$REPORT" | sed -n 's/.*] Points:[[:space:]]*\([0-9]\+\).*/\1/p' | head -1)
  echo "  $d -> 注册图像 ${REG:-0}，3D 点 ${PTS:-0}"
  if [ "${REG:-0}" -gt "$BEST_N" ]; then BEST="$d"; BEST_N="${REG:-0}"; fi
done

[ -n "$BEST" ] || { echo "建图失败：没有任何子模型（特征不足：纯色/高噪声纹理/重叠太少都会这样）"; exit 3; }

# 失败时给出匹配诊断：多少对图像匹配上了、匹配点数分布如何
if [ "${BEST_N:-0}" -lt 3 ]; then
  echo "— 匹配诊断（前 8 对图像的特征匹配数）—"
  python3 - "$DB" <<'PY'
import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(db)
try:
    rows = c.execute("select image_id, rows from matches order by rows desc limit 0").fetchall()
except Exception:
    pass
cols = [r[1] for r in c.execute("PRAGMA table_info(matches)")]
print("  matches 表字段：", cols)
n_pairs = c.execute("select count(*) from matches").fetchone()[0]
print(f"  有匹配的图像对：{n_pairs}")
tot = c.execute("select sum(rows) from matches").fetchone()[0] or 0
print(f"  匹配点总数：{tot}")
n_kp = c.execute("select sum(rows) from keypoints").fetchone()[0] or 0
print(f"  特征点总数：{n_kp}")
PY
fi

RATE=$(python3 -c "print(round($BEST_N/max($N_IMG,1),3))")
cat > "$DATA/sfm_summary.json" <<JSON
{
  "input_images": $N_IMG,
  "registered_images": $BEST_N,
  "model_path": "$BEST",
  "registration_rate": $RATE,
  "min_rate_required": $MIN_RATE
}
JSON

if [ "$BEST" != "$SPARSE/0/" ]; then
  echo "把最佳模型复制成 sparse/0（训练脚本默认读这个路径）"
  rm -rf "$SPARSE/0"
  cp -r "$BEST" "$SPARSE/0"
fi

# 训练脚本（03）读的是 TXT 模型：必须显式转一次，否则只有 .bin
echo "把 sparse/0 转出 TXT（训练器读 TXT）"
colmap model_converter --input_path "$SPARSE/0" --output_path "$SPARSE/0" --output_type TXT >/dev/null

echo
colmap model_analyzer --path "$SPARSE/0" 2>&1 | grep -E 'Cameras|Images|Points|error' || true
echo "注册率：$RATE（门槛 $MIN_RATE）"

python3 - "$RATE" "$MIN_RATE" <<'PY'
import sys
rate, minimum = float(sys.argv[1]), float(sys.argv[2])
if rate < minimum:
    print(f"❌ 注册率 {rate} 低于门槛 {minimum}：这份稀疏重建不能拿去训练，请先修输入（纹理/重叠/清晰度）")
    sys.exit(3)
print(f"✅ 注册率达标（{rate} ≥ {minimum}），sparse/0 可用于训练")
PY
