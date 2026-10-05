import { NavLink, Outlet } from 'react-router-dom'

import { useBackend } from './lib/useBackend'

/**
 * 站点外壳：顶栏导航 + 内容区 + 页脚。各页面只负责自己的内容
 * （场景库、查看器、个人主页在 pages/ 下）。
 */
export default function App() {
  const mode = useBackend(true)

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
          <NavLink to="/methods">方法对比</NavLink>
          <NavLink to="/about">关于我</NavLink>
          <NavLink to="/guestbook">留言板</NavLink>
        </nav>
      </header>

      <main className="content">
        <Outlet />
      </main>

      <footer className="foot">
        <span>郑州大学 · 双足实验室 3D 方向考核作品</span>
        <span>
          Three.js + @sparkjsdev/spark · FastAPI + SQLModel
        </span>
      </footer>
    </div>
  )
}
