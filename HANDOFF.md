# HANDOFF —— web3d-lab 交接表

> 新会话开场**只读这一个文件 + `PROGRESS.md` 的自动区**，就够开工。
> 不要 dump `state.db` 考古、不要 resume 老会话——代价写在第五节坑表里。
> **最后更新：2026-10-05 15:35（桌面端 profile 10086 那条线）**

## 一、这条线已经发生过什么（会话表）

| 时间 | 会话 | 干了什么 | 留下的产物 | 花费 |
|---|---|---|---|---|
| 10-02 10:11 | `@session:10086/20261002_101154_7f2d80`<br>「开发3DCV项目发现与安装网站」 | 做静态个人页（3D 方向 + 三维视觉开源项目雷达），装 4 个技能，部署上线 | **https://shawn100861224.github.io/bipedal-lab-3d/**<br>`C:\Users\Shawn\lab\web-3d` | $0.29 |
| 10-04 12:04 | `@session:10086/20261004_120422_d40c7c`<br>「领取 DeepSeek 六元券」 | 领到 ¥6 赠金；桌面主模型切 native deepseek；装 5 个技能；**立项** | `D:\lab\web3d-lab` 立项 + README/PROGRESS/项目卡 | $0.51 |
| 10-05 00:22 | `@session:10086/20261005_002207_3ee8fa`<br>「继续上次会话」 | **模块 1–9 全部推进**：前后端一体站点 + 训练管线 + 部署上线；含 8GB 机器的显存上限实测 | 见「二、现在到哪了」 | $1.26 |

## 二、现在到哪了

**线上（可交付）：** https://shawn100861224.github.io/web3d-lab/ ← GitHub Pages，公开可访问
**仓库：** https://github.com/Shawn100861224/web3d-lab （含全部过程文档；构建产物不入库）

- ✅ **模块 1–7 全部完成并验收**（脚手架 / 场景元数据 API / 3DGS 查看器 / 场景库与路由 / 访问统计 / 留言板 / 个人主页与方法对比）
- ✅ **模块 8 训练管线跑通**：合成采集 40 视角 → COLMAP 40/40 注册 → gsplat 训练 → 导出 `.splat` → 网页实时渲染 → 指标回写
  - 另外用**公开数据集**（Mip-NeRF 360 counter，240 张真实照片、自带位姿）验证过真实照片链路：流程全绿，但**房间级重建在本机做不到**（见坑表「WSL 显存天花板」）
- 🟡 **模块 9 部署**：前端已上线；后端未上线（要自有域名，EdgeOne 默认域名是带鉴权的预览链接）
- 📄 《作品说明》一页 PDF：`docs/作品说明.pdf`（可随链接一起提交）
- 场景库现有 **5 个已发布场景**：4 个 spark 官方示例 + 1 个自训合成场景；房间级那个公开数据集场景因画质糊已转草稿（`published=false`，数据留着）

## 三、费用与额度（2026-10-05 实测，权威数字）

| 钱包 | 现状 |
|---|---|
| **DeepSeek 账户** | 余额 **¥26.23**（充值 26.23 + **赠金 0.00**）；累计消费 ≈ **¥80** |
| **ofox 钱包** | 充 $10、已用 **$6.82**、剩 **$3.18** |
| Hermes 两条线自身记账 | 92 会话 / 4,659 次调用 / **$7.98 ≈ ¥56.6**（ofox $4.48 · DeepSeek 直连 flash $1.45 · pro $1.20 · 微信线 v4-pro $0.82） |

- ⚠️ **¥6 赠金已全部用尽**（6.00 → 0.00，在 10/6 21:00 过期前刚好烧完）→ 不必再等它，也不必担心浪费
- 10-05 这一大轮（774 次调用、输出 48.4 万 tokens、含训练与十几轮失败重试）：**实付约 ¥6**（国庆假期闲时价 5 折）
- **省钱三杠杆**：① 长会话走缓存命中（当天 3.45 亿命中 tokens，单价约为未命中的 1/50）→ 少开新会话、多读交接文档；② 闲时时段跑重活；③ 重活压 Codex/Harness（同一 DeepSeek 账户，赠金/余额共享）
- 主模型当前 = native `deepseek`/`deepseek-flash`（走 `api.deepseek.com`，不需代理）；想回 ofox 就 `/model ofox`

## 四、坑表（别再重复踩）

