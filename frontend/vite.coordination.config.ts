import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// The public landing document also runs independently of the React application.
export default defineConfig({
  publicDir: false,
  build: {
    outDir: 'public/landing-assets/coordination',
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL('./src/landing/coordination.ts', import.meta.url)),
      formats: ['es'],
      fileName: () => 'viewer.js',
    },
  },
})
