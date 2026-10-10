import { NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { fetchScenes } from './lib/api'
import { useBackend } from './lib/useBackend'

/** 公开联系方式（本人确认公开的邮箱） */
const CONTACT_EMAIL = '18711505157@163.com'

/**
 * 站点外壳：顶栏导航 + 内容区 + 页脚。各页面只负责自己的内容
 * （场景库、查看器、个人主页在 pages/ 下）。
 */
export default function App() {
  const mode = useBackend(true)
  // 页头那条技术栏里的场景数**必须来自接口**：曾经硬编码写死成 5，
  // 而实际已发布 7 个 —— 站点上的数字要么实时取、要么不写。
  const [sceneCount, setSceneCount] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    fetchScenes({ limit: 200 })
      .then((r) => {
        if (alive) setSceneCount(r.total)
      })
      .catch(() => {
        if (alive) setSceneCount(null)
      })
    return () => {
      alive = false
    }
  }, [])

  /**
   * 全局交互增强（v2 皮肤用，纯渐进增强，关掉 JS 内容照样完整可见）：
   *  1) Card Spotlight —— 鼠标跟随聚光。**只有一个委托监听器**，且只在
   *     「悬停的元素变了」时才读一次 getBoundingClientRect（避免每次 mousemove
   *     都强制布局，这是这类效果最常见的性能坑）；只写两个 CSS 变量，不触发重排。
   *  2) 顶部导航滚动态 —— 滚动超过 8px 时出现 1px 分隔线。
   *  3) 用户开了 prefers-reduced-motion 就整个跳过（不注册任何监听）。
   */
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return

    const SPOT = '.card-scene, .feature, .stats-card, .tile-spot, .panel-block'
    let current: HTMLElement | null = null
    let rect: DOMRect | null = null

    const onMove = (e: MouseEvent) => {
      const el = (e.target as HTMLElement | null)?.closest?.(SPOT) as HTMLElement | null
      if (el !== current) {
        current = el
        rect = el ? el.getBoundingClientRect() : null
      }
      if (!el || !rect) return
      el.style.setProperty('--mx', `${e.clientX - rect.left}px`)
      el.style.setProperty('--my', `${e.clientY - rect.top}px`)
    }

    const nav = document.querySelector('.nav')
    const onScroll = () => nav?.classList.toggle('scrolled', window.scrollY > 8)
    onScroll()

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('scroll', onScroll)
    }
  }, [])


  return (
    <div className="shell">
      {/* 键盘用户 Tab 第一下即可跳到正文，不必逐个走过 6 个导航链接 */}
      <a className="skip-link" href="#main">
        跳到主内容
      </a>
      <header className="nav">
        <NavLink to="/" className="brand">
          <span className="brand-mark">◈</span>
          <span>
            web3d-lab
            <em>3DGS 在线重建查看器</em>
          </span>
        </NavLink>
        <nav>
          {mode === 'offline' && (
            <span className="badge badge--warn" id="backend-mode" data-mode="offline" title="本部署为静态演示版：场景渲染全部可用，访问统计与留言需要后端服务">
              演示版
            </span>
          )}
          <NavLink to="/" end>
            首页
          </NavLink>
          <NavLink to="/scenes">场景库</NavLink>
          <NavLink to="/projects">开源项目</NavLink>
          <NavLink to="/methods">方法对比</NavLink>
          <NavLink to="/about">关于我</NavLink>
          <NavLink to="/guestbook">留言板</NavLink>
        </nav>
      </header>

      <div className="techstrip" aria-hidden="true">
        <span>WebGL2</span>
        <span>3DGS · Spark 2.3.1</span>
        <span>FastAPI + SQLModel</span>
        <span>
          后端测试 <b>39</b> 项通过
        </span>
        <span>
          场景 <b>{sceneCount ?? '—'}</b> 个
        </span>
      </div>

      <main className="content" id="main" tabIndex={-1}>
        <Outlet />
      </main>

      <footer className="foot">
        <span>
          郑州大学 · 双足实验室 3D 方向考核作品 · 联系方式：
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
        </span>
        <span>Three.js + @sparkjsdev/spark · FastAPI + SQLModel</span>
      </footer>
    </div>
  )
}
