import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import AboutPage from './pages/AboutPage.tsx'
import GuestbookPage from './pages/GuestbookPage.tsx'
import MethodsPage from './pages/MethodsPage.tsx'
import NotFoundPage from './pages/NotFoundPage.tsx'
import HomePage from './pages/HomePage.tsx'
import LibraryPage from './pages/LibraryPage.tsx'
import ViewerPage from './pages/ViewerPage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* basename 必须跟着 vite 的 base 走：子路径部署（GitHub Pages 的 /<repo>/）时，
        没有它所有路由都匹配不上 —— 表现是「无报错但页面全空白」，很难查。 */}
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomePage />} />
          <Route path="scenes" element={<LibraryPage />} />
          <Route path="scenes/:slug" element={<ViewerPage />} />
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
