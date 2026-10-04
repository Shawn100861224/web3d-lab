# web3d-lab —— 3DGS 在线重建查看器 + 个人主页

> 双足实验室招新考核作品（3D / 三维视觉方向）。**前后端一体**，核心卖点：访客能在浏览器里实时旋转作者亲手训练的 3D Gaussian Splatting 场景，并看到真实训练指标。

## 为什么是它（定位）

- 考核里绝大多数人交静态个人主页；能把**自己训出来的 3DGS 场景**放进网页实时渲染的几乎没有 —— 这就是差异化的全部。
- 后端不是装饰：场景元数据/指标、访问统计、留言板、渲染帧率回写，都是真接口。
- 与「软件工程」身份对齐：前端工程化 + API 设计 + 数据库 + 容器部署，一条链都能讲。

## 技术栈（已定）

| 层 | 选型 | 说明 |
|---|---|---|
| 前端 | Vite + React + TypeScript | 页面/路由 |
| 3D 渲染 | Three.js + `@sparkjsdev/spark` | 支持 ply/spz/splat/ksplat；官方有 R3F 模板 |
| 后端 | Python 3.12 + FastAPI + SQLModel + SQLite | 与训练脚本同语言，任务队列不用跨语言 |
| 训练 | WSL2 Ubuntu-24.04 + PyTorch(cu12x) + gsplat + COLMAP | 本机 RTX 5060 8GB，只做小场景（单物体/桌面） |
| 部署 | docker-compose（nginx + uvicorn）+ Cloudflare Tunnel | 免服务器费用即可给公网链接 |
| 测试 | pytest + httpx（后端）、Playwright（端到端） | 验收用真实浏览器点一遍 |

**明确不用 Electron**：交付形态是「一个链接」。Electron 要下载安装包、手机打不开、3D 能力零增益；将来真要桌面版，用 Tauri 套壳（~5MB）而不是现在。

## 模块与验收标准

状态由 `.devloop/state.json` 维护，`PROGRESS.md` 由脚本渲染 —— **不要手写 PROGRESS.md**。

| # | 模块 | 验收方式 |
|---|---|---|
| 1 | 脚手架 | 前后端各一条命令能起，页面/JSON 有响应 |
| 2 | 场景元数据 API | `curl /api/scenes` 返回预期 JSON + 空结果路径 |
| 3 | 3DGS 查看器页 | 浏览器打开能转、能显示指标面板（截图为准） |
| 4 | 场景库与路由 | 卡片从 API 拉取，点击进详情 |
| 5 | 访问统计 | POST 写库后 `/api/stats` 曲线变化 |
| 6 | 留言板 | POST/GET 通，注入 `<script>` 被转义，有限流 |
| 7 | 个人主页与方法对比 | 并入 `lab/web-3d` 的内容，3DGS 方法对比成页 |
| 8 | 训练管线 | COLMAP → 3DGS → 导出 .spz + 指标回写（**需要照片**） |
| 9 | 部署 | docker-compose 起得来 + 公网链接（**发布前问用户**） |

## 需要用户（本人）输入的三件事

1. **照片**：手机环拍单个物体/桌面 30–50 张（模块 8 需要；模块 1–7 先用 spark 官方示例 `.spz` 跑通）。
2. **是否发布到公网** + 用免费隧道还是自有服务器。
3. 现有 `C:\Users\Shawn\lab\web-3d`（静态页）**归另一个 Hermes 实例维护**，本项目另起目录，最后把其中的 About 内容并进来。

## 本地开发命令（模块 1 起可用）

```bash
# 后端（端口 8000）
cd D:/lab/web3d-lab/backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 前端（端口 5173，dev server 已把 /api 反代到 8000）
cd D:/lab/web3d-lab/frontend && npm run dev
```

自检：浏览器开 http://127.0.0.1:5173/?scene=robot-head ，应看到左侧视口里可旋转的 3DGS 场景 + 右侧指标面板。

## 前端验收钩子

查看器把实时状态镜像到 DOM 的 `#viewer-state`（`data-status` / `data-splats` / `data-fps` /
`data-camera` / `data-extent` / `data-bbox` / `data-error`），Playwright 与脚本用它断言，
不用去猜画面。相关脚本：`frontend/scripts/check_render.py`（截图像素级判空画布）。

## 示例资产（frontend/public/demo/）

4 个示例 `.spz` 共约 19 MB，来自 spark 官方示例清单（`sparkjs.dev` 的
`examples/assets.json`），用途是「先把链路跑通」，模块 8 会用自训场景替换掉最显眼的位置。
重新拉取用 `frontend/scripts/fetch-demo-assets.sh`（**必须走 Clash 代理**，直连 sparkjs.dev 速度为 0）。

| 文件 | 点数 | 包围盒（世界单位） | 实测 |
|---|---|---|---|
| `robot-head.spz` | 45,401 | 单物体 | 加载 0.5s，headless 下 76–147 FPS |
| `fireplace.spz` | 301,000 | 8.2×6.5×7.0 | 正常 |
| `painted-bedroom.spz` | 500,000 | 10.3×7.3×11.5 | 正常 |
| `valley.spz` | 500,000 | 915.9×341.6×414.8 | 正常，需按宽高比取景 |

**踩过的坑（模块 8 导出 .spz 时必看）**：`snow-street.spz`（官方示例之一，981,908 点）
在 spark 2.3.1 下 `numSplats` 能解析成 981,908，但 `getBoundingBox()` 返回**空盒**
（size 全为 ±Infinity）、画面全黑。解压后对比头部发现它与其他文件不同：

```
NGSP v2 头：magic(4) version(4) numPoints(4) shDegree(1) fractionalBits(1) flags(1) reserved(1)
robot-head       sh=3  fractionalBits=12   ← 正常
valley/fireplace sh=0  fractionalBits=12   ← 正常
snow-street      sh=2  fractionalBits=6    ← 空盒、画面全黑
```

结论：**导出自训场景时用 fractionalBits=12**（gsplat / spark `writeSpz` 的默认值），
不要用 6。查看器里已对退化 bbox 做了兜底（退回半径 1 的机位），但兜底救不回数据本身。
诊断脚本：`frontend/scripts/inspect_spz.mjs`（离线读点位）、`frontend/scripts/check_render.py`
（对截图做像素级「非空画布」判定）。

## 新会话怎么接手（重要）

- **先读 `HANDOFF.md`**（交接表：这条线发生过什么 / 留下什么 / 别再重复什么 / 下一步），再读 `PROGRESS.md` 的自动区。
- **续跑**：读 `PROGRESS.md` 看「进行中/待办」，跑
  `python <skills>/autonomous-ai-agents/autonomous-dev-loop/scripts/devloop.py check`
  从下一个模块接着做；不要重新侦察已定的技术栈。
- **恢复原对话**：桌面端左栏点这条会话，或 `hermes --resume <session_id>`。
- **自主开发循环**默认开启：不停下等确认，但**拍摄照片、发布上线、花真钱、注册第三方账号**这四类必须停下来问本人。

## 环境快照（截至 2026-10-04）

- 已装技能（下一会话生效）：`ui-ux-pro-max`、`ui-styling`、`fastapi`、`playwright`、`3d-orbit-inspect-demo`。
- Hermes(profile 10086) 主模型临时 = native `deepseek`/`deepseek-flash`（消耗 Harness 活动赠金，赠金优先于充值余额扣），另留别名 `ofox` 回切；**赠金 2026-10-06 21:00 过期**。
- 本机：RTX 5060 Laptop 8GB / 16GB DDR5 / D 盘余 ~600GB / WSL2 Ubuntu-24.04 已装（训练用）。
