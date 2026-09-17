import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  publicDir: false,
  build: {
    outDir: 'public/landing-assets/detached', emptyOutDir: false,
    lib: { entry: fileURLToPath(new URL('./src/landing/detached-viewer.ts', import.meta.url)), formats: ['es'], fileName: () => 'viewer.js' },
  },
})
