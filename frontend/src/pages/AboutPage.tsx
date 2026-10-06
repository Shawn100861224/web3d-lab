import { useEffect } from 'react'
import ProjectsPreview from '../components/ProjectsPreview'
import { trackEvent } from '../lib/api'

/**
 * /about —— 个人主页。内容由原静态考核页（lab/web-3d）的文案并入，
 * 并结合本项目补了「这个站是怎么做的」一段。
 * 四类必须本人确认的信息（联系方式、高中经历等）此处刻意留白，不替本人编。
 */

const DID: { when: string; tag: string; title: string; body: string }[] = [
  {
    when: '2026 年 9 月 · 班务',
    tag: '做成了',
    title: '让 AI 把班级群的 53 人名单变成 Excel',
    body: '当副班长后，考勤和早晚自习统计要反复用班级名单，但名单散在微信群里、格式是「姓名+学号+手机号」的昵称。我让 AI 直接在桌面端驱动微信窗口逐批读取昵称，最后整理成一张能用的表。',
  },
  {
    when: '2026 年 9 月 · 班务',
    tag: '做成了',
    title: '用脚本改考勤表，而不是手工搬列',
    body: '需要给「课堂考勤表」补上周六周日两天的 10 列，还要保留原来的合并单元格、表头、底色。手工做要反复复制粘贴还容易错，我改成让 AI 写 openpyxl 脚本：先解除所有合并、插入列、按模板逐格复制样式、再按位移重建合并区。跑完一次就对上了。',
  },
  {
    when: '2026 年 10 月 · 环境',
    tag: '做成了',
    title: '在自己的笔记本上装出 Linux 开发环境',
    body: '学长说第一学期先打 C++ 和 Linux 的基础，我就从零把 WSL2 + Ubuntu 24.04 装起来：限制了 8GB 内存防止吃干宿主、apt 换清华源、装好 g++ / CMake / gdb / git，并在里面编译运行了第一个 hello.cpp。这一步的意义是：我知道编译、链接、调试这套东西在自己机器上是什么样了。',
  },
  {
    when: '2026 年 9–10 月 · 工具',
    tag: '在持续做',
    title: '把 AI 变成顺手的工作台，而不是聊天框',
    body: '我在这台电脑上配好了自己的 AI 编码链路（本地模型路由 + 官方 API 直连，编码工具由本地启动器注入增强），也把 AI 助手接上了技能系统：需要什么能力就去找、装、然后真的用起来。装错东西把依赖搞坏过一次，也自己修回来了。',
  },
  {
    when: '2026 年 10 月 · 这个站',
    tag: '就是它',
    title: '用 AI 做出了你现在看的这个网站',
    body: '这次不是静态页：前端在浏览器里实时渲染我训练/导出的 3DGS 场景（Three.js + Spark），后端是真接口（FastAPI + SQLModel + SQLite），访问统计与留言都写进数据库。中间踩的坑写在下面第 05 节。',
  },
  {
    when: '2026 年 10 月 · 这个站',
    tag: '做成了',
    title: '给这个站配上自己的域名，让它在校园网之外也能打开',
    body: '原本放在 GitHub Pages，但国内网络下不稳：同一台电脑能开，换手机流量就白屏。于是自己去腾讯云买了域名，用 EdgeOne 的「全球可用区（不含中国大陆）」部署——这个加速区域不需要备案。域名归属验证、DNS 记录、HTTPS 证书一路配通，过程中也踩了坑：站点上线后一片白屏，排查到是构建时资源路径带上了仓库子路径，改成根路径才对。现在电脑和手机流量都能正常打开。',
  },
]

const TRIES_OK = [
  '把 53 人班级名单提取成结构化表格，之后每次统计都省几十分钟。',
  '用脚本给考勤表加了两天共 10 列，样式和合并单元格都保住了。',
  'WSL2 里编译并运行 C++ 成功，会用 CMake 组织多文件项目。',
  '给 AI 助手装了 5 个技能并真的用起来：3D 高斯泼溅方法对比、3DGS 论文阅读、UI 设计体系、官方 FastAPI 最佳实践、Playwright 端到端测试。',
  '把这个网站从零做出来：3DGS 查看器 + 场景库 + 访问统计 + 留言板，全部有自动化测试与真实运行证据。',
]

