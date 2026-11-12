import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load .env.local or .env from project root
  const env = loadEnv(mode, process.cwd(), '');

  // Dev proxy target — override with VITE_API_BASE in .env.local if needed
  const apiTarget = env.VITE_API_BASE || 'http://localhost:8000';

  const apiProxy = {
    target: apiTarget,
    changeOrigin: true,
    bypass: (req) => {
      if (req.headers.accept && req.headers.accept.includes('text/html')) {
        return '/index.html';
      }
    },
  };

  return {
    plugins: [react()],

    // Expose API base URL to the app at build time
    define: {
      __API_BASE__: JSON.stringify(env.VITE_API_BASE || ''),
    },

    server: {
      port: 5173,
      proxy: {
        '/healthz':              apiProxy,
        '/dashboard':            apiProxy,
        '/eval':                 apiProxy,
        '/audit':                apiProxy,
        '/audit-log':            apiProxy,
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
        '/auth':                 apiProxy,
        '/invoices':             apiProxy,
        '/payment-attempts':     apiProxy,
        '/subscriptions':        apiProxy,
        '/ledger':               apiProxy,
        '/customers':            apiProxy,
        '/analytics':            apiProxy,
        '/disputes':             apiProxy,
        '/recovery':             apiProxy,
        '/merchant-sales':       apiProxy,
        '/webhook-events':       apiProxy,
        '/settings':             apiProxy,
        '/internal':             apiProxy,
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  };
});
