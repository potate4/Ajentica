import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Forward /api/* to the FastAPI backend so the frontend can stay on
      // a single origin in dev (no CORS), matching the production layout.
      '/api': {
        // Use 127.0.0.1 (not localhost) so Node 22 doesn't resolve to ::1
        // when the backend only binds to IPv4.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
