import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { cp } from 'node:fs/promises'
import path from 'path'

const proxyTarget = process.env.TARGET || 'http://localhost:8000'

// 수식(katex)은 번들에 넣지 않고 파일로 내보낸다. 넣으면 JS 와 폰트 수십 개를
// 모든 방문자가 첫 화면에서 받는데, 수식을 쓰는 글에서만 필요하다.
// 주소는 plugins/markdown.js 의 editorExtensions.katex 가 가리킨다.
// 폰트는 katex.min.css 가 fonts/ 상대 경로로 부르므로 함께 복사해야 한다.
function copyKatex () {
  return {
    name: 'copy-katex',
    apply: 'build',
    async closeBundle () {
      const from = path.resolve(__dirname, 'node_modules/katex/dist')
      const to = path.resolve(__dirname, 'dist/katex')
      for (const name of ['katex.min.js', 'katex.min.css', 'fonts']) {
        await cp(path.join(from, name), path.join(to, name), { recursive: true })
      }
    }
  }
}

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
    },
    copyKatex()
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
  },
  test: {
    // localStorage 를 쓰는 코드(utils/storage.js)가 있어 DOM 환경이 필요하다
    environment: 'happy-dom',
    include: ['tests/**/*.spec.js'],
    setupFiles: ['tests/setup.js']
  }
})
