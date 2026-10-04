import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import HomePage from './pages/HomePage.tsx'
import LibraryPage from './pages/LibraryPage.tsx'
import ViewerPage from './pages/ViewerPage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<HomePage />} />
          <Route path="scenes" element={<LibraryPage />} />
          <Route path="scenes/:slug" element={<ViewerPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
