import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  base: '/app/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:39527',
      '/auth': 'http://127.0.0.1:39527',
      '/config': 'http://127.0.0.1:39527',
      '/tools': 'http://127.0.0.1:39527',
      '/exec': 'http://127.0.0.1:39527',
      '/prompt': 'http://127.0.0.1:39527',
      '/skills': 'http://127.0.0.1:39527',
      '/files': 'http://127.0.0.1:39527',
    },
  },
})
