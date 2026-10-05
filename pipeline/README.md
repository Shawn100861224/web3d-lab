# pipeline —— 训练管线（COLMAP → 3DGS → 导出 → 网页）

这条管线的目标：**把一组照片变成网页里能转的 3DGS 场景**，每一步都能单独跑、单独验证。

```
00_setup_gs_env.sh             准备训练环境（CUDA 工具链 + gsplat）
01_make_synthetic_capture.py   合成一组多视角照片（离线可复现，用于链路验证）
02_colmap_sfm.sh               COLMAP 稀疏重建：照片 → 相机位姿 + 稀疏点云
03_train_gsplat.sh / .py       gsplat 训练 3DGS：COLMAP 数据集 → 高斯点云 .ply + PSNR/SSIM
04_export_to_web.py            导出适合上网的 PLY + 回写指标到后端
tests/test_colmap_parser.py    解析器自测（不依赖真实数据）
```

## 环境（本机实测，2026-10-05，全部在 WSL2 里）

| 项 | 值 |
|---|---|
| 系统 | WSL2 Ubuntu-24.04，内核 6.18.40.1-microsoft-standard-WSL2 |
| GPU 直通 | NVIDIA GeForce RTX 5060 Laptop GPU / 8151 MiB / 驱动 610.74 ✅ |
| 资源 | 8 核 / 7.8 GB 内存（WSL 上限）/ 磁盘 954 GB 可用 |
| 工具链 | python3.12 · gcc 13.3 · cmake 3.28 · ninja · git ✅ |
| COLMAP | **3.9.1（apt 装，无 CUDA）** → SIFT 必须加 `--SiftExtraction.use_gpu 0`，否则直接报错 |
| PyTorch | **2.14.1+cu130**，`torch.cuda.is_available()=True`，算力 **(12, 0) = sm_120 Blackwell** |
| CUDA 编译器 | **自己拼的 CUDA 13.4**（见下节），`CUDA_HOME=~/web3d/cuda-debs-extracted/usr/local/cuda-13.4` |
| Python 环境 | `~/web3d/venv`；数据放 `~/web3d/data/`（9p 跨文件系统比内盘慢一个量级）—— **但见下方「WSL 空闲即关」**：写进 WSL 内盘的未落盘数据会在硬重启中丢失，**要求结果可存活时请把数据集放 `/mnt/d/...`** |

## 环境搭建踩的四个坑（都别再踩）

1. **gsplat 没有 Blackwell 的预编译轮子。** 官方轮子索引（`docs.gsplat.studio/whl`）只发到
   `pt24cu124`，而 RTX 50 系需要 CUDA 12.8+。→ 只能 JIT 编译 CUDA 核 → **必须有 nvcc**。
2. **torch 自带的 CUDA 组件里没有 nvcc。** `site-packages/nvidia/cu13` 只有头文件和 `.so`；
   pip 的 `nvidia-cuda-nvcc-cu12` 也只带 `ptxas` + crt 头。→ 得另想办法拿 nvcc。
3. **Ubuntu 24.04 仓库的 `nvidia-cuda-toolkit` 是 CUDA 12.0**，编不出 sm_120。→ 不能用 apt 装。
4. **CUDA 13 把 nvvm 改名成了 `libnvvm`**（12.x 时叫 `cuda-nvvm`）。只下 `cuda-nvcc-13-4`
   会得到 `.../nvvm/bin/cicc: not found` —— `cicc` 是编译前端的核心，缺它 nvcc 只能干瞪眼。

**最终解法**：从 NVIDIA 官方 deb 仓库抓 `cuda-nvcc-13-4` + **`libnvvm-13-4`** + `cuda-crt-13-4`
+ `cuda-cudart(-dev)-13-4`，用 `dpkg-deb -x` 解到自己的目录（**不动系统、不需要 root、不装包**），
deb 内部是 `./usr/local/cuda-13.4/` 结构，所以 `CUDA_HOME` 指向那一层。验证方式不是看版本号，
而是**真的编译一个 `-arch=sm_120` 的 kernel 并跑起来**（`00_setup_gs_env.sh` 第 5 步）。

## 输入纹理踩的三个坑（合成采集为什么长这样）

模块 8 要验证的是**链路本身**（特征能不能匹配、训练能不能收敛、导出的文件能不能在网页渲染），
不是「照片拍得好不好」。真实照片只有本人能拍，所以在照片到位前用 01 合成一组等价输入。
但合成输入也要讲究，前两版纹理都让 COLMAP 直接失败：

| 版本 | 纹理 | 结果 | 原因 |
|---|---|---|---|
| v1 | 1024×512 纯高频白噪声 | **40 张只注册 2 张** | 同一块纹理在不同视角下采样点全变，SIFT 没有稳定特征 |
| v2 | 多尺度分形噪声 + 棋盘地面 | **依然只注册 2 张** | 自相似 + 周期性太强 → 匹配到大量**错误**对应，RANSAC 全否 |
| v3 | **抖动网格 Voronoi 马赛克**（随机格色 + 暗色格边 + 高亮点） | **40/40 全注册，18069 点，重投影误差 0.356px** | 每格唯一、边缘密集、无周期性 ≈ 摄影测量的标定板 |

**照片到位后**，把 `<data>/images/` 换成真实照片，02/03/04 一个字都不用改。

## 一键跑法

