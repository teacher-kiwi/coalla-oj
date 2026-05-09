import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const proxyTarget = process.env.TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'admin-rewrite',
      configureServer (server) {
        server.middlewares.use((req, res, next) => {
          if (req.url.startsWith('/admin')) {
            req.url = '/admin.html'
          }
          next()
        })
      }
    }
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@oj': path.resolve(__dirname, 'src/pages/oj'),
      '@admin': path.resolve(__dirname, 'src/pages/admin'),
      '~': path.resolve(__dirname, 'src/components')
    }
  },
  server: {
    port: 8080,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true
      },
      '/public': {
        target: proxyTarget,
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      input: {
        oj: path.resolve(__dirname, 'index.html'),
        admin: path.resolve(__dirname, 'admin.html')
      }
    }
  },
  css: {
    preprocessorOptions: {
      less: {
        javascriptEnabled: true
      }
    }
  }
})
