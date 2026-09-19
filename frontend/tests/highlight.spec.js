import { describe, it, expect } from 'vitest'
import { hljs, hljsLanguage } from '@/plugins/highlight'

// 채점기가 쓰는 언어 이름(backend/judge/languages.py)과 블록 코딩.
const JUDGE_LANGUAGES = ['C', 'C++', 'Java', 'Python3', 'Golang', 'JavaScript', 'Block Coding']

describe('코드 하이라이트', () => {
  it('채점하는 언어를 모두 색칠할 수 있다', () => {
    // 이름을 안 바꿔주거나 언어를 등록하지 않으면 hljs 가 조용히 넘긴다.
    // 제출 코드 보기에서 색이 빠진 채로 나온다.
    for (const name of JUDGE_LANGUAGES) {
      expect(hljs.getLanguage(hljsLanguage(name)), name).toBeTruthy()
    }
  })

  it('블록으로 짠 코드는 파이썬으로 본다', () => {
    expect(hljsLanguage('Block Coding')).toBe(hljsLanguage('Python3'))
  })

  it('모르는 언어는 빈 이름을 준다', () => {
    // 빈 이름이면 hljs 가 스스로 추측한다. 콘솔에 경고를 찍지 않는다.
    expect(hljsLanguage('Pascal')).toBe('')
  })
})
