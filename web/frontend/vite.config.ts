import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// @ts-ignore
import cesium from 'vite-plugin-cesium';
// @ts-ignore
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    cesium(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico'],
      manifest: {
        name: 'VIAIOS 智能视频侦查平台',
        short_name: 'VIAIOS',
        description: 'VIAIOS Enterprise 4.0 — Visual Intelligence AI Operating System',
        theme_color: '#0f0f23',
        background_color: '#0f0f23',
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: '/',
        icons: [
          { src: '/vite.svg', sizes: '192x192', type: 'image/svg+xml' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          { urlPattern: /^https:\/\/.*\.tile\.openstreetmap\.org\/.*/i,
            handler: 'CacheFirst', options: { cacheName: 'map-tiles', expiration: { maxEntries: 500, maxAgeSeconds: 86400 } } },
        ],
      },
    }),
  ],
  resolve: { alias: { '@': '/src' } },
  server: { port: 3000,
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true },
             '/actuator': { target: 'http://localhost:8080', changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd', '@ant-design/icons'],
          'vendor-echarts': ['echarts', 'echarts-for-react'],
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
          'vendor-flow': ['reactflow'],
          'vendor-hls': ['hls.js'],
        },
      },
    },
  },
});