const TRIES_FAIL = [
  '装 WSL 时商店下载卡在几百 MB 不动，才去查「Delivery Optimization 下载队列」，最后换镜像 + 换路径才通。',
  '装一个 Python 包把语音依赖里的 onnxruntime 顶坏了，和 AI 助手一起把它降回可用版本才修好。',
  '第一次抓 GitHub 数据用的是匿名接口——每小时只有 60 次额度，跑到一半就 403。后来换成用本机已授权的令牌，并把结果落成文件存起来。',
  '这台机器上 GitHub 直连只有几百 KB/s，大文件得走镜像分片下；Spark 官方示例资源更是直连速度为 0，必须走代理。这直接改变了我的资源选择。',
]

const AI_STEPS: { lead: string; body: string }[] = [
  {
    lead: '先定结构，再让 AI 写。',
    body: '我先想清楚页面要回答评审的四个问题（你是谁 / 你折腾过什么 / 你为什么选这个方向 / 你怎么用 AI），把每节内容先写成中文要点，再让 AI 做版式与实现。反过来会得到一堆漂亮但没有信息的页面。',
  },
  {
    lead: '不让 AI 编数据。',
    body: '页面上的星标不是它写的，是脚本抓的；3DGS 的点数、加载耗时、帧率也是运行实测出来的（后端 /api/scenes 与浏览器里的实时帧率）。',
  },
  {
    lead: 'AI 的第一版被我退回两次。',
    body: '项目雷达第一次打算用网页爬虫抓 GitHub，我改成用官方 API；第二次它没处理接口限额，我要求改用本机已授权令牌并把结果缓存下来。',
  },
  {
    lead: '发现 AI 的筛选逻辑不严，我自己补规则。',
    body: '抓回 138 个仓库里混着人脸识别、扫地机器人这类高星但不相关的项目——我把「相关性关键词 + 人工否决清单」加进脚本，重抓到 116 个，每个都得说得出为什么属于三维视觉。',
  },
  {
    lead: '不接受「跑起来了就算完成」。',
    body: '这次做网站，我要求每一步都留下证据：后端 28 项 pytest、真实 HTTP 状态码、以及「截图里必须真的出现渲染出来的点云」这种像素级检查——空画布不许算通过。',
  },
  {
    lead: '视觉上我有自己的判断。',
    body: '不想要「渐变背景 + 三张等宽卡片」的模板页：所以深色底 + 等宽数字 + 明确的指标面板，让「数字是真的」一眼看得出来。',
  },
]

