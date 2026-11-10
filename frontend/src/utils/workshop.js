// 캐릭터 공방(관리자 아이템 편집기)의 그리기 도구와 JSON 형식.
// "우리반 도트 공방" 프로토타입에서 옮겼다. 화면과 상관없는 계산만 둬서 테스트할 수 있다.
//
// 그림(draft)은 { 부위: Uint8Array } 이고 값은 PAL 번호(1~64, 0은 빈칸)다.
import { PAL, PART, BASE, FACE, FOOT, BOOT, SLOTS, SLOT_KEYS, PAIR, VARIANT_LABEL,
  partsFor, allowedCell, buildPart, composePixels, capPixels } from './character'

// 편집 중에는 하의의 바지·치마를 오가도 그림이 남도록 세 부위를 다 들고 있는다
export const DRAFT_PARTS = {
  hair: ['head'], hat: ['head'], face: ['head'], acc: ['head'],
  top: ['torso', 'armL', 'armR'], bottom: ['legL', 'legR', 'skirt'], shoes: ['legL', 'legR']
}

export const blankPart = p => new Uint8Array(PART[p].w * PART[p].h)
export const blankDraft = slot => Object.fromEntries(DRAFT_PARTS[slot].map(p => [p, blankPart(p)]))
export const cloneDraft = d => Object.fromEntries(Object.entries(d).map(([k, v]) => [k, v.slice()]))
export const isBlank = d => Object.values(d).every(a => !a.some(v => v))

// 저장할 부위만 남긴다(바지면 치마 그림을 버리는 식)
export function partsToSave (slot, variant, draft) {
  return Object.fromEntries(partsFor(slot, variant).map(p => [p, draft[p] || blankPart(p)]))
}

// 팔레트를 보여 줄 차례: 분홍·빨강·보라 / 노랑·주황·초록 / 파랑·청록·회색 / 피부·갈색·어두운색
export const DISPLAY_ORDER = ['#ffd6e0', '#ffb3c7', '#ff8fab', '#f6757a', '#ff6b6b', '#e43b44', '#ff0044', '#d6336c',
  '#a22633', '#b55088', '#68386c', '#e0c3fc', '#b8a1e3', '#9b5de5', '#4a2c6f', '#3d348b',
  '#fff3b0', '#fee761', '#ffe0a3', '#feae34', '#ffc4a3', '#f77622', '#d77643', '#be4a2f',
  '#b5b35c', '#7a7a3a', '#c1f0e1', '#8fd9b6', '#63c74d', '#3e8948', '#265c42', '#193c3e',
  '#bde0fe', '#8ec5ff', '#2ce8f5', '#0099db', '#7678ed', '#124e89', '#1aa7a1', '#0f6e6a',
  '#ffffff', '#e5e7eb', '#c0cbdc', '#9ca3af', '#8b9bb4', '#5a6988', '#4b5563', '#3a4466',
  '#ffe3cc', '#f5e6d3', '#ead4aa', '#e8b796', '#e4a672', '#d9b38c', '#c28569', '#c68642',
  '#b86f50', '#8d5524', '#8c5a3c', '#733e39', '#5a3825', '#3e2731', '#262b44', '#181425']

const rgb = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
const lum = c => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]

// 색마다 '한 단계 어두운 색'(팔레트 안에서). 자동 명암이 쓴다.
const DARK = PAL.map((h, i) => {
  const c = rgb(h)
  const t = [c[0] * 0.68, c[1] * 0.68, c[2] * 0.78]
  let best = i
  let bd = 1e9
  PAL.forEach((h2, j) => {
    if (j === i) return
    const c2 = rgb(h2)
    if (lum(c2) >= lum(c) - 10) return
    const d = (c2[0] - t[0]) ** 2 + (c2[1] - t[1]) ** 2 + (c2[2] - t[2]) ** 2
    if (d < bd) { bd = d; best = j }
  })
  return best
})

// 아래·오른쪽 가장자리 칸을 한 단계 어둡게 한다
export function shade (draft) {
  for (const p in draft) {
    const { w, h } = PART[p]
    const src = draft[p].slice()
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x
        const v = src[i]
        if (!v) continue
        const below = y + 1 < h ? src[i + w] : 0
        const right = x + 1 < w ? src[i + 1] : 0
        if (!below || !right) draft[p][i] = DARK[v - 1] + 1
      }
    }
  }
}