| 坑 | 已确认的结论 |
|---|---|
| 用 Electron 交付 | ❌ 否决：交付形态是**链接**；安装包手机打不开、对 3D 零增益 |
| 从市场挑高星技能安装 | ✅ 已做过两轮（10-02 装 4 个、10-04 装 5 个）。再装先 `hermes skills list` 去重；每个安装 5–7 分钟（安全扫描主导） |
| 直连 GitHub / sparkjs.dev 下大文件 | ❌ 卡死；走 Clash 代理 `127.0.0.1:7897`（实测 100–740 KB/s）。反过来：npmmirror / 清华 PyPI / hf-mirror **要关代理**才快 |
| 读老会话上下文 | 用 `session_search(session_id="…")` 一次读全文；禁止 dump 数据库 |
| 桌面端一条会话聊到底 | 越聊越贵 → 换阶段就开新会话 + 读本文件 |
| **WSL 里 GPU 能分配多少显存** | ⚠️ **远低于标称**：8GB 卡实测单进程只能分配 **约 1.5 GB**（干净进程 2.7 GB），且**与 Windows 可用内存强相关**（实测 700 MB ↔ 2.7 GB）。训练前先关浏览器/游戏平台。探测脚本：`pipeline/tests/probe_vram.py` |
| **`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`** | ❌ WSL 下**不能开**：走 CUDA VMM 接口，会在"还有 5.8 GB 空闲"时报 `memory mapping failed with OOM`，连 20 MB 都分配不了（PyTorch 报错信息里推荐的参数，照做反而故障） |
| **房间级 3DGS 重建** | ❌ 本机做不到：参考实现要 **100–300 万高斯**，本机天花板约 6–10 万。**单物体/桌面级可行**（3–5 万高斯即可）→ 拍单个物体最合适 |
| **`huggingface_hub` 拉 HF 镜像** | ❌ 会卡死在元数据交互（5 分钟 0 字节）→ 改用镜像 resolve 地址直连并发下载（240 张 78 秒），见 `pipeline/05_fetch_public_dataset.py` |
| **`wsl.exe -lc` 内联命令里用 `$VAR`** | ❌ 变量会被外层吞掉（`du -sh $D` 量成了当前目录）→ **写成脚本文件再执行**，或用绝对路径 |
| WSL 的 `/tmp` | ⚠️ 是 tmpfs，**WSL 一重启日志就没了** → 日志写 `~/web3d/logs/` |
| GitHub Pages 建站 | 工作流里的 `GITHUB_TOKEN` **无权创建 Pages 站点**（`Resource not accessible by integration`）→ 先用 `gh api -X POST repos/<o>/<r>/pages -f build_type=workflow` 建好 |
| 静态托管的深链 | GitHub Pages 对未知路径返回 404（用 404.html 承载 SPA）→ 构建脚本会为每个已知路由生成**真实目录**，深链即可返回 200（`frontend/scripts/make_deep_link_dirs.py`） |
| EdgeOne 的免费域名 | ⚠️ 它的 `*.edgeone.cool` **是带鉴权的预览链接**（不带 token 返回 401、3 小时过期）；公开访问需绑**自有域名**（官方文档明确） |

## 五、技能清单（已装，无需再去找）

- **本项目在用**：`ui-ux-pro-max`、`ui-styling`、`fastapi`、`playwright`、`3d-orbit-inspect-demo`
- **其他已有**：`3dgs-paper-reader`、`3dgs-method-compare`、`autonomous-dev-loop`（项目进度状态机）、`web3d-lab`（项目卡）、`skill-creator`、`git`、`best-minds`、`find-skills`、`github-repo-quickstart`、`web-deploy-github`

## 六、下一步（按价值排序）

1. **拍照片**（只有本人能做）：手机环拍**单个物体或桌面** 30–50 张（多角度、相邻重叠 60%+、光照均匀、别拍糊、表面有纹理最好）
   → 给我照片后跑 `pipeline/run_all.sh`，把线上那个「合成采集（链路验证场景）」换成实拍场景
2. **可选：给后端一个自有域名**（`.cn` ¥38/年起）→ 我 1–2 小时把后端迁到 EdgeOne Cloud Functions（Python 原生支持 FastAPI，同域免 CORS），让访问统计与留言板真正在线
3. **可选：给 EdgeOne 项目绑域名**（同样需要先有域名，国内节点可能还需 ICP 备案）→ 换来更快的国内 CDN
4. 实验室任务线：按学长要求打 C++ / Linux 基础（WSL2 环境已就绪，首个 C++ 程序与 CMake 多文件项目已跑通）
