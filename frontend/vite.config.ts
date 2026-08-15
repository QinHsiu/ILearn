import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Override with ILEARN_API_TARGET when the API runs on a non-default port.
const apiTarget = process.env.ILEARN_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/sessions': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/docs': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/redoc': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