// 브레젠험 직선. 지나는 칸마다 fn(x, y)
export function line (x0, y0, x1, y1, fn) {
  const dx = Math.abs(x1 - x0)
  const dy = -Math.abs(y1 - y0)
  const sx = x0 < x1 ? 1 : -1
  const sy = y0 < y1 ? 1 : -1
  let e = dx + dy
  for (;;) {
    fn(x0, y0)
    if (x0 === x1 && y0 === y1) break
    const e2 = 2 * e
    if (e2 >= dy) { e += dy; x0 += sx }
    if (e2 <= dx) { e += dx; y0 += sy }
  }
}

// 채우기. 빈칸을 채울 때는 맨몸이 있는 칸 안에서만 번진다(치마는 예외).
// ok(x, y) 가 false 인 칸(칠할 수 없는 곳)은 넘지 않는다.
export function flood (a, p, x, y, v, ok = () => true) {
  const { w, h } = PART[p]
  const t = a[y * w + x]
  if (t === v) return
  const free = p === 'skirt'
  const st = [[x, y]]
  while (st.length) {
    const [cx, cy] = st.pop()
    if (cx < 0 || cy < 0 || cx >= w || cy >= h) continue
    const i = cy * w + cx
    if (a[i] !== t || (t === 0 && !free && !BASE[p][i]) || !ok(cx, cy)) continue
    a[i] = v
    st.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1])
  }
}

/* ---------- 맨몸 가이드 ---------- */
// 편집기 바탕에 흐리게 깔 그림(색 배열, 템플릿 크기). 자리마다 무엇을 비울지가 다르다.
export function guidePart (slot, variant, p) {
  const o = { pad: false }
  if (p === 'skirt') {
    // 치마 자리는 따로 그린 맨몸이 없어서 전신에서 잘라 온다
    const px = composePixels()
    const { w, h, o: [ox, oy] } = PART.skirt
    const out = []
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) out.push(px[(oy + y) * 64 + ox + x])
    return out
  }
  if (slot === 'face') return buildPart(p, { face: { parts: {} } }, o)
  if (slot === 'acc') return buildPart(p, {}, o)
  if (slot === 'shoes') return buildPart(p, { shoes: { kind: variant, parts: {} } }, o)
  if (slot === 'hat') return buildPart(p, { hat: { cover: variant, parts: { head: blankPart('head') } } }, o)
  return buildPart(p, {}, { ...o, defHair: false })
}

/* ---------- JSON ---------- */
const CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
const VARIANT_KEY = { hat: 'cover', bottom: 'btype', shoes: 'kind' }

function prettyJSON (o) {
  // 숫자 두 개짜리 배열만 한 줄로 접는다. rows 는 한 줄에 하나씩 남는다.
  return JSON.stringify(o, null, 2).replace(/\[\n\s+(-?\d+),\n\s+(-?\d+)\n\s+\]/g, '[$1, $2]')
}

// 그림 → JSON 문자열. 부위마다 그림이 있는 네모만 rows 로 적는다.
export function itemToJSON ({ name = '', designer = '', slot, variant, parts }) {
  const obj = { name, designer, slot }
  if (VARIANT_KEY[slot]) obj[VARIANT_KEY[slot]] = variant
  const cmap = new Map()
  const out = {}
  for (const p of partsFor(slot, variant)) {
    const a = parts[p]
    if (!a) continue
    const { w, h } = PART[p]
    let x0 = w
    let y0 = h
    let x1 = -1
    let y1 = -1
    a.forEach((c, i) => {
      if (!c) return
      const x = i % w
      const y = Math.floor(i / w)
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y)
    })
    if (x1 < 0) continue
    const rows = []
    for (let y = y0; y <= y1; y++) {
      let r = ''
      for (let x = x0; x <= x1; x++) {
        const c = a[y * w + x]
        if (!c) { r += '.'; continue }
        if (!cmap.has(c)) cmap.set(c, CHARS[cmap.size])
        r += cmap.get(c)
      }
      rows.push(r)
    }
    out[p] = { x: x0, y: y0, rows }
  }
  obj.colors = Object.fromEntries([...cmap].map(([c, ch]) => [ch, PAL[c - 1]]))
  obj.parts = out
  return prettyJSON(obj)
}

