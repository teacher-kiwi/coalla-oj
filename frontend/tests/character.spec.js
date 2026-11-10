import { describe, it, expect } from 'vitest'
import { composePixels, crop, toneOf, PAL, PART, SIZE, BUST, FRAMES,
  HAIR_TONES, SHIRT_TONES } from '@/utils/character'

const OUT = '#181425'

describe('캐릭터 그리기', () => {
  it('64×64 칸을 만들고 빈칸은 null 이다', () => {
    const px = composePixels()
    expect(px).toHaveLength(SIZE * SIZE)
    expect(px[0]).toBeNull()
    expect(px.filter(Boolean).length).toBeGreaterThan(500)
  })

  it('모든 동작이 그려진다', () => {
    FRAMES.forEach((_, frame) => {
      expect(composePixels({ frame }).filter(Boolean).length).toBeGreaterThan(500)
    })
  })

  it('맨몸에도 외곽선이 있다', () => {
    expect(composePixels()).toContain(OUT)
  })

  it('같은 아이디는 늘 같은 모습이다', () => {
    expect(composePixels({ seed: '학생12345678' })).toEqual(composePixels({ seed: '학생12345678' }))
    expect(toneOf('a')).toEqual(toneOf('a'))
  })

  it('아이디마다 머리색·옷색이 갈린다', () => {
    const tones = new Set()
    for (let i = 0; i < 200; i++) {
      const t = toneOf(`학생${10000000 + i * 7919}`)
      expect(t.hair).toBeLessThan(HAIR_TONES.length)
      expect(t.shirt).toBeLessThan(SHIRT_TONES.length)
      tones.add(`${t.hair}.${t.shirt}`)
    }
    // 24가지 조합 대부분이 나와야 순위표에서 모두 같아 보이지 않는다
    expect(tones.size).toBeGreaterThan(18)
  })

  it('상의 아이템을 입으면 그 색이 몸통에 칠해진다', () => {
    const { w, h } = PART.torso
    const torso = new Array(w * h).fill(0)
    const red = PAL.indexOf('#e43b44') + 1
    torso[8 * w + 10] = red
    const px = composePixels({ eq: { top: { id: 1, slot: 'top', parts: { torso } } } })
    const [ox, oy] = PART.torso.o
    expect(px[(oy + 8) * SIZE + ox + 10]).toBe('#e43b44')
  })

  it('머리를 전부 덮는 모자를 쓰면 기본 머리가 사라진다', () => {
    const { w, h } = PART.head
    const head = new Array(w * h).fill(0)
    const hat = { id: 2, slot: 'hat', cover: 'full', parts: { head } }
    const bare = composePixels({ seed: 'x' })
    const covered = composePixels({ seed: 'x', eq: { hat } })
    const tone = HAIR_TONES[toneOf('x').hair][0]
    expect(bare).toContain(tone)
    expect(covered.filter(c => c === tone).length).toBeLessThan(bare.filter(c => c === tone).length)
  })

  it('상반신은 머리와 어깨를 자른다', () => {
    const b = crop(composePixels(), BUST)
    expect(b).toHaveLength(BUST.w * BUST.h)
    // 위·아래 끝 줄 사이에 그림이 있다
    expect(b.filter(Boolean).length).toBeGreaterThan(400)
  })

  it('팔레트는 64색이고 순서가 고정이다', () => {
    // 아이템이 색 번호로 저장되므로 앞쪽 색이 바뀌면 안 된다
    expect(PAL).toHaveLength(64)
    expect(PAL[0]).toBe('#be4a2f')
    expect(PAL[31]).toBe('#c28569')
    expect(PAL[63]).toBe('#ff6b6b')
  })
})
