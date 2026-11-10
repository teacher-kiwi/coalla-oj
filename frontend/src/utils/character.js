// 도트 캐릭터 그리기. "우리반 도트 공방" 프로토타입의 그리는 부분을 옮겼다.
//
// 캐릭터는 64×64 칸이다. 몸을 부위(머리·몸통·팔·다리·치마)로 나눠 따로 그린 뒤
// 동작마다 부위를 몇 칸씩 옮겨 겹친다. 그래서 아이템은 부위별로 한 번만 그리면
// 서기·걷기·점프가 저절로 만들어진다.
//
// 이 파일은 칸마다 색(#rrggbb 또는 null)만 계산한다. 캔버스에 찍는 일은
// 컴포넌트가 한다. 그래서 캔버스 없이 테스트할 수 있다.

export const SIZE = 64

// 아이템은 색을 이 목록의 번호(1부터, 0은 빈칸)로 저장한다.
// **순서를 절대 바꾸지 말 것.** 바꾸면 저장된 모든 아이템의 색이 바뀐다. 새 색은 끝에만 붙인다.
// 앞 32색은 Endesga 32 팔레트, 뒤 32색은 파스텔·피부톤·갈색·회색·보라 계열.
export const PAL = ['#be4a2f', '#d77643', '#ead4aa', '#e4a672', '#b86f50', '#733e39', '#3e2731', '#a22633',
  '#e43b44', '#f77622', '#feae34', '#fee761', '#63c74d', '#3e8948', '#265c42', '#193c3e',
  '#124e89', '#0099db', '#2ce8f5', '#ffffff', '#c0cbdc', '#8b9bb4', '#5a6988', '#3a4466',
  '#262b44', '#181425', '#ff0044', '#68386c', '#b55088', '#f6757a', '#e8b796', '#c28569',
  '#ffd6e0', '#ffb3c7', '#e0c3fc', '#b8a1e3', '#c1f0e1', '#8fd9b6', '#bde0fe', '#8ec5ff',
  '#fff3b0', '#ffe0a3', '#ffc4a3', '#9b5de5', '#4a2c6f', '#ff8fab', '#d6336c', '#1aa7a1',
  '#0f6e6a', '#b5b35c', '#7a7a3a', '#f5e6d3', '#d9b38c', '#8c5a3c', '#5a3825', '#ffe3cc',
  '#c68642', '#8d5524', '#e5e7eb', '#9ca3af', '#4b5563', '#3d348b', '#7678ed', '#ff6b6b']

// 부위: 크기(w×h)와 64×64 안에서의 왼쪽 위 위치(o)
export const PART = {
  skirt: { w: 26, h: 16, o: [19, 43] },
  head: { w: 40, h: 36, o: [12, 2] },
  torso: { w: 24, h: 18, o: [20, 33] },
  armL: { w: 10, h: 16, o: [14, 35] },
  armR: { w: 10, h: 16, o: [40, 35] },
  legL: { w: 11, h: 16, o: [22, 47] },
  legR: { w: 11, h: 16, o: [31, 47] }
}
// 겹치는 순서. 치마는 다리 위, 몸통 아래
const ORDER = ['legL', 'legR', 'skirt', 'torso', 'armL', 'armR', 'head']

// 머리 템플릿에서 이 줄 위가 '윗머리'. 윗머리만 덮는 모자를 쓰면 숨긴다.
const ZONE = 16
// 다리 템플릿에서 FOOT 줄부터 발. 부츠는 BOOT 줄까지 올라온다.
const FOOT = 11
const BOOT = 6

// 동작 8장. 부위를 [x, y] 칸만큼 옮긴다.
const UP = { head: [0, 1], torso: [0, 1], armL: [0, 1], armR: [0, 1] }
export const FRAMES = [
  { label: '서기 1', off: {} },
  { label: '서기 2', off: UP },
  { label: '걷기 1', off: { armL: [0, -1], armR: [0, 1], legL: [0, -2] } },
  { label: '걷기 2', off: UP },
  { label: '걷기 3', off: { armL: [0, 1], armR: [0, -1], legR: [0, -2] } },
  { label: '걷기 4', off: UP },
  { label: '점프 1', off: { head: [0, -1], torso: [0, -1], armL: [-1, -6], armR: [1, -6], legL: [0, -4], legR: [0, -4] } },
  { label: '점프 2', off: { armL: [-2, -2], armR: [2, -2], legL: [-1, 0], legR: [1, 0] } }
]
export const ANIM = { idle: [0, 1], walk: [2, 3, 4, 5], jump: [6, 7] }

