import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/store/user'

// 스토어는 @oj/api 를 동적으로 import 한다. 실제 요청 대신 가짜를 물린다.
const getUserInfo = vi.fn()
vi.mock('@oj/api', () => ({
  default: {
    getUserInfo: (...args) => getUserInfo(...args)
  }
}))

function profileResponse (user) {
  return { data: { data: user ? { user } : null } }
}

describe('user 스토어', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // ensureProfile 의 단일 요청 캐시는 모듈 수준 변수라 pinia 를 새로 만들어도
    // 남는다. 브라우저에서는 페이지가 살아 있는 동안 유지되는 게 맞는 동작이라,
    // 테스트에서만 clearProfile 로 초기화한다.
    useUserStore().clearProfile()
    getUserInfo.mockReset()
    window.localStorage.clear()
  })

  it('프로필을 받으면 로그인 상태가 된다', async () => {
    getUserInfo.mockResolvedValue(profileResponse({ id: 1, username: '홍길동', admin_type: 'Regular User' }))
    const store = useUserStore()

    expect(store.isAuthenticated).toBe(false)
    await store.getProfile()

    expect(store.isAuthenticated).toBe(true)
    expect(store.user.username).toBe('홍길동')
    expect(store.profileReady).toBe(true)
  })

  it('ensureProfile 을 여러 번 불러도 요청은 한 번만 나간다', async () => {
    // 목록 화면들이 각자 ensureProfile 을 부르는데, 그때마다 /api/profile 이
    // 나가면 안 된다. 이 단일 요청 보장이 깨지면 화면은 멀쩡하고 요청만 늘어난다.
    getUserInfo.mockResolvedValue(profileResponse({ id: 1, username: '홍길동' }))
    const store = useUserStore()

    await Promise.all([store.ensureProfile(), store.ensureProfile(), store.ensureProfile()])

    expect(getUserInfo).toHaveBeenCalledTimes(1)
  })

  it('비로그인이면 profileReady 만 서고 로그인 상태는 아니다', async () => {
    getUserInfo.mockResolvedValue(profileResponse(null))
    const store = useUserStore()

    await store.ensureProfile()

    expect(store.profileReady).toBe(true)
    expect(store.isAuthenticated).toBe(false)
  })

  it('요청이 실패해도 profileReady 를 세워 화면이 멈추지 않게 한다', async () => {
    // 목록 화면은 profileReady 를 기다렸다 데이터를 부른다.
    // 여기서 안 서면 네트워크 오류 시 목록이 영영 비어 있게 된다.
    getUserInfo.mockRejectedValue(new Error('network'))
    const store = useUserStore()

    await store.ensureProfile()

    expect(store.profileReady).toBe(true)
    expect(store.isAuthenticated).toBe(false)
  })

  it('로그아웃하면 프로필이 비고 다음 ensureProfile 은 다시 요청한다', async () => {
    getUserInfo.mockResolvedValue(profileResponse({ id: 1, username: '홍길동' }))
    const store = useUserStore()
    await store.ensureProfile()
    expect(getUserInfo).toHaveBeenCalledTimes(1)

    store.clearProfile()
    expect(store.isAuthenticated).toBe(false)

    await store.ensureProfile()
    expect(getUserInfo).toHaveBeenCalledTimes(2)
  })

  it('역할 판별이 admin_type 을 따른다', async () => {
    getUserInfo.mockResolvedValue(profileResponse({ id: 2, username: '김선생', admin_type: 'Teacher' }))
    const store = useUserStore()
    await store.getProfile()

    expect(store.isTeacher).toBe(true)
    expect(store.isAdminRole).toBe(false)
    expect(store.isSuperAdmin).toBe(false)
  })
})
