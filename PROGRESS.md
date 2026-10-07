# PROGRESS — 3DGS 在线重建查看器 + 个人主页（前后端一体，服务双足实验室 3D 方向考核）

> 自动区由 `devloop.py` 维护，不要手改（改了会被覆盖）。最后更新：2026-10-07 19:51

<!-- DEVLoop:AUTO:START -->
## 当前阶段

**完成**　（模块 9/9 已完成）

## 模块进度

| # | 模块 | 状态 | 尝试 | 最近一次结论 |
|---|------|------|------|--------------|
| 1 | 脚手架 | 已完成 | 1 | 通过：backend: pytest tests -q -> 3 passed；uvicorn 实起后 curl /api/health -> HTTP 200 {"status":"ok","service":"web3d-lab API","version":"0.1.0","db":"web3d.db"}；frontend: npm run build -> tsc -b + vite build OK (dist/index.html 0.70kB, index.js 221KB)；浏览器 http://localhost:5173 渲染出「✓ 链路正常」并列出后端 version/db/uptime（vite 代理 /api -> 127.0.0.1:8000 实测 200） |
| 2 | 场景元数据API | 已完成 | 1 | 通过：pytest tests -q -> 11 passed；真实 HTTP 复验 backend/scripts/verify_api.py -> 全部通过（空库 GET /api/scenes 返回 200 {"total":0,"items":[]} 而非常见 404；POST 201 后中文标题 UTF-8 往返无损；未知 slug 404、重复 slug 409、缺字段 422、limit=0 422）；seed_scenes.py --reset -> 库中 2 条，GET 列表 total=2 |
| 3 | 3DGS查看器页 | 已完成 | 1 | 通过：tsc -p tsconfig.app.json --noEmit 无错；npm run build 通过（dist js 3.30MB，含 three+spark）；浏览器 127.0.0.1:5173/?scene=robot-head -> DOM 钩子 #viewer-state: status=ready splats=45401 loadMs=526 fps=76~147；截图像素核验 scripts/check_render.py -> 亮像素 9.88%、重心(0.49,0.45)、std 40.4 = 渲染有效；自动巡航 3 次采样相机 x: -0.530 -> -0.965 -> -1.386（在转）；滚轮事件使 z 4.628 -> 3.405（缩放生效）；4 个示例场景机器人头/壁炉/卧室/山谷均 status=ready 且 bbox 正常（山谷 916x342x415，按宽高比取景后亮像素 0.86%->4.58%）；错误路径 ?scene=desk-chair 显示「资产加载失败：Invalid gzip header」+ 路径提示 + 面板状态=加载失败 |
| 4 | 场景库与路由 | 已完成 | 1 | 通过：tsc 无错 + npm run build 通过；浏览器 /scenes -> 显示「共 4 个场景」+ 4 张卡片（缩略图由 scripts/make_thumbnails.py 从实拍截图裁出，亮度统计与原图一致）；点击卡片 -> 路由到 /scenes/robot-head，钩子 #viewer-state status=ready splats=45401；深链直接开 /scenes/valley 刷新后仍正常（SPA fallback + useParams）；/ 首页精选行显示 2 个 featured 场景；视觉核验无错位/破图 |
| 5 | 访问统计 | 已完成 | 1 | 通过：pytest tests -q -> 19 passed（含 30s 去重、独立访客去重、splat_load 单独计数、days 越界 422、+08 时区分桶）；真实 HTTP：POST /api/events -> 201 {id:1,deduped:false}，同参数 30s 内重发 -> 202 deduped:true；GET /api/stats 由 total_views=0 变为 3、splat_loads=2、per_scene=[(robot-head,2)]，日桶落在本地 2026-10-05；前端首页统计卡显示「3 累计浏览 / 2 独立访客 / 2 场景加载成功」+ 14 天 SVG 曲线，查看器页显示「已被浏览 2 次」——皆为浏览器真实上报后回读 |
| 6 | 留言板 | 已完成 | 1 | 通过：pytest tests -q -> 28 passed（含空列表200、原文存储、限流、按场景过滤、越界422）；真实 HTTP：连续 3 条 201、第 4 条 429「请 600 秒后再试」+ Retry-After 头；读回确认留言正文里的 <img src=x onerror=...> 原样保存（未被预转义）且响应不含 client_id；前端浏览器实测：注入载荷 imgX=0 / scriptNodes=0 / window.__xssFired 未定义 / 载荷只以文本呈现（React 默认转义），真人填写表单提交 -> 「留言已提交」+ 列表新增 + 库中回读，再提交第 4 次 -> 界面显示「提交太频繁：留言太频繁，请 574 秒后再试」；seed_guestbook.py --reset 清掉验证垃圾、灌 3 条示例，页面回读「共 3 条」 |
| 7 | 个人主页与方法对比 | 已完成 | 1 | 通过：tsc 无错 + npm run build 通过；浏览器 /about -> 六个板块全部渲染（方向/真实做过的事×5/小尝试与踩坑/雷达/用AI过程/下一步），无 dangerouslySetInnerHTML（改用 JSX，全页仅 Vite dev 自带 3 个 script）；项目雷达读取 public/radar.json（从原静态页并入的真实抓取数据）：116 仓库 / 31 我读过 / 8 星速爆发 / 685,077 合计星标、11 个分类计数正确、搜索+排序选择器就位；浏览器 /methods -> 表格 9 行 × 8 列（几何基元/表面质量/规模/速度/压缩/开源/对我意味着什么），每行「为什么和我有关」列均有内容 |
| 8 | 训练管线 | 已完成 | 1 | 通过：云端 GPU（AutoDL vGPU-32GB，31GB 显存）跑 gsplat DefaultStrategy 30000 步，全分辨率 2016x1512：31 训练 + 8 留出视角（--holdout-mode ring 按相机方位角均匀留出，修掉 tail 留出一整段连续弧≈70°盲区）。三组同数据对照：down=2 全量稠密化 647,860 高斯 / 留出 PSNR 14.46 / SSIM 0.678；down=1 保守稠密化 14,612 高斯 / 14.52 / 0.765；down=1 中等稠密化 66,904 高斯 / 14.443 / 0.7333（上线版：训练 659s，显存峰值 869MB，资产 2,140,928B）。本机冒烟 300 步导出 web_300.splat=1268 点/40,576B（字节数被 32 整除）；.splat 记录必须含四元数（32B/条）由浏览器报错验证。 |
| 9 | 部署 | 已完成 | 1 | 通过：EdgeOne Makers 改走官方 CLI 自动部署：edgeone login --site china → edgeone makers deploy ./frontend/dist-edgeone -n web3d-lab --json → projectId=makers-jtlpapfcff7f、deploymentId=dp0idbc84qru、status=success。真机验收 https://www.shawnlab.cn/scenes/shoe/：#viewer-state data-status=ready、data-splats=66904、data-bytes=2140928、data-load-ms=3120、data-error 空，面板 PSNR 14.44dB / SSIM 0.7333 / 30,000 步。两处入口资产 md5 与本地一致 dc972cbc0a7392f4e28fc8e69cd274b9，GitHub Actions 37502296567 success 39s。教训：Pages 版（base=/web3d-lab/）deploy 到 EdgeOne 会白屏，EdgeOne 必须用 build-for-edgeone.sh 的 dist-edgeone（base=/）。 |