/* ---------- 맨몸 캐릭터 ---------- */
const SKIN = '#f3cba7'
const SKIN_D = '#e0a68a'
const SKIN_SOFT = '#ebbc9a'
const SHIRT = '#eef1f5'
const SHIRT_D = '#c0cbdc'
const HAIR = '#3e2731'
const HAIR_HI = '#733e39'
const OUT = '#181425'
const HEAD_IN = [6, 4, 3, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 3, 5]

const blank = p => new Array(PART[p].w * PART[p].h).fill(null)
function setter (a, p) {
  const { w, h } = PART[p]
  return (x, y, c) => { if (x >= 0 && y >= 0 && x < w && y < h) a[y * w + x] = c }
}

function makeBase () {
  const B = {}
  let a = blank('head')
  let s = setter(a, 'head')
  for (let r = 0; r < 26; r++) {
    const k = HEAD_IN[r]
    for (let x = k; x < 30 - k; x++) s(5 + x, 8 + r, r === 25 || (x === 29 - k && r > 8 && r < 23) ? SKIN_SOFT : SKIN)
  }
  ;[[10, 27], [11, 27], [28, 27], [29, 27]].forEach(([x, y]) => s(x, y, '#f6757a'))
  B.head = a
  a = blank('torso')
  s = setter(a, 'torso')
  for (let r = 0; r < 13; r++) {
    const k = r === 0 ? 3 : r === 1 ? 1 : 0
    for (let x = k; x < 18 - k; x++) s(3 + x, 2 + r, r === 12 || x === 17 - k ? SHIRT_D : SHIRT)
  }
  B.torso = a
  for (const p of ['armL', 'armR']) {
    a = blank(p)
    s = setter(a, p)
    for (let r = 0; r < 12; r++) {
      const k = r === 0 || r === 11 ? 1 : 0
      for (let x = k; x < 6 - k; x++) {
        const sh = x === 5 - k
        s(2 + x, 1 + r, r < 4 ? (sh ? SHIRT_D : SHIRT) : (sh ? SKIN_D : SKIN))
      }
    }
    B[p] = a
  }
  for (const p of ['legL', 'legR']) {
    a = blank(p)
    s = setter(a, p)
    for (let r = 0; r < 13; r++) {
      for (let x = 0; x < 7; x++) {
        const sh = x === 6
        s(2 + x, 1 + r, r < 5 ? (sh ? '#3a4466' : '#5a6988') : r < 10 ? (sh ? SKIN_D : SKIN) : r < 12 ? '#3a4466' : '#262b44')
      }
    }
    B[p] = a
  }
  B.skirt = blank('skirt')
  return B
}
const BASE = makeBase()

function capPixels () {
  const out = []
  const add = (lx, r, t = 0) => out.push([lx + 5, r + 8, t])
  for (let r = -1; r <= 6; r++) {
    const k = r < 0 ? HEAD_IN[0] + 1 : Math.max(-1, HEAD_IN[r] - 1)
    for (let x = k; x <= 29 - k; x++) add(x, r)
  }
  // 앞머리 끝을 지그재그로
  for (let r = 7; r <= 9; r++) {
    for (let x = 0; x < 30; x++) {
      const p = x % 6
      const thr = [3, 1.6, 0.6][r - 7]
      if (Math.abs(p - 2.5) <= thr) add(x, r)
    }
  }
  for (let r = 7; r <= 14; r++) {
    for (const x of [0, 1, 2, 27, 28, 29]) add(x, r)
    if (r <= 12) { add(-1, r); add(30, r) }
  }
  ;[[1, 7], [1, 8], [1, 9], [1, 10], [1, 11], [1, 18], [1, 19], [1, 20], [2, 6], [2, 7], [2, 8]].forEach(([r, x]) => add(x, r, 1))
  return out
}
const DEFAULT_HAIR = blank('head')
capPixels().forEach(([x, y, t]) => { DEFAULT_HAIR[y * 40 + x] = t ? HAIR_HI : HAIR })

