import { describe, it, expect } from 'vitest'
import { PART, PAL, CODE, encodePart, decodePart, itemFromRecord, allowedCell, FOOT, composePixels, SIZE } from '@/utils/character'
import { blankDraft, isBlank, partsToSave, shade, flood, line, itemToJSON, parseItemJSON,
  templateJSON, refArt, exampleItems, guidePart } from '@/utils/workshop'

describe('아이템 저장 형식', () => {
  it('글자표는 빈칸 + 64색', () => {
    expect(CODE).toHaveLength(65)
    expect(new Set(CODE).size).toBe(65)
  })

  it('부위 그림을 문자열로 바꿨다가 그대로 되돌린다', () => {
    const a = new Uint8Array(PART.head.w * PART.head.h)
    a[0] = 1; a[5] = 64; a[100] = 33
    const text = encodePart(a)
    expect(text).toHaveLength(1440)
    expect(text[0]).toBe('a')
    expect(text[5]).toBe('/')
    expect(decodePart(text, 'head')).toEqual(a)
  })

  it('서버 레코드를 그리기용 아이템으로 바꾼다', () => {
    const it = itemFromRecord({ id: 3, slot: 'hat', variant: 'full', parts: { head: 'a' + '.'.repeat(1439) }, last_update_time: 't' })
    expect(it.cover).toBe('full')
    expect(it.v).toBe('t')
    expect(it.parts.head[0]).toBe(1)
  })
})

describe('그리기 도구', () => {
  it('바지는 발 구역에 칠할 수 없다', () => {
    expect(allowedCell('bottom', 'pants', 'legL', 3, FOOT - 1)).toBe(true)
    expect(allowedCell('bottom', 'pants', 'legL', 3, FOOT)).toBe(false)
    expect(allowedCell('face', '', 'head', 0, 0)).toBe(false)
  })

  it('저장할 때는 종류에 맞는 부위만 남긴다', () => {
    const d = blankDraft('bottom')
    expect(Object.keys(d).sort()).toEqual(['legL', 'legR', 'skirt'])
    expect(Object.keys(partsToSave('bottom', 'skirt', d))).toEqual(['skirt'])
    expect(Object.keys(partsToSave('bottom', 'pants', d))).toEqual(['legL', 'legR'])
  })

  it('채우기는 맨몸 밖으로 번지지 않는다', () => {
    const d = blankDraft('top')
    flood(d.torso, 'torso', 10, 8, 5)
    const painted = d.torso.filter(Boolean).length
    expect(painted).toBeGreaterThan(100)
    expect(painted).toBeLessThan(PART.torso.w * PART.torso.h)
  })

  it('직선은 양 끝을 지난다', () => {
    const cells = []
    line(0, 0, 3, 2, (x, y) => cells.push(`${x},${y}`))
    expect(cells[0]).toBe('0,0')
    expect(cells[cells.length - 1]).toBe('3,2')
  })

  it('자동 명암은 가장자리를 어둡게 한다', () => {
    const d = blankDraft('top')
    d.torso[0] = PAL.indexOf('#feae34') + 1
    shade(d)
    expect(d.torso[0]).not.toBe(PAL.indexOf('#feae34') + 1)
  })

  it('맨몸 가이드는 템플릿 크기다', () => {
    expect(guidePart('hair', '', 'head')).toHaveLength(1440)
    expect(guidePart('bottom', 'skirt', 'skirt')).toHaveLength(26 * 16)
  })
})

describe('JSON', () => {
  it('예시 15개가 모두 그려져 있고 JSON 으로 오간다', () => {
    const items = exampleItems()
    expect(items).toHaveLength(15)
    for (const ex of items) {
      expect(isBlank(ex.parts)).toBe(false)
      const { item, msgs } = parseItemJSON(itemToJSON(ex))
      expect(msgs.filter(m => m.t === 'err')).toEqual([])
      expect(item.slot).toBe(ex.slot)
      expect(item.variant).toBe(ex.variant)
      for (const p of Object.keys(item.parts)) expect(Array.from(item.parts[p])).toEqual(Array.from(ex.parts[p]))
    }
  })

  it('예시를 입히면 맨몸과 달라진다', () => {
    const bare = composePixels()
    for (const ex of exampleItems()) {
      const eq = { [ex.slot]: { id: 1, slot: ex.slot, parts: ex.parts, cover: ex.variant, btype: ex.variant, kind: ex.variant } }
      expect(composePixels({ eq })).not.toEqual(bare)
      expect(composePixels({ eq })).toHaveLength(SIZE * SIZE)
    }
  })

  it('문법 오류와 빈 그림을 알려 준다', () => {
    expect(parseItemJSON('{').item).toBeNull()
    expect(parseItemJSON('{"slot":"cape"}').item).toBeNull()
    const empty = parseItemJSON(templateJSON('top', ''))
    expect(empty.item).toBeNull()
    expect(empty.msgs.some(m => m.m.includes('그려진 칸이 하나도'))).toBe(true)
  })

  it('팔레트 밖 색은 가까운 색으로, 칠할 수 없는 칸은 지운다', () => {
    const { item, msgs } = parseItemJSON(JSON.stringify({
      slot: 'bottom', btype: 'pants', colors: { a: '#e43b45' },
      parts: { legL: { x: 3, y: 9, rows: ['a', 'a', 'a'] } }
    }))
    expect(item.parts.legL.filter(Boolean)).toHaveLength(2)
    expect(msgs.some(m => m.t === 'warn' && m.m.includes('가까운 색'))).toBe(true)
    expect(msgs.some(m => m.m.includes('칠할 수 없는 곳'))).toBe(true)
  })

  it('mirror 면 왼팔만 적어도 오른팔이 채워진다', () => {
    const { item } = parseItemJSON(JSON.stringify({
      slot: 'top', mirror: true, colors: { a: '#e43b44' }, parts: { armL: { x: 2, y: 2, rows: ['a'] } }
    }))
    expect(item.parts.armR[2 * 10 + 7]).toBe(PAL.indexOf('#e43b44') + 1)
  })

  it('참고 그림에 칠할 수 없는 곳이 x 로 나온다', () => {
    expect(refArt('face', '')).toContain('x')
    expect(refArt('top', '')).toContain('torso (24×18)')
  })
})
