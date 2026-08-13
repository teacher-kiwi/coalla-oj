import { defineStore } from 'pinia'
import storage from '@/utils/storage'
import { STORAGE_KEY, USER_TYPE, PROBLEM_PERMISSION } from '@/utils/constants'

// 첫 프로필 조회는 앱 전체에서 한 번만 나가면 된다. 화면마다 부르면 같은 요청이 겹친다.
let profileRequest = null

export const useUserStore = defineStore('user', {
  state: () => ({
    profile: {},
    // 프로필 조회가 끝났는지(= 로그인 여부가 확정됐는지). 목록 화면은 이게 true 가
    // 된 뒤에 데이터를 부른다. 확정 전에 부르면 프로필이 도착하는 순간 다시 부르게 되어
    // 같은 요청이 두 번 나간다.
    profileReady: false
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
      try {
        const res = await api.getUserInfo()
        this.changeProfile(res.data.data || {})
      } finally {
        // 실패해도 "확정됐다"고 본다. 화면이 영영 비어 있는 것보다 낫다.
        this.profileReady = true
      }
    },
    // 여러 화면이 동시에 불러도 요청은 한 번만 나간다.
    // 실패는 여기서 삼킨다(profileReady 는 이미 세워졌고, 화면마다 잡을 필요가 없다).
    ensureProfile () {
      if (!profileRequest) profileRequest = this.getProfile().catch(() => {})
      return profileRequest
    },
    changeProfile (profile) {
      this.profile = profile
      storage.set(STORAGE_KEY.AUTHED, !!profile.user)
    },
    clearProfile () {
      profileRequest = null
      this.profile = {}
      storage.clear()
    }
  }
})
