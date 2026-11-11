import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxy = {
  target: 'http://localhost:8000',
  changeOrigin: true,
  bypass: (req) => {
    // If request is from browser navigating to an HTML page, serve index.html
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
      return '/index.html';
    }
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // During dev: proxy all API calls to FastAPI
      '/healthz':              apiProxy,
      '/dashboard':            apiProxy,
      '/eval':                 apiProxy,
      '/audit':                apiProxy,
      '/projects':             apiProxy,
      '/milestones':           apiProxy,
      '/cases':                apiProxy,
      '/approvals':            apiProxy,
      '/submission-approvals': apiProxy,
      '/reconciliation':       apiProxy,
      '/outbox':               apiProxy,
      '/reputation':           apiProxy,
      '/demo':                 apiProxy,
      '/fixtures':             apiProxy,
      '/webhooks':             apiProxy,
      '/sim':                  apiProxy,
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
