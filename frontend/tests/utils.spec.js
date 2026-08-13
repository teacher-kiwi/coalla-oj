import { describe, it, expect } from 'vitest'
import utils from '@/utils/utils'
import time from '@/utils/time'
import { buildProblemCodeKey, JUDGE_STATUS, DIFFICULTY_LABEL } from '@/utils/constants'

describe('정답률 표시', () => {
  it('제출이 없어도 0으로 나누지 않는다', () => {
    // 0 분기만 숫자 0 을 그대로 문자열로 만들어서 소수점이 붙지 않는다.
    // 다른 값은 toFixed(2) 를 거쳐 "33.33%" 형태라 표기가 어긋나지만,
    // 지금 화면에서 문제되지 않아 현재 동작을 그대로 고정해둔다.
    expect(utils.getACRate(0, 0)).toBe('0%')
  })

  it('소수점 두 자리로 반올림한다', () => {
    expect(utils.getACRate(1, 3)).toBe('33.33%')
    expect(utils.getACRate(1, 2)).toBe('50.00%')
    expect(utils.getACRate(7, 7)).toBe('100.00%')
  })
})

describe('제출 시간·메모리 표시', () => {
  it('값이 없으면 -- 로 보여준다', () => {
    // 채점 중인 제출은 statistic_info 가 비어 있다
    expect(utils.submissionTimeFormat(undefined)).toBe('--')
    expect(utils.submissionMemoryFormat(undefined)).toBe('--')
  })

  it('시간은 ms, 메모리는 MB 로 붙인다', () => {
    expect(utils.submissionTimeFormat(12)).toBe('12ms')
    expect(utils.submissionMemoryFormat(1048576)).toBe('1MB')
    expect(utils.submissionMemoryFormat(1572864)).toBe('2MB')
  })
})

describe('filterEmptyValue', () => {
  it('빈 문자열·null·undefined 는 뺀다', () => {
    expect(utils.filterEmptyValue({ a: '', b: null, c: undefined, d: 'x' })).toEqual({ d: 'x' })
  })

  it('0 과 false 는 값이므로 남긴다', () => {
    // 라우터 쿼리에서 page=0 이나 myself=false 가 사라지면 안 된다
    expect(utils.filterEmptyValue({ page: 0, myself: false })).toEqual({ page: 0, myself: false })
  })
})

describe('breakLongWords', () => {
  it('긴 영문은 지정한 길이마다 줄바꿈을 넣는다', () => {
    expect(utils.breakLongWords('abcdefghij', 5)).toBe('abcde\nfghij\n')
  })

  it('한글이 섞이면 더 짧은 간격으로 끊는다', () => {
    // 한글은 폭이 넓어 절반 기준으로 끊는다
    expect(utils.breakLongWords('가나다라마바', 4)).toBe('가나다\n라마바\n')
  })
})

describe('문제 코드 저장 키', () => {
  it('대회 문제와 일반 문제를 다른 키로 저장한다', () => {
    expect(buildProblemCodeKey('1000')).toBe('problemCode_NaN_1000')
    expect(buildProblemCodeKey('1000', 7)).toBe('problemCode_7_1000')
  })
})

describe('시간 변환', () => {
  it('UTC 문자열을 지정한 형식으로 바꾼다', () => {
    expect(time.utcToLocal('2026-08-13T00:00:00Z', 'YYYY-MM-DD')).toBe('2026-08-13')
  })

  it('초를 시:분:초로 바꾼다', () => {
    expect(time.secondFormat(3661)).toBe('1:1:1')
  })
})

describe('상수 표', () => {
  it('채점 결과 코드에 라벨이 모두 있다', () => {
    // 목록 화면이 JUDGE_STATUS[result].label 을 그대로 쓰므로 빠지면 화면이 깨진다
    for (const code of ['-2', '-1', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) {
      expect(JUDGE_STATUS[code], `결과 코드 ${code}`).toBeDefined()
      expect(JUDGE_STATUS[code].label).toBeTruthy()
    }
  })

  it('난이도 라벨이 세 단계 모두 있다', () => {
    expect(DIFFICULTY_LABEL.Low).toBeTruthy()
    expect(DIFFICULTY_LABEL.Mid).toBeTruthy()
    expect(DIFFICULTY_LABEL.High).toBeTruthy()
  })
})