export default function AboutPage() {
  useEffect(() => {
    trackEvent('view', '/about')
  }, [])

  return (
    <section className="about">
      <header className="hero">
        <p className="kicker">关于我 · 郑州大学 · 软件工程 2026 级</p>
        <h1>肖宇航</h1>
        <p className="lede">
          方向选 <b>3D（三维视觉 / 三维重建）</b>；11v11 定为大二目标。
          学长给的第一学期任务是「打基础（C++ / Linux）+ 过考核」，这个网站在做后半件。
        </p>
        <p className="lede">
          联系方式：<a href="mailto:18711505157@163.com">18711505157@163.com</a>
        </p>
      </header>

      <h2 className="section-title">01 / 方向：为什么是 3D</h2>
      <div className="two-col">
        <ul className="clean">
          <li>
            <b>3D 解决的是机器人低级但致命的问题：</b>我在哪（位姿/里程计）、周围是什么形状（深度/重建）、
            目标在哪个位置和姿态（6D 位姿）。这些答错了，后面多聪明的决策都是空转。
          </li>
          <li>
            <b>它天然是「软件 + 数学」的方向。</b>相机是传感器里最便宜的，剩下的活全在算法里——
            重投影误差、光束法平差、可微渲染，本质是优化问题。我是软件工程专业，这些我能一行行写下来、跑起来、看结果对不对。
          </li>
          <li>
            <b>门槛低、反馈快。</b>一个 8GB 显存的笔记本就能跑小场景的 COLMAP、3DGS、NeRF——
            先把一个小物体重建出来，看到点云在屏幕上转，比在仿真里等一个月更有正反馈。
          </li>
          <li>
            <b>它正好是 11v11 的地基。</b>多机协同要求每台机器人先知道自己在场地哪个位置、球在哪，
            这两件事都是三维视觉在做。所以我把 11v11 写成大二目标，而不是现在硬上。
          </li>
          <li>
            <b>这条线的历史很清晰，好自学。</b>传统几何（SfM/MVS/SLAM）→ 神经渲染（NeRF、3D 高斯泼溅）
            → 视觉几何大模型（DUSt3R、VGGT）。三代方法都开源，都能找到原始代码。
          </li>
        </ul>
        <aside className="def">
          <h3>我理解的「3D 方向 = 做 CV」</h3>
          <dl>
            <dt>输入</dt>
            <dd>单目 / 双目 / RGB-D 图像、深度相机、激光雷达的原始数据。</dd>
            <dt>中间</dt>
            <dd>特征与匹配 → 相机位姿 → 深度与点云 → 网格与表面 → 语义。</dd>
            <dt>输出</dt>
            <dd>一张能拿来用地形、走路的「地图」，和物体相对于机器人的位置与姿态。</dd>
            <dt>与人形的关系</dt>
            <dd>人形机器人抖动大、视点变化剧烈，视觉既要做状态估计的输入，也要做决策的输入。</dd>
            <dt>我现在会什么</dt>
            <dd>Python 能写、C++ 刚起步（WSL2 + Ubuntu 已就绪）、线代在学。坦诚说：还不会任何 3D 视觉算法，但知道第一站该去哪。</dd>
          </dl>
        </aside>
      </div>

      <h2 className="section-title">02 / 真实的你：从入学到现在我主动折腾的事</h2>
      <p className="note">没有比赛奖项，也没有完整的大项目。下面每一条都能被追问：为什么做、卡在哪、最后跑没跑起来。</p>
      <div className="rows">
        {DID.map((row) => (
          <div className="row" key={row.title}>
            <div className="when">{row.when}</div>
            <div>
              <h3>
                {row.title}
                <span className="tagline">{row.tag}</span>
              </h3>
              <p>{row.body}</p>
            </div>
          </div>
        ))}
      </div>

      <h2 className="section-title">03 / 小尝试，包括失败的那几条</h2>
      <div className="two-col">
        <div className="card">
          <h3>做成的小事</h3>
          <ul>
            {TRIES_OK.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>踩过的坑 ⚠</h3>
          <ul>
            {TRIES_FAIL.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      </div>

      <h2 className="section-title">04 / 三维视觉开源项目雷达</h2>
      <p className="note">
        脚本从 GitHub 官方接口按 topic 与关键词抓取三维视觉相关仓库，按星标与「星速」（星标 ÷ 月龄）排序；
        带「我读过」标记的是我逐个看过、写了中文笔记并给出安装命令的。数据是抓的，不是编的。
        （下面是 6 个示例，全部项目在「开源项目」页可搜索、按分类筛选。）
      </p>
      <ProjectsPreview />

      <h2 className="section-title">05 / 过程：我是怎么用 AI 把想法做成能跑的东西的</h2>
      <ul className="clean">
        {AI_STEPS.map((step) => (
          <li key={step.lead}>
            <b>{step.lead}</b>
            {step.body}
          </li>
        ))}
      </ul>

      <h2 className="section-title">06 / 下一步：进来之前我会先做到的</h2>
      <div className="two-col">
        <div className="card">
          <h3>12 周内</h3>
          <ul>
            <li>把 C++ 过完指针 / 内存 / 面向对象 / STL 四段，每天一题保持手感。</li>
            <li>Linux 只在 WSL 里练：每天用命令行干一件真事（处理名单、统计考勤）。</li>
            <li>在 Ubuntu 里从零 clone 一个开源 C++ 项目，编译、跑起来、用 gdb 打断点。</li>
          </ul>
        </div>
        <div className="card">
          <h3>3D 这条线</h3>
          <ul>
            <li>跑通一条最小重建链路：自己拍一组照片 → COLMAP 出点云 → Open3D 看结果。</li>
            <li>装 nerfstudio，用同一组照片训一次 3DGS，比较它和传统重建的差别。</li>
            <li>把每一步的失败与结论写进自己的笔记，而不是只留在聊天记录里。</li>
          </ul>
        </div>
      </div>
      <p className="note">
        如果组里允许，我最想做的是跟着做「机器人视觉感知」里最脏最基础的那部分活：标定、数据整理、日志与可视化工具。
        我知道新人多半从这些开始，也愿意从这些开始——它们恰恰是「机器人的眼睛」最不能出错的地方。
      </p>
    </section>
  )
}
