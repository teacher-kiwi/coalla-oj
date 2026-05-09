import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import routes from './routes'
import storage from '@/utils/storage'
import { STORAGE_KEY } from '@/utils/constants'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior (to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { left: 0, top: 0 }
  },
  routes
})

router.beforeEach(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!storage.get(STORAGE_KEY.AUTHED)) {
      ElMessage.error('Please login first')
      const { useAppStore } = await import('@/store/app')
      useAppStore().changeModalStatus({ mode: 'login', visible: true })
      next({ name: 'home' })
      return
    }
  }
  next()
})

export default router
