import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // During dev: proxy all API calls to FastAPI
      '/healthz':              { target: 'http://localhost:8000', changeOrigin: true },
      '/dashboard':            { target: 'http://localhost:8000', changeOrigin: true },
      '/eval':                 { target: 'http://localhost:8000', changeOrigin: true },
      '/audit':                { target: 'http://localhost:8000', changeOrigin: true },
      '/projects':             { target: 'http://localhost:8000', changeOrigin: true },
      '/milestones':           { target: 'http://localhost:8000', changeOrigin: true },
      '/cases':                { target: 'http://localhost:8000', changeOrigin: true },
      '/approvals':            { target: 'http://localhost:8000', changeOrigin: true },
      '/submission-approvals': { target: 'http://localhost:8000', changeOrigin: true },
      '/reconciliation':       { target: 'http://localhost:8000', changeOrigin: true },
      '/outbox':               { target: 'http://localhost:8000', changeOrigin: true },
      '/reputation':           { target: 'http://localhost:8000', changeOrigin: true },
      '/demo':                 { target: 'http://localhost:8000', changeOrigin: true },
      '/fixtures':             { target: 'http://localhost:8000', changeOrigin: true },
      '/webhooks':             { target: 'http://localhost:8000', changeOrigin: true },
      '/sim':                  { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
