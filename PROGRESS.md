# PROGRESS — 3DGS 在线重建查看器 + 个人主页（前后端一体，服务双足实验室 3D 方向考核）

> 自动区由 `devloop.py` 维护，不要手改（改了会被覆盖）。最后更新：2026-10-05 00:54

<!-- DEVLoop:AUTO:START -->
## 当前阶段

**模块开发**　（模块 5/9 已完成）

## 模块进度

| # | 模块 | 状态 | 尝试 | 最近一次结论 |
|---|------|------|------|--------------|
| 1 | 脚手架 | 已完成 | 1 | 通过：backend: pytest tests -q -> 3 passed；uvicorn 实起后 curl /api/health -> HTTP 200 {"status":"ok","service":"web3d-lab API","version":"0.1.0","db":"web3d.db"}；frontend: npm run build -> tsc -b + vite build OK (dist/index.html 0.70kB, index.js 221KB)；浏览器 http://localhost:5173 渲染出「✓ 链路正常」并列出后端 version/db/uptime（vite 代理 /api -> 127.0.0.1:8000 实测 200） |
| 2 | 场景元数据API | 已完成 | 1 | 通过：pytest tests -q -> 11 passed；真实 HTTP 复验 backend/scripts/verify_api.py -> 全部通过（空库 GET /api/scenes 返回 200 {"total":0,"items":[]} 而非常见 404；POST 201 后中文标题 UTF-8 往返无损；未知 slug 404、重复 slug 409、缺字段 422、limit=0 422）；seed_scenes.py --reset -> 库中 2 条，GET 列表 total=2 |
| 3 | 3DGS查看器页 | 已完成 | 1 | 通过：tsc -p tsconfig.app.json --noEmit 无错；npm run build 通过（dist js 3.30MB，含 three+spark）；浏览器 127.0.0.1:5173/?scene=robot-head -> DOM 钩子 #viewer-state: status=ready splats=45401 loadMs=526 fps=76~147；截图像素核验 scripts/check_render.py -> 亮像素 9.88%、重心(0.49,0.45)、std 40.4 = 渲染有效；自动巡航 3 次采样相机 x: -0.530 -> -0.965 -> -1.386（在转）；滚轮事件使 z 4.628 -> 3.405（缩放生效）；4 个示例场景机器人头/壁炉/卧室/山谷均 status=ready 且 bbox 正常（山谷 916x342x415，按宽高比取景后亮像素 0.86%->4.58%）；错误路径 ?scene=desk-chair 显示「资产加载失败：Invalid gzip header」+ 路径提示 + 面板状态=加载失败 |
| 4 | 场景库与路由 | 已完成 | 1 | 通过：tsc 无错 + npm run build 通过；浏览器 /scenes -> 显示「共 4 个场景」+ 4 张卡片（缩略图由 scripts/make_thumbnails.py 从实拍截图裁出，亮度统计与原图一致）；点击卡片 -> 路由到 /scenes/robot-head，钩子 #viewer-state status=ready splats=45401；深链直接开 /scenes/valley 刷新后仍正常（SPA fallback + useParams）；/ 首页精选行显示 2 个 featured 场景；视觉核验无错位/破图 |
| 5 | 访问统计 | 已完成 | 1 | 通过：pytest tests -q -> 19 passed（含 30s 去重、独立访客去重、splat_load 单独计数、days 越界 422、+08 时区分桶）；真实 HTTP：POST /api/events -> 201 {id:1,deduped:false}，同参数 30s 内重发 -> 202 deduped:true；GET /api/stats 由 total_views=0 变为 3、splat_loads=2、per_scene=[(robot-head,2)]，日桶落在本地 2026-10-05；前端首页统计卡显示「3 累计浏览 / 2 独立访客 / 2 场景加载成功」+ 14 天 SVG 曲线，查看器页显示「已被浏览 2 次」——皆为浏览器真实上报后回读 |
| 6 | 留言板 | 待办 | 0 |  |
| 7 | 个人主页与方法对比 | 待办 | 0 |  |
| 8 | 训练管线 | 待办 | 0 |  |
| 9 | 部署 | 待办 | 0 |  |

## 问题与解决方案

（暂无）

## 跳过项（同一问题修复超过 5 次仍未解决）

（暂无）

## 端到端验收

- 结论：**未执行**

## 阻塞（需人工介入）

（无。无阻塞时不允许停下来等确认。）
<!-- DEVLoop:AUTO:END -->

## 手记（人写区，脚本不会覆盖）
（在这里写任何脚本管不着的东西：灵感、待确认的取舍、给用户的备注。）