// 빈 템플릿 JSON. 칠할 수 있는 네모만큼 '.' 을 채워 둔다.
export function templateJSON (slot, variant) {
  const obj = {
    _안내: ['rows의 글자 하나가 칸 하나예요. . 은 빈칸이에요.',
      'colors에 글자와 색을 짝지어 적고, 그 글자로 rows를 채워요.',
      '외곽선은 자동이에요. 그림이 있는 부분만 남기고 x, y로 위치를 정해도 돼요.'],
    name: '',
    designer: '',
    slot
  }
  if (VARIANT_KEY[slot]) obj[VARIANT_KEY[slot]] = variant
  obj.colors = { a: '#e43b44', b: '#a22633', c: '#ffffff' }
  obj.mirror = false
  obj.parts = {}
  for (const p of partsFor(slot, variant)) {
    const { w, h } = PART[p]
    let x = 0
    let y = 0
    let W = w
    let H = h
    if (slot === 'face') { x = FACE.x0; y = FACE.y0; W = FACE.x1 - FACE.x0 + 1; H = FACE.y1 - FACE.y0 + 1 } else if (slot === 'bottom' && variant === 'pants') { H = FOOT } else if (slot === 'shoes') { y = variant === 'boots' ? BOOT : FOOT; H = h - y }
    obj.parts[p] = { x, y, rows: Array.from({ length: H }, () => '.'.repeat(W)) }
  }
  return prettyJSON(obj)
}

function nearest (hex) {
  const c = rgb(hex)
  let best = 0
  let bd = 1e9
  PAL.forEach((h, i) => {
    const d = rgb(h).reduce((s, v, k) => s + (v - c[k]) ** 2, 0)
    if (d < bd) { bd = d; best = i }
  })
  return best
}

/**
 * JSON 문자열을 읽어 아이템으로 만든다. 고칠 수 있는 문제는 고치고 msgs 에 적는다.
 * @returns {{ item: null | { name, designer, slot, variant, parts }, msgs: { t: 'ok'|'warn'|'err', m: string }[] }}
 */
