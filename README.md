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

自检：浏览器开 http://localhost:5173 ，页面应显示「✓ 链路正常」并列出后端 version / db / uptime。

## 新会话怎么接手（重要）

- **续跑**：读 `PROGRESS.md` 看「进行中/待办」，跑
  `python <skills>/autonomous-ai-agents/autonomous-dev-loop/scripts/devloop.py check`
  从下一个模块接着做；不要重新侦察已定的技术栈。
- **恢复原对话**：桌面端左栏点这条会话，或 `hermes --resume <session_id>`。
- **自主开发循环**默认开启：不停下等确认，但**拍摄照片、发布上线、花真钱、注册第三方账号**这四类必须停下来问本人。

## 环境快照（截至 2026-10-04）

- 已装技能（下一会话生效）：`ui-ux-pro-max`、`ui-styling`、`fastapi`、`playwright`、`3d-orbit-inspect-demo`。
- Hermes(profile 10086) 主模型临时 = native `deepseek`/`deepseek-flash`（消耗 Harness 活动赠金，赠金优先于充值余额扣），另留别名 `ofox` 回切；**赠金 2026-10-06 21:00 过期**。
- 本机：RTX 5060 Laptop 8GB / 16GB DDR5 / D 盘余 ~600GB / WSL2 Ubuntu-24.04 已装（训练用）。
