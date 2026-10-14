import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import './skin.css' // v2 视觉皮肤（方案 A：碳黑+镭射青）—— 排在 index.css 之后、narrow.css 之前：
// 桌面规则能覆盖旧样式，而 ≤640px 的窄屏修正仍压在最上层；整体回滚只需删掉这一行
import './narrow.css' // 窄屏（≤640px）排版修正，必须排在 index.css 之后才覆盖得上
import App from './App.tsx'
import HomePage from './pages/HomePage.tsx'

// 查看器是唯一用到 Three.js + @sparkjsdev/spark 的页面，这两样占了打包体积的大头
// （此前整个站打成一个 3.4MB 的 JS，构建时 vite 一直在警告单包过大）。
// 改成按需加载后，首页 / 场景库 / 关于我等页面**完全不下载**这部分 —— 手机流量下首屏明显更快。
const ViewerPage = lazy(() => import('./pages/ViewerPage.tsx'))

// T4（2026-10-14 实测：主包 107 KB 里装了全部页面）：其余页面同样按需加载，
// 首屏只留 App（外壳）+ HomePage；兜底 Suspense 放在 App.tsx 的内容区，页头/页脚不会跟着闪。
const LibraryPage = lazy(() => import('./pages/LibraryPage.tsx'))
const ProjectsPage = lazy(() => import('./pages/ProjectsPage.tsx'))
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage.tsx'))
const GuestbookPage = lazy(() => import('./pages/GuestbookPage.tsx'))
const MethodsPage = lazy(() => import('./pages/MethodsPage.tsx'))
const AboutPage = lazy(() => import('./pages/AboutPage.tsx'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.tsx'))

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
