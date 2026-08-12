import { defineStore } from 'pinia'
import storage from '@/utils/storage'
import { STORAGE_KEY, USER_TYPE, PROBLEM_PERMISSION } from '@/utils/constants'

export const useUserStore = defineStore('user', {
  state: () => ({
    profile: {}
  }),
  getters: {
    user: (state) => state.profile.user || {},
    isAuthenticated () {
      return !!this.user.id
    },
    isAdminRole () {
      return this.user.admin_type === USER_TYPE.ADMIN ||
        this.user.admin_type === USER_TYPE.SUPER_ADMIN
    },
    isSuperAdmin () {
      return this.user.admin_type === USER_TYPE.SUPER_ADMIN
    },
    isTeacher () {
      return this.user.admin_type === USER_TYPE.TEACHER
    },
    hasProblemPermission () {
      return this.user.problem_permission !== PROBLEM_PERMISSION.NONE
    }
  },
  actions: {
    async getProfile () {
      const { default: api } = await import('@oj/api')
      const res = await api.getUserInfo()
      this.changeProfile(res.data.data || {})
    },
    changeProfile (profile) {
      this.profile = profile
      storage.set(STORAGE_KEY.AUTHED, !!profile.user)
    },
    clearProfile () {
      this.profile = {}
      storage.clear()
    }
  }
})
