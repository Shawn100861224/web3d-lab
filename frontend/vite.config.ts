import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// dev server 把 /api 反代到后端，避免前端写死 baseURL 也绕过 CORS
// 静态托管在子路径时（GitHub Pages 是 /<repo>/）必须设 base，否则资源 404。
// 用法：VITE_BASE=/web3d-lab/ npm run build
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