## 问题与解决方案

（暂无）

## 跳过项（同一问题修复超过 5 次仍未解决）

（暂无）

## 端到端验收

- 结论：**通过**
- 2026-10-07 17:26：访客路径全站走查（本地后端+前端真机）：①后端 pytest 36 项全绿；scripts/verify_api.py 修复为幂等+自清理后连跑两次全绿（空库 200、POST 201、中文标题往返、未知 slug 404、重复 409、缺字段/越界 422）；②首页：精选 2 个官方场景带缩略图、统计条 57 浏览 / 20 独立访客 / 40 场景加载 + 14 天曲线、分场景排行（shoe 18 次最高）；③场景库：7 张卡片全部有缩略图（含 3 个自训场景）；④查看器 /scenes/shoe：钩子 status=ready、66,904 高斯、2,140,928 字节、默认机位 az153/el14、无错误；⑤留言板：有后端时显示可写表单 + 7 个场景下拉，空列表文案正确（写入链路实测：写 1 条→库中确有该行→已删除，删后可见 0 条）；⑥关于我：8 条真实做过的事 + 小尝试 7 条 + 踩坑 7 条，本轮内容已上线；⑦线上两处入口资产/快照 md5 与本地一致。
- 2026-10-07 19:51：后端云上上线验收（EdgeOne Cloud Functions + Neon Postgres）：① scripts/verify-cloud.sh 在预览域与正式域各 7/7 通过 —— 健康检查 200（db 显示 postgres:ep-...pooler）、场景列表 total=7、留言板 200、访问统计 200（含 14 天序列）、随机路径兜底 html 对照、辅助包无路由泄漏、首页 200；② 线上首页实测渲染出来自数据库的实时统计（2-4 浏览/2-3 独立访客）与 2 个精选场景；③ 线上留言板显示可写表单+场景下拉（不再显示离线快照提示）；④ 浏览器实测四个请求全部成功：/api/health 200、/api/stats 200、/api/scenes?featured=true 200、/api/events 201；⑤ 后端本地 pytest 36 项全绿；scripts/pg_smoke.py 对真实 Neon 跑通写/读/按天聚合/清理（残留 0）；⑥ 数据：场景元数据 9 条已灌入（公开 7 条），留言与统计从上线时刻起算真实数据。

## 阻塞（需人工介入）

（无。无阻塞时不允许停下来等确认。）
<!-- DEVLoop:AUTO:END -->

## 手记（人写区，脚本不会覆盖）
（在这里写任何脚本管不着的东西：灵感、待确认的取舍、给用户的备注。）
