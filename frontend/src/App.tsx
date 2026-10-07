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


  return (
    <div className="shell">
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

      <main className="content">
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
