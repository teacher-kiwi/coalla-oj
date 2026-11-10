import { describe, it, expect, vi } from 'vitest'
import { lookOf, setLook } from '@/utils/looks'
import { CODE } from '@/utils/character'

// 서버 대신 가짜 응답. 아이디 a 만 모자를 쓰고 있다.
const get = vi.fn()
vi.mock('axios', () => ({ default: { get: (...args) => get(...args) } }))

const head = CODE[3] + '.'.repeat(40 * 36 - 1)
const hat = { id: 7, slot: 'hat', variant: 'top', parts: { head }, last_update_time: 't1' }

describe('looks: 여러 사람의 모습 모아 묻기', () => {
  it('같은 순간의 아이디를 한 번에 묻고, 받은 뒤 아이템으로 바꿔 준다', async () => {
    get.mockResolvedValue({ data: { error: null, data: { looks: { a: { hat: 7 } }, items: { 7: hat } } } })
    expect(lookOf('a')).toEqual({})
    expect(lookOf('b')).toEqual({})
    expect(lookOf('a')).toEqual({})
    await new Promise(resolve => setTimeout(resolve, 5))
    expect(get).toHaveBeenCalledTimes(1)
    expect(get.mock.calls[0][1].params.usernames).toBe('a,b')
    const eq = lookOf('a')
    expect(eq.hat.id).toBe(7)
    expect(eq.hat.cover).toBe('top')
    expect(eq.hat.parts.head[0]).toBe(3)
    expect(lookOf('b')).toEqual({})
    // 이미 물은 아이디는 다시 묻지 않는다
    await new Promise(resolve => setTimeout(resolve, 5))
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('내 모습을 바꾸면 바로 반영된다', () => {
    setLook('me', { hat: 7 }, [hat])
    expect(lookOf('me').hat.id).toBe(7)
    setLook('me', {})
    expect(lookOf('me')).toEqual({})
    expect(get).toHaveBeenCalledTimes(1)
  })
})
