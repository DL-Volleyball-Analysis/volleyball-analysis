/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = process.env.VBALL_API ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The app calls /api/...; the backend serves the same paths without the prefix.
    proxy: { '/api': { target: API, rewrite: (path) => path.replace(/^\/api/, '') } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/test/setup.ts'],
    css: { include: [/theme\.css/] }, // contrast test reads the tokens
    // `npm run test:coverage` fails below these (2026-10-11: lines 88%, statements 87%, branches 81%, functions 86%)
    coverage: { include: ['src/**'], exclude: ['src/**/*.test.*', 'src/test/**', 'src/api/schema.d.ts', 'src/main.tsx'],
      thresholds: { lines: 85, statements: 85, branches: 75, functions: 80 } },
  },
})
