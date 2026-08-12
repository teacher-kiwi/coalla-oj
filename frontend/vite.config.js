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
      // changeOrigin 을 켜면 Host 헤더가 backend:8000 으로 바뀌는데,
      // 브라우저가 보낸 Origin(localhost:8080)과 달라져 Django 4 의 CSRF Origin
      // 검사에서 모든 POST 가 403 이 된다. Host 를 그대로 넘겨야 한다.
      '/api': {
        target: proxyTarget,
        changeOrigin: false
      },
      '/public': {
        target: proxyTarget,
        changeOrigin: false
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
