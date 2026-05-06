import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config runs in Node.js (not the browser).
// loadEnv reads .env.local so we can inject the server URL at dev time.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const serverUrl = env.VITE_SERVER_URL || 'http://localhost:8000'

  return {
    plugins: [react()],

    server: {
      port: 5173,
      // Proxy rewrites /api/* → serverUrl/*
      // This means the browser never makes a cross-origin request —
      // everything goes to localhost:5173, and Vite forwards it to the server.
      proxy: {
        '/api': {
          target: serverUrl,
          changeOrigin: true,
          rewrite: path => path.replace(/^\/api/, ''),
        },
      },
    },

    build: {
      outDir: 'dist',
    },
  }
})