function drawFace (a, look) {
  const s = setter(a, 'head')
  for (const ex of [13, 24]) {
    for (let y = 22; y < 26; y++) for (let x = 0; x < 3; x++) s(ex + x + look, y, y === 25 ? '#3a4466' : OUT)
  }
  s(13 + look, 22, '#ffffff')
  s(24 + look, 22, '#ffffff')
  s(19 + look, 29, '#b55088')
  s(20 + look, 29, '#b55088')
}

/* ---------- 기본 모습 (사람마다 머리색·옷색이 다르다) ---------- */
// 아이템이 없어도 순위표에서 모두 똑같아 보이지 않게, 아이디로 머리색과 기본 옷색을 고른다.
// [주색, 밝은 결]
export const HAIR_TONES = [[HAIR, HAIR_HI], ['#181425', '#3a4466'], ['#733e39', '#b86f50'], ['#b86f50', '#e4a672']]
// [주색, 그림자]
export const SHIRT_TONES = [[SHIRT, SHIRT_D], ['#bde0fe', '#8ec5ff'], ['#c1f0e1', '#8fd9b6'],
  ['#fff3b0', '#feae34'], ['#ffd6e0', '#ffb3c7'], ['#e0c3fc', '#b8a1e3']]

function hash (text) {
  let h = 0
  for (const ch of String(text)) h = (h * 31 + ch.codePointAt(0)) >>> 0
  return h
}

// 아이디 → { hair: 번호, shirt: 번호 }. 같은 아이디는 늘 같은 모습이다.
export function toneOf (seed) {
  const h = hash(seed)
  return { hair: h % HAIR_TONES.length, shirt: Math.floor(h / HAIR_TONES.length) % SHIRT_TONES.length }
}

function recolor (arr, from, to) {
  if (from[0] === to[0] && from[1] === to[1]) return arr
  return arr.map(c => c === from[0] ? to[0] : c === from[1] ? to[1] : c)
}

