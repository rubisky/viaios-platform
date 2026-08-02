import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/actuator': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      external: ['cesium'],  // Optional: Cesium 3D globe — loaded at runtime
      output: {
        manualChunks: {
          // Framework core (~150KB) — cached across all pages
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // UI library (~1MB+) — cached across all pages
          'vendor-antd': ['antd', '@ant-design/icons'],
          // Charts (~1MB) — only Dashboard/Analytics pages load this
          'vendor-echarts': ['echarts', 'echarts-for-react'],
          // Maps (~200KB) — only CameraDetail/Trajectory pages load
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
          // Flow graph (~500KB) — only Workflow/Graph pages load
          'vendor-flow': ['reactflow'],
          // Video streaming (~200KB) — only CameraDetail page loads
          'vendor-hls': ['hls.js'],
        },
      },
    },
  },
});
