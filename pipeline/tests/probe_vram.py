"""探测本机（WSL2 + RTX 5060 8GB）真实可分配的显存上限。

背景：gsplat 报 "Tried to allocate 322.00 MiB ... 5.58 GiB is free"，
而 torch 只占了 1.12 GiB —— 数字自相矛盾（报错里还有 17179869184 GiB 这种溢出值），
说明 nvidia-smi/驱动的"空闲"数不可信。这里用逐步分配测真实天花板。
"""

import torch

print("torch", torch.__version__, "| cuda", torch.version.cuda)
free_b, total_b = torch.cuda.mem_get_info()
print(f"torch 报告的初始：free {free_b/1024**3:.2f} GiB / total {total_b/1024**3:.2f} GiB")

blocks = []
sizes_mb = [100, 200, 400, 800, 1200, 1600, 2000, 2500, 3000, 3500, 4000]
total = 0
for mb in sizes_mb:
    try:
        blocks.append(torch.empty(mb * 1024 * 1024, dtype=torch.uint8, device="cuda"))
        total += mb
        torch.cuda.synchronize()
        fb, tb = torch.cuda.mem_get_info()
        print(f"  成功: 本次 {mb} MB，累计 {total} MB | 之后 free {fb/1024**3:.2f} GiB")
    except Exception as exc:
        print(f"  ✗ 失败: 尝试 {mb} MB（累计已 {total} MB）-> {str(exc)[:120]}")
        break

print(f"\n结论：本环境单进程可分配约 {total} MB（约 {total/1024:.1f} GiB）")
print("若明显低于 8 GB 显卡标称值，说明 WSL/WDDM 侧有额外限制，需要按实测值配置训练参数。")
