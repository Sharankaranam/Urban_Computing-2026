import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Builds straight into the FastAPI static folder, which serves index.html at "/"
// and everything else under "/static".
export default defineConfig({
  base: '/static/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: {
    outDir: path.resolve(__dirname, '../src/fuzzy_tariff/api/static'),
    emptyOutDir: true,
    chunkSizeWarningLimit: 1600,
  },
  server: {
    proxy: { '/v1': 'http://127.0.0.1:8000', '/docs': 'http://127.0.0.1:8000', '/openapi.json': 'http://127.0.0.1:8000' },
  },
})
