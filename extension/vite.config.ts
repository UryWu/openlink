import { defineConfig } from 'vite'
import { resolve } from 'path'
import { copyFileSync, mkdirSync, readdirSync, existsSync } from 'fs'

export default defineConfig({
  plugins: [
    {
      name: 'copy-public',
      closeBundle() {
        mkdirSync('dist', { recursive: true })
        // Copy all files from public/ to dist/
        const publicDir = resolve(__dirname, 'public')
        if (existsSync(publicDir)) {
          for (const file of readdirSync(publicDir)) {
            copyFileSync(resolve(publicDir, file), resolve('dist', file))
          }
        }
      },
    },
  ],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        content: resolve(__dirname, 'src/content/index.ts'),
        injected: resolve(__dirname, 'src/injected/index.ts'),
        background: resolve(__dirname, 'src/background/index.ts'),
      },
      output: {
        entryFileNames: '[name].js',
      },
    },
  },
})