export function parseItemJSON (text) {
  const msgs = []
  const fail = m => { msgs.push({ t: 'err', m }); return { item: null, msgs } }
  let o
  try {
    o = JSON.parse(text)
  } catch (e) {
    return fail(`JSON 문법이 맞지 않아요. 쉼표, 따옴표, 괄호를 확인해 주세요. (${e.message})`)
  }
  if (!o || typeof o !== 'object' || Array.isArray(o)) return fail('맨 바깥은 { } 로 감싼 하나의 객체여야 해요.')
  if (!SLOT_KEYS.includes(o.slot)) return fail(`slot은 ${SLOT_KEYS.join(', ')} 중 하나여야 해요.`)
  const slot = o.slot
  const choices = SLOTS[slot].variants
  let variant = VARIANT_KEY[slot] ? o[VARIANT_KEY[slot]] : ''
  if (choices.length && !choices.includes(variant)) {
    if (variant !== undefined) msgs.push({ t: 'warn', m: `'${variant}'는 쓸 수 없는 값이라 기본값(${choices[0]})으로 읽었어요.` })
    variant = choices[0]
  }
  if (!o.colors || typeof o.colors !== 'object') return fail('colors가 없어요. 예: "colors": { "r": "#e43b44" }')
  const map = {}
  const snapped = []
  for (const [k, hex] of Object.entries(o.colors)) {
    if (k.length !== 1 || k === '.' || k === ' ') {
      msgs.push({ t: 'warn', m: `colors의 '${k}'는 글자 한 개가 아니라서 건너뛰었어요.` })
      continue
    }
    const hx = String(hex).trim().toLowerCase().replace(/^#?/, '#')
    if (!/^#[0-9a-f]{6}$/.test(hx)) {
      msgs.push({ t: 'warn', m: `'${k}'의 색 '${hex}'를 읽을 수 없어요. #RRGGBB 형식으로 적어주세요.` })
      continue
    }
    const i = nearest(hx)
    if (PAL[i] !== hx) snapped.push(`${k}: ${hx} → ${PAL[i]}`)
    map[k] = i + 1
  }
  if (snapped.length) msgs.push({ t: 'warn', m: '팔레트에 없는 색을 가까운 색으로 바꿨어요. ' + snapped.join(', ') })
  if (!o.parts || typeof o.parts !== 'object') return fail('parts가 없어요.')
  const allowed = partsFor(slot, variant)
  const parts = Object.fromEntries(allowed.map(p => [p, blankPart(p)]))
  const given = new Set()
  const unknown = new Set()
  let crop = 0
  let blocked = 0
  let painted = 0
  for (const [pn, pd] of Object.entries(o.parts)) {
    if (!allowed.includes(pn)) {
      msgs.push({ t: 'warn', m: `'${pn}'은(는) 이 종류에서 쓰지 않는 부위라 건너뛰었어요. 쓸 수 있는 부위: ${allowed.join(', ')}` })
      continue
    }
    if (!pd || !Array.isArray(pd.rows)) {
      msgs.push({ t: 'warn', m: `${pn}에 rows 목록이 없어요.` })
      continue
    }
    given.add(pn)
    const { w, h } = PART[pn]
    const x0 = Math.round(+pd.x || 0)
    const y0 = Math.round(+pd.y || 0)
    const a = parts[pn]
    pd.rows.forEach((row, j) => {
      [...String(row)].forEach((ch, i) => {
        if (ch === '.' || ch === ' ') return
        const c = map[ch]
        if (!c) { unknown.add(ch); return }
        const X = x0 + i
        const Y = y0 + j
        if (X < 0 || Y < 0 || X >= w || Y >= h) { crop++; return }
        if (!allowedCell(slot, variant, pn, X, Y)) { blocked++; return }
        a[Y * w + X] = c
        painted++
      })
    })
  }
  if (o.mirror === true) {
    for (const pn of allowed) {
      const { w } = PART[pn]
      const q = PAIR[pn]
      if (q) {
        if (given.has(pn) && !given.has(q) && allowed.includes(q)) {
          parts[pn].forEach((c, i) => {
            if (c) parts[q][Math.floor(i / w) * w + (w - 1 - i % w)] = c
          })
        }
      } else {
        const a = parts[pn]
        a.forEach((c, i) => {
          const x = i % w
          const y = Math.floor(i / w)
          if (c && x < w / 2 && !a[y * w + (w - 1 - x)]) a[y * w + (w - 1 - x)] = c
        })
      }
    }
  }
  if (unknown.size) msgs.push({ t: 'warn', m: `colors에 없는 글자(${[...unknown].join(' ')})는 빈칸으로 처리했어요.` })
  if (crop) msgs.push({ t: 'warn', m: `템플릿 밖으로 넘친 ${crop}칸을 잘라냈어요.` })
  if (blocked) msgs.push({ t: 'warn', m: `칠할 수 없는 곳에 적은 ${blocked}칸을 지웠어요.` })
  if (isBlank(parts)) return fail('그려진 칸이 하나도 없어요. rows에 colors의 글자를 적어주세요.')
  const kind = variant ? ` · ${VARIANT_LABEL[variant]}` : ''
  msgs.unshift({ t: 'ok', m: `${SLOTS[slot].label}${kind} 아이템을 읽었어요. 칠한 칸 ${painted}개${o.mirror === true ? ' (대칭으로 채운 칸 제외)' : ''}.` })
  return { item: { name: String(o.name || ''), designer: String(o.designer || ''), slot, variant, parts }, msgs }
}

// 맨몸 참고 그림(글자 그림). o 외곽선 · s 피부 · c 기본 옷 · p 기본 반바지 · f 기본 신발
// · h 기본 머리 · e 눈·입·볼 · x 그릴 수 없는 곳 · . 빈칸
export function refArt (slot, variant) {
  const CMAP = { '#181425': 'o', '#f3cba7': 's', '#e0a68a': 's', '#ebbc9a': 's', '#eef1f5': 'c', '#c0cbdc': 'c', '#3e2731': 'h', '#733e39': 'h' }
  const lines = []
  for (const p of partsFor(slot, variant)) {
    const { w, h } = PART[p]
    const g = guidePart(slot, variant, p)
    lines.push(`${p} (${w}×${h})`)
    let ruler = ''
    for (let x = 0; x < w; x += 5) ruler += String(x).padEnd(5, ' ')
    lines.push('    ' + ruler.slice(0, w + 1).replace(/\s+$/, ''))
    for (let y = 0; y < h; y++) {
      let r = String(y).padStart(3, ' ') + ' '
      for (let x = 0; x < w; x++) {
        const c = g[y * w + x]
        if (!allowedCell(slot, variant, p, x, y)) { r += 'x'; continue }
        if (!c) { r += '.'; continue }
        let ch = CMAP[c]
        if (!ch) ch = (p === 'legL' || p === 'legR') ? (y >= FOOT ? 'f' : 'p') : 'e'
        if (p === 'skirt' && ch === 'e') ch = 'p'
        if ((p === 'legL' || p === 'legR') && ch === 'c') ch = 'p'
        r += ch
      }
      lines.push(r)
    }
    lines.push('')
  }
  return lines.join('\n')
}

// 생성형 AI 에게 아이템을 그려 달라고 부탁하는 글
export function aiPrompt (slot, variant, label) {
  const vk = VARIANT_KEY[slot]
  return `'코알라 OJ 캐릭터'에 넣을 ${label} 아이템을 아래 규칙에 맞춰 JSON으로 만들어 주세요.
만들 아이템: [여기에 아이템 설명을 적어주세요. 예) 하늘색 체크무늬 교복 셔츠]

규칙
- 출력은 JSON 하나만. 설명이나 코드 블록 표시 없이.
- slot은 "${slot}"${vk ? `, ${vk}는 "${variant}"` : ''}.
- colors: 글자 한 개 → "#RRGGBB". 아래 팔레트 64색 중에서만 고르세요.
- parts: 부위 이름마다 { "x": 시작 칸, "y": 시작 줄, "rows": [문자열 목록] }. 글자 하나가 칸 하나, "."은 빈칸.
- 쓸 수 있는 부위: ${partsFor(slot, variant).map(p => `${p} (${PART[p].w}×${PART[p].h})`).join(', ')}
- 참고 그림에서 x로 표시된 칸에는 그리지 마세요. 외곽선은 자동으로 그려지니 넣지 마세요.
- 귀여운 2등신 도트 캐릭터용이에요. 명암은 같은 계열의 한 단계 어두운 색으로 아래쪽과 오른쪽에 넣어주세요.
- 좌우 대칭이면 "mirror": true로 두고 왼쪽 절반(또는 왼팔·왼다리)만 그려도 돼요.

참고 그림 (o 외곽선, s 피부, c 기본 옷, p 기본 반바지, f 기본 신발, h 기본 머리, e 눈·입, x 그릴 수 없는 곳, . 빈칸)
${refArt(slot, variant)}
팔레트 64색
${DISPLAY_ORDER.join(' ')}

빈 템플릿
${templateJSON(slot, variant)}`
}

/* ---------- 예시 아이템 ---------- */
// 프로토타입에 있던 예시 15개. 처음 샵을 채우거나 JSON 작성법을 보여 줄 때 쓴다.
const pi = hex => PAL.indexOf(hex) + 1
function draw (p, fn) {
  const a = blankPart(p)
  const { w, h } = PART[p]
  fn((x, y, hex) => { if (x >= 0 && y >= 0 && x < w && y < h) a[y * w + x] = hex ? pi(hex) : 0 })
  return a
}
// 맨몸이 있는 칸에만 칠한다
function onMask (p, fn) {
  return draw(p, s => {
    const { w, h } = PART[p]
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (BASE[p][y * w + x]) {
          const c = fn(x, y)
          if (c) s(x, y, c)
        }
      }
    }
  })
}
const armsOf = fn => ({ armL: onMask('armL', (x, y) => fn(x, y, 'L')), armR: onMask('armR', (x, y) => fn(x, y, 'R')) })
const legsOf = fn => ({ legL: onMask('legL', fn), legR: onMask('legR', fn) })

