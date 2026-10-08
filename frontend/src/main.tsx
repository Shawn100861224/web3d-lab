import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import './narrow.css' // 窄屏（≤640px）排版修正，必须排在 index.css 之后才覆盖得上
import App from './App.tsx'
import AboutPage from './pages/AboutPage.tsx'
import GuestbookPage from './pages/GuestbookPage.tsx'
import MethodsPage from './pages/MethodsPage.tsx'
import NotFoundPage from './pages/NotFoundPage.tsx'
import HomePage from './pages/HomePage.tsx'
import LibraryPage from './pages/LibraryPage.tsx'
import ProjectDetailPage from './pages/ProjectDetailPage.tsx'
import ProjectsPage from './pages/ProjectsPage.tsx'

// 查看器是唯一用到 Three.js + @sparkjsdev/spark 的页面，这两样占了打包体积的大头
// （此前整个站打成一个 3.4MB 的 JS，构建时 vite 一直在警告单包过大）。
// 改成按需加载后，首页 / 场景库 / 关于我等页面**完全不下载**这部分 —— 手机流量下首屏明显更快。
const ViewerPage = lazy(() => import('./pages/ViewerPage.tsx'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* basename 必须跟着 vite 的 base 走：子路径部署（GitHub Pages 的 /<repo>/）时，
        没有它所有路由都匹配不上 —— 表现是「无报错但页面全空白」，很难查。 */}
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomePage />} />
          <Route path="scenes" element={<LibraryPage />} />
          {/* 查看器按需加载：首屏（首页/场景库）不必下载 Three.js + Spark */}
          <Route
            path="scenes/:slug"
            element={
              <Suspense fallback={<p style={{ padding: '28px', color: 'var(--muted)' }}>正在加载查看器…</p>}>
                <ViewerPage />
              </Suspense>
            }
          />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:owner/:name" element={<ProjectDetailPage />} />
          <Route path="guestbook" element={<GuestbookPage />} />
          <Route path="methods" element={<MethodsPage />} />
          <Route path="about" element={<AboutPage />} />
          {/* 通配路由放最后：EdgeOne Pages 的 SPA 404 由它兜住 */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