```bash
# 在 WSL 里（wsl -d Ubuntu-24.04 -u shawn）
cd ~/web3d && source venv/bin/activate
DATA=~/web3d/data/toy40

python /mnt/d/lab/web3d-lab/pipeline/01_make_synthetic_capture.py --out "$DATA" --views 40
bash   /mnt/d/lab/web3d-lab/pipeline/02_colmap_sfm.sh "$DATA" 0.6
bash   /mnt/d/lab/web3d-lab/pipeline/03_train_gsplat.sh "$DATA" 7000
python /mnt/d/lab/web3d-lab/pipeline/04_export_to_web.py --data "$DATA" --slug toy-capture
```

> 注意：**在 `wsl.exe -c "...$VAR..."` 这种内联命令里不要用 shell 变量** —— 本机实测里
> `$VAR` 会被外层吃掉变成空串（`mkdir -p $D` 会报 "missing operand"、`for c in ...; $c`
> 会变成空）。要么写成脚本文件再 `bash script.sh`，要么用绝对路径。

## ⚠️ 8GB 笔记本的可达上限（2026-10-05 实测，结论最重要）

用公开数据集（Mip-NeRF 360 `counter`，240 张真实照片、自带 COLMAP 位姿）试房间级重建时，
撞上一个**硬限制**：**WSL 下 GPU 单进程能分配的显存远低于标称值**。

| 实测 | 数字 |
|---|---|
| 干净进程逐步分配（`tests/probe_vram.py`） | 100+200+400 = 700 MB 成功；单独再要 800 MB **失败** |
| 关掉 WSL 释放宿主内存后重测 | 可分配上限 **700 MB → 2700 MB** |
| 驱动同时声称的空闲 | 6.87 GiB（**数字不可信**，报错里还有 `17179869184 GiB` 这种溢出值） |
| 训练进程里的实际天花板 | 约 1.5 GB（320 MB 的分配在"还有 5.1 GiB 空闲"时报 OOM） |

**两个可操作的结论**：

1. **显存上限与 Windows 可用内存强相关**（WDDM 下 GPU 显存用系统内存兜底）。实测：
   Windows 只剩 1.7 GB 空闲时上限 700 MB；关掉 WSL 释放到 5.8 GB 后立刻变成 2700 MB。
   → **训练前先看宿主内存**（`Get-CimInstance Win32_OperatingSystem` 的 FreePhysicalMemory），
   把浏览器/游戏平台之类关掉，能直接换来 4 倍的可用显存。
2. **`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 在 WSL 上不能开**。它走 CUDA VMM 接口，
   会在"还剩 5.83 GiB 空闲"时报 `memory mapping failed with OOM`，连 20 MB 都映射不了。
   这是 PyTorch 自己报错信息里推荐的参数 —— 在本环境照做反而制造故障。

**房间级 vs 单物体（决定能做什么）**：

| 场景类型 | 参考实现需要的点数 | 本机能给 | 结果 |
|---|---|---|---|
| 单物体 / 桌面（如官方的 robot-head 4.5 万点） | 3–5 万 | 6–30 万 ✅ | 能看 |
| 房间 / 街景（如 Mip-NeRF 360 counter） | 100–300 万 | 6.6 万（压到 down=4 也只到 6.6 万） | **糊到认不出**（PSNR 11.6） |

→ **本机适合小场景**（就是 README 里「手机环拍单个物体 / 桌面」那条路）；
房间级要么换原生 Windows CUDA 环境（绕开 WSL 的分配限制），要么换显卡。

## 性能观测（重要，别凭直觉估）

| 配置 | 每步耗时 | 7000 步总耗时 | 显存峰值 | 备注 |
|---|---|---|---|---|
| 450×337（--down 2），18k~33k 点 | ~0.041 s | **290 s** | 288–782 MB | 可用 |
| 900×675（--down 1），17.6k 点 | **~3.6 s** | 30000 步 ≈ **30 小时** | 2094 MB | 慢约 20 倍，**已放弃** |

全分辨率比按像素数（4×）推算慢了约 20 倍，说明有非线性开销（怀疑在每步的可微 SSIM 卷积
和 SH3 求值上，但**我没有 profile 过，不下结论**）。当前策略：

* 合成采集场景用 **--down 2 + 7000 步**（5 分钟一轮），够验证链路；
* 真实照片到位后若要更好的画质：先在 `--steps 10` 下跑一次计时，确认每步耗时再决定步数与分辨率，
  或者改用官方 gsplat `examples/simple_trainer.py`（它的实现经过优化，本仓库的精简版是为了
  零额外依赖而手写的）。

## 每一步的验收信号

| 步骤 | 通过标准 | 本机实测结果 |
|---|---|---|
| 00 | `nvcc -arch=sm_120` 能编译并跑起来 | ✅ `sm_120 compile+link OK` |
| 01 | 图不是黑的（平均亮度 > 100） | ✅ 40 张，平均亮度 140.5 |
| 02 | `registration_rate ≥ 起点阈值`（脚本默认 0.6，低于它**直接报错退出**） | ✅ 1.0（40/40），18069 点 |
| 03 | 训练日志 PSNR 上升、产出 `ckpt_*.ply` 与 `metrics.json` | 见运行日志 |
| 04 | 后端能读到新场景，网页 `/scenes/<slug>` 能转 | 见运行日志 |
