import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  root: path.resolve(__dirname),
  base: '/',
  publicDir: path.resolve(__dirname, './public'),
  server: {
    port: 3000,
    strictPort: true
  },
  preview: {
    port: 4173
  },
  build: {
    outDir: path.resolve(__dirname, './dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, './index.html')
      }
    }
  }
})