export function exampleItems () {
  const beanie = {
    head: draw('head', s => {
      const R = { 4: [13, 26], 5: [10, 29], 6: [8, 31], 7: [6, 33], 8: [5, 34] }
      for (let y = 4; y <= 15; y++) {
        const [a, b] = R[y] || [4, 35]
        for (let x = a; x <= b; x++) s(x, y, y >= 13 ? '#a22633' : x % 3 === 0 && y >= 6 ? '#a22633' : '#e43b44')
      }
      for (let y = 0; y < 4; y++) for (let x = 18; x < 22; x++) if (!((y === 0 || y === 3) && (x === 18 || x === 21))) s(x, y, '#ffffff')
      s(21, 2, '#c0cbdc')
    })
  }
  const twin = {
    head: draw('head', s => {
      capPixels('straight').forEach(([x, y, t]) => s(x, y, t ? '#e4a672' : '#b86f50'))
      const W = [1, 2, 2, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 1, 1]
      W.forEach((wd, k) => {
        const y = 14 + k
        for (let x = 0; x < 6; x++) {
          if (Math.abs(x - 2.5) <= wd) {
            const c = y === 15 ? '#e43b44' : x <= 1 ? '#733e39' : '#b86f50'
            s(x, y, c); s(39 - x, y, c)
          }
        }
      })
    })
  }
  const afro = {
    head: draw('head', s => {
      for (let y = 0; y <= 27; y++) {
        for (let x = 0; x < 40; x++) {
          const e = ((x - 19.5) / 19.5) ** 2 + ((y - 13) / 14) ** 2
          if (e > 1) continue
          if (y >= 17 && x >= 8 && x <= 31) continue
          s(x, y, (x * 3 + y * 2) % 7 === 0 ? '#733e39' : (x + y) % 9 === 0 && y < 12 ? '#b86f50' : '#3e2731')
        }
      }
    })
  }
  const track = {
    torso: onMask('torso', (x, y) => x === 11 || x === 12 ? '#c0cbdc' : y === 14 || x === 20 || y <= 3 ? '#265c42' : '#3e8948'),
    ...armsOf((x, y, side) => y > 10 ? null : (side === 'L' ? x === 2 : x === 7) ? '#ffffff' : y === 10 ? '#265c42' : '#3e8948')
  }
  const hoodie = {
    torso: onMask('torso', (x, y) => {
      if (y === 10 && x >= 7 && x <= 16) return '#f77622'
      if (y > 10 && y < 13 && (x === 7 || x === 16)) return '#f77622'
      if ((x === 10 || x === 13) && y >= 3 && y <= 6) return '#ffffff'
      if (y === 14 || x === 20) return '#f77622'
      return '#feae34'
    }),
    ...armsOf((x, y) => y > 10 ? null : y === 10 || x === 7 ? '#f77622' : '#feae34')
  }
  const stripe = { torso: onMask('torso', (x, y) => y % 2 ? '#ffffff' : '#0099db'), ...armsOf((x, y) => y > 5 ? null : y % 2 ? '#ffffff' : '#0099db') }
  const jeans = legsOf((x, y) => y < FOOT ? (x === 4 ? '#0099db' : '#124e89') : null)
  const pleats = {
    skirt: draw('skirt', s => {
      for (let y = 2; y <= 11; y++) {
        const hw = Math.min(12.5, 8.5 + (y - 2) * 0.5)
        for (let x = 0; x < 26; x++) if (Math.abs(x - 12.5) <= hw) s(x, y, y <= 4 ? '#262b44' : y === 11 ? '#262b44' : (x % 3 === 0 && y >= 5) ? '#262b44' : '#124e89')
      }
    })
  }
  const happyFace = {
    head: draw('head', s => {
      [[12, 25], [13, 24], [14, 23], [15, 24], [16, 25]].forEach(([x, y]) => { s(x, y, '#181425'); s(39 - x, y, '#181425') })
      ;[[10, 27], [11, 27]].forEach(([x, y]) => { s(x, y, '#f6757a'); s(39 - x, y, '#f6757a') })
      s(18, 28, '#733e39'); s(21, 28, '#733e39'); s(19, 29, '#e43b44'); s(20, 29, '#e43b44')
    })
  }
  const roundGlasses = {
    head: draw('head', s => {
      const c = '#262b44'
      const m = (x, y) => { s(x, y, c); s(39 - x, y, c) }
      for (let x = 12; x <= 16; x++) { m(x, 20); m(x, 27) }
      for (let y = 21; y <= 26; y++) { m(11, y); m(17, y) }
      m(18, 22); m(19, 22)
      for (let x = 5; x <= 10; x++) m(x, 22)
      s(13, 21, '#ffffff'); s(24, 21, '#ffffff')
    })
  }
  const heartSticker = {
    head: draw('head', s => {
      [[9, 26], [11, 26], [9, 27], [10, 27], [11, 27], [10, 28]].forEach(([x, y]) => { s(x, y, '#ff6b6b'); s(39 - x, y, '#ff6b6b') })
    })
  }
  const sneakers = legsOf((x, y) => y < FOOT ? null : y === 13 ? '#8b9bb4' : y === 11 && (x === 4 || x === 6) ? '#e43b44' : x === 8 ? '#c0cbdc' : '#ffffff')
  const rainBoots = legsOf((x, y) => y < BOOT ? null : y === 13 ? '#5a3825' : y === BOOT ? '#feae34' : x === 8 ? '#feae34' : x === 3 && y < 11 ? '#fff3b0' : '#fee761')
  const starPin = {
    head: draw('head', s => {
      [[30, 8], [29, 9], [30, 9], [31, 9], [27, 10], [28, 10], [29, 10], [30, 10], [31, 10], [32, 10], [33, 10],
        [28, 11], [29, 11], [30, 11], [31, 11], [32, 11], [29, 12], [31, 12], [28, 13], [32, 13]].forEach(([x, y]) => s(x, y, '#fee761'))
      s(30, 10, '#feae34')
    })
  }
  const bear = {
    head: draw('head', s => {
      for (let y = 4; y <= 31; y++) {
        const [a, b] = y < 6 ? [9, 30] : y < 8 ? [6, 33] : [4, 35]
        for (let x = a; x <= b; x++) {
          if (y >= 15 && x >= 9 && x <= 30 && y <= 30) continue
          s(x, y, x === b || y === 31 ? '#733e39' : '#b86f50')
        }
      }
      for (const cx of [8, 31]) {
        for (let y = 0; y <= 6; y++) {
          for (let x = cx - 3; x <= cx + 3; x++) {
            const d = (x - cx) ** 2 + (y - 3) ** 2
            if (d <= 10) s(x, y, d <= 3 ? '#e4a672' : '#b86f50')
          }
        }
      }
    })
  }
  return [
    { name: '빨간 비니', slot: 'hat', variant: 'top', price: 40, parts: beanie },
    { name: '곰돌이 후드', slot: 'hat', variant: 'full', price: 60, parts: bear },
    { name: '별 머리핀', slot: 'hat', variant: 'none', price: 30, parts: starPin },
    { name: '양갈래 머리', slot: 'hair', variant: '', price: 70, parts: twin },
    { name: '뽀글 파마', slot: 'hair', variant: '', price: 60, parts: afro },
    { name: '반달 웃는 눈', slot: 'face', variant: '', price: 40, parts: happyFace },
    { name: '둥근 안경', slot: 'acc', variant: '', price: 35, parts: roundGlasses },
    { name: '하트 볼 스티커', slot: 'acc', variant: '', price: 30, parts: heartSticker },
    { name: '노란 후드티', slot: 'top', variant: '', price: 60, parts: hoodie },
    { name: '초록 체육복', slot: 'top', variant: '', price: 60, parts: track },
    { name: '줄무늬 티셔츠', slot: 'top', variant: '', price: 50, parts: stripe },
    { name: '청바지', slot: 'bottom', variant: 'pants', price: 50, parts: jeans },
    { name: '남색 플리츠 치마', slot: 'bottom', variant: 'skirt', price: 50, parts: pleats },
    { name: '흰 운동화', slot: 'shoes', variant: 'low', price: 30, parts: sneakers },
    { name: '노란 장화', slot: 'shoes', variant: 'boots', price: 40, parts: rainBoots }
  ]
}
