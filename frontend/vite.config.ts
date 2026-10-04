import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// dev server 把 /api 反代到后端，避免前端写死 baseURL 也绕过 CORS
export default defineConfig({
  plugins: [react()],
  server: {
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
