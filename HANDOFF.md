# HANDOFF —— web3d-lab 交接表

> 新会话开场**只读这一个文件**（再扫一眼 `PROGRESS.md` 的自动区）就够开工。
> 不要 dump `state.db` 考古、不要 resume 老会话——两者的代价都写在下面"坑表"里。

## 一、这条线已经发生过什么（会话表）

| 时间 | 会话 | 干了什么 | 留下的产物 | 花费 |
|---|---|---|---|---|
| 10-02 10:11 | `@session:10086/20261002_101154_7f2d80`<br>「开发3DCV项目发现与安装网站」 | 做静态个人页（3D 方向 + 三维视觉开源项目雷达），装 4 个技能，部署上线 | **https://shawn100861224.github.io/bipedal-lab-3d/**（已实测 HTTP 200 在线）<br>`C:\Users\Shawn\lab\web-3d` | $0.29 / 83 次调用 |
| 10-04 12:04 | `@session:10086/20261004_120422_d40c7c`<br>「领取 DeepSeek 六元券」 | 领到 6 元赠金（Harness 登出重登）；桌面 Hermes 主模型切到 native deepseek；装 5 个技能；**立项**并建 README / PROGRESS / 项目卡技能 | 赠金 ¥6（10/6 21:00 过期）<br>`D:\lab\web3d-lab` 立项<br>5 个技能 + `web3d-lab` 项目卡 | $0.64 / 225 次调用 |
| 10-05 00:22 | `@session:10086/20261005_002207_3ee8fa`<br>「继续上次会话」 | 模块 1（脚手架）、模块 2（场景元数据 API）**通过验收**；开始模块 3（3DGS 查看器），下好 2 个 SPZ 资产；顺带发现统计日桶按 UTC 切天的 bug | `backend/`、`frontend/`、seed 数据、`backend/scripts/verify_api.py`；PROGRESS.md 自动区 | $0.20 / 272 次调用 |

合计约 **$1.13**（走 DeepSeek 直连＝赠金；ofox 侧只有零头）。

## 二、现在到哪了

以 `PROGRESS.md` 的自动区为准（**机器维护，禁止手写**）：

- ✅ 模块 1 脚手架、模块 2 场景元数据 API（都有真实证据：pytest 11 passed、`curl /api/health` 200、边界 404/409/422 全过）
- 🔄 模块 3 3DGS 查看器页
- ⬜ 模块 4–9

```bash
python "C:/Users/Shawn/AppData/Local/hermes/profiles/10086/skills/autonomous-ai-agents/autonomous-dev-loop/scripts/devloop.py" check
```

## 三、别再重复的劳动（坑表）

| 坑 | 已确认的结论 |
|---|---|
| 用 Electron 交付 | ❌ 否决：交付形态是**链接**，Electron 是安装包、手机打不开、对 3D 零增益 |
| "从市场挑高星项目安装" | ✅ **已做过两轮**（10-02 装 4 个、10-04 装 5 个，清单见第四节）。再要装先 `hermes skills list` 去重 |
| 直连 GitHub / sparkjs.dev 下大文件 | ❌ 卡死；走 Clash 代理 `127.0.0.1:7897` 实测 ~106 KB/s |
| 安装 Hermes 技能 | 每个 **5–7 分钟**（安全扫描主导）；`hermes skills install <id> --yes`；被扫拦时先审计再 `--force` |
| 想读老会话的上下文 | 用 `session_search(session_id="…")` **一次读全文**；禁止 dump 数据库 / 写临时脚本 / `sed` 翻页 |
| 按目录恢复会话（`--workspace` / `--in`） | ⚠️ 对**桌面会话无效**（70 条里只有 1 条记录了 cwd）→ 只能按 **ID 或标题**恢复 |
| 桌面端一条会话聊到底 | 越聊越贵（那条已出现 **1200 万 token** 的重复读取）→ 换阶段就开新会话 + 读本文件 |

## 四、技能清单（已装，无需再去找）

- **本项目要用**：`ui-ux-pro-max`、`ui-styling`、`fastapi`、`playwright`、`3d-orbit-inspect-demo`
- **其他已有**：`3dgs-paper-reader`、`3dgs-method-compare`、`best-minds`、`find-skills`、`github-repo-quickstart`、`web-deploy-github`、`skill-creator`、`git` + 一批官方/本地技能

## 五、下一步（按顺序）

1. **模块 3 收尾**——3DGS 查看器页（可以 resume `@session:10086/20261005_002207_3ee8fa` 接着做，或新会话读本表开工）
2. 模块 4–7：场景库与路由 → 访问统计 → 留言板 → 个人主页与方法对比
3. **需要本人出手的两件事**：拍照片（模块 8 训练管线）、决定是否发布公网（模块 9）
4. **10/6 21:00 赠金过期**，之后把主模型切回 ofox：
   `hermes config set model.default deepseek/deepseek-v4.1-flash` + `hermes config set model.provider custom:ofox`