/* ---------- 부위 그리기 ---------- */
// eq: { hair, hat, face, acc, top, bottom, shoes } 각 자리에 아이템(또는 없음)
// 아이템: { slot, parts: { 부위: 색 번호 배열 }, cover?(모자), kind?(신발), btype?(하의) }
function buildPart (p, eq, tone, look) {
  const { w, h } = PART[p]
  let a = BASE[p].slice()
  if (p === 'torso' || p === 'armL' || p === 'armR') a = recolor(a, SHIRT_TONES[0], SHIRT_TONES[tone.shirt])
  const put = it => {
    const px = it && it.parts && it.parts[p]
    if (!px) return
    for (let i = 0; i < px.length; i++) if (px[i]) a[i] = PAL[px[i] - 1]
  }
  if (p === 'head') {
    if (eq.face && eq.face.parts && eq.face.parts.head) {
      eq.face.parts.head.forEach((v, i) => {
        if (!v) return
        const x = i % w + look
        if (x < w) a[Math.floor(i / w) * w + x] = PAL[v - 1]
      })
    } else {
      drawFace(a, look)
    }
    const hat = eq.hat
    const cover = hat ? (hat.cover || 'top') : 'none'
    const hair = eq.hair
      ? Array.from(eq.hair.parts.head, v => v ? PAL[v - 1] : null)
      : recolor(DEFAULT_HAIR, HAIR_TONES[0], HAIR_TONES[tone.hair])
    if (cover !== 'full') {
      // 윗머리 덮기: 구역선 위의 머리 + 모자가 있는 세로줄에서 모자 아랫단보다 위의 머리를 숨긴다
      const low = new Array(w).fill(-1)
      if (cover === 'top') {
        hat.parts.head.forEach((v, i) => {
          if (!v) return
          const x = i % w
          const y = Math.floor(i / w)
          if (y > low[x]) low[x] = y
        })
      }
      hair.forEach((c, i) => {
        if (!c) return
        const x = i % w
        const y = Math.floor(i / w)
        if (cover === 'top' && (y < ZONE || y <= low[x])) return
        a[i] = c
      })
    }
    put(eq.acc)
    put(hat)
  } else if (p === 'legL' || p === 'legR') {
    const shoes = eq.shoes
    const limit = shoes && shoes.kind === 'boots' ? BOOT : FOOT
    // 신발을 신으면 기본 신발 대신 맨발 위에 신긴다
    if (shoes) {
      for (let y = FOOT; y < h; y++) {
        for (let x = 0; x < w; x++) if (a[y * w + x]) a[y * w + x] = x === w - 3 ? SKIN_D : SKIN
      }
    }
    const pants = eq.bottom && (eq.bottom.btype || 'pants') === 'pants' && eq.bottom.parts[p]
    if (pants) pants.forEach((v, i) => { if (v && Math.floor(i / w) < FOOT) a[i] = PAL[v - 1] })
    const shoe = shoes && shoes.parts[p]
    if (shoe) shoe.forEach((v, i) => { if (v && Math.floor(i / w) >= limit) a[i] = PAL[v - 1] })
  } else if (p === 'skirt') {
    if (eq.bottom && eq.bottom.btype === 'skirt') put(eq.bottom)
  } else {
    put(eq.top)
  }
  // 외곽선은 템플릿 바깥으로 1칸 넓힌 공간에서 계산한다. 끝까지 칠해도 바깥에 외곽선이 생긴다.
  const W = w + 2
  const H = h + 2
  const b = new Array(W * H).fill(null)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) b[(y + 1) * W + x + 1] = a[y * w + x]
  const out = b.slice()
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (b[y * W + x]) continue
      if ((x > 0 && b[y * W + x - 1]) || (x < W - 1 && b[y * W + x + 1]) ||
          (y > 0 && b[(y - 1) * W + x]) || (y < H - 1 && b[(y + 1) * W + x])) out[y * W + x] = OUT
    }
  }
  return out
}

/**
 * 동작 한 장을 64×64 색 배열(길이 4096, 칸마다 '#rrggbb' 또는 null)로 만든다.
 * @param {object} opts
 * @param {number} [opts.frame=0] FRAMES 번호
 * @param {object} [opts.eq={}] 입은 아이템
 * @param {string} [opts.seed=''] 기본 머리색·옷색을 고를 값(아이디)
 * @param {number} [opts.look=0] 걸을 때 얼굴이 진행 방향으로 1칸 움직인다
 */
export function composePixels ({ frame = 0, eq = {}, seed = '', look = 0 } = {}) {
  const tone = toneOf(seed)
  const px = new Array(SIZE * SIZE).fill(null)
  for (const p of ORDER) {
    const a = buildPart(p, eq, tone, look)
    const w = PART[p].w + 2
    const h = PART[p].h + 2
    const [ox, oy] = PART[p].o
    const [dx, dy] = FRAMES[frame].off[p === 'skirt' ? 'torso' : p] || [0, 0]
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const c = a[y * w + x]
        if (!c) continue
        const X = ox - 1 + dx + x
        const Y = oy - 1 + dy + y
        if (X < 0 || Y < 0 || X >= SIZE || Y >= SIZE) continue
        px[Y * SIZE + X] = c
      }
    }
  }
  return px
}

// 표에 넣는 작은 그림은 머리와 어깨만 잘라 쓴다. 전신을 작게 줄이면 얼굴이 안 보인다.
// 머리 템플릿(64×64 안 x 12~51, y 2~37)과 어깨가 들어가게 44×44 를 자른다.
export const BUST = { x: 10, y: 2, w: 44, h: 44 }
export const FULL = { x: 0, y: 0, w: SIZE, h: SIZE }

export function crop (px, rect) {
  const out = new Array(rect.w * rect.h)
  for (let y = 0; y < rect.h; y++) {
    for (let x = 0; x < rect.w; x++) out[y * rect.w + x] = px[(rect.y + y) * SIZE + rect.x + x]
  }
  return out
}
