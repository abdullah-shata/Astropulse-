
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    host: '127.0.0.1',
    port: Number(process.env.ASTROPULSE_FRONTEND_PORT || 5180),
    strictPort: true,

    proxy: {
      '/api': `http://127.0.0.1:${process.env.ASTROPULSE_BACKEND_PORT || '8180'}`,

      '/ws': {
        target: `ws://127.0.0.1:${process.env.ASTROPULSE_BACKEND_PORT || '8180'}`,
        ws: true,
      },
    },
  },
});
