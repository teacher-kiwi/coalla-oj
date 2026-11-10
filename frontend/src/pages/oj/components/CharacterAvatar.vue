<template>
  <canvas v-if="animated" ref="canvas" class="character" :width="rect.w" :height="rect.h"
          :style="boxStyle" role="img" :aria-label="label" />
  <img v-else class="character" :src="src" :style="boxStyle" :alt="label" />
</template>

<script setup>
// 사용자 캐릭터. 표에서는 상반신 정지 그림(bust), 프로필에서는 전신(full)이 서 있는 동작을 한다.
//
// 정지 그림은 같은 모습이면 한 번만 그려 data URL 로 다시 쓴다. 순위표 한 쪽에
// 수십 명이 나와도 실제로 그리는 횟수는 서로 다른 모습의 수만큼이다.
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { composePixels, crop, toneOf, ANIM, BUST, FULL, SIZE } from '@/utils/character'
import { lookOf } from '@/utils/looks'

const props = defineProps({
  // 아이디. 아이템이 없을 때 머리색·옷색을 고르는 데 쓴다.
  username: { type: String, default: '' },
  // 입은 아이템 { 자리: 아이템 }. 주지 않으면 아이디로 그 사람이 입은 아이템을 찾아 그린다.
  // 샵의 입어보기·관리자 미리보기처럼 정해진 모습을 그릴 때만 넘긴다.
  eq: { type: Object, default: null },
  // 화면에 보이는 한 변 길이(px)
  size: { type: Number, default: 32 },
  mode: { type: String, default: 'bust', validator: v => ['bust', 'full'].includes(v) },
  // true 면 서 있는 동작(숨쉬기)을 한다. 움직임 줄이기 설정이면 멈춘다.
  animate: { type: Boolean, default: false }
})

const wear = computed(() => props.eq || lookOf(props.username))
const rect = computed(() => props.mode === 'full' ? FULL : BUST)
const label = computed(() => props.username ? `${props.username}의 캐릭터` : '캐릭터')
const reduceMotion = typeof window !== 'undefined' && window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
const animated = computed(() => props.animate && !reduceMotion)

// 원래 크기보다 작게 줄일 때는 부드럽게, 키울 때는 도트를 살린다
const boxStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  imageRendering: props.size >= rect.value.w ? 'pixelated' : 'auto'
}))

function eqKey (eq) {
  // 고친 아이템이 옛 그림으로 남지 않게 고친 시각(v)도 열쇠에 넣는다
  return Object.keys(eq).sort().map(k => `${k}:${eq[k] ? `${eq[k].id}@${eq[k].v || ''}` : ''}`).join(',')
}

function paint (ctx, frame) {
  const r = rect.value
  const px = crop(composePixels({ frame, eq: wear.value, seed: props.username }), r)
  const img = ctx.createImageData(r.w, r.h)
  px.forEach((c, i) => {
    if (!c) return
    const k = i * 4
    img.data[k] = parseInt(c.slice(1, 3), 16)
    img.data[k + 1] = parseInt(c.slice(3, 5), 16)
    img.data[k + 2] = parseInt(c.slice(5, 7), 16)
    img.data[k + 3] = 255
  })
  ctx.putImageData(img, 0, 0)
}

const src = computed(() => {
  if (animated.value) return ''
  const t = toneOf(props.username)
  const key = `${props.mode}|${t.hair}.${t.shirt}|${eqKey(wear.value)}`
  if (!cache.has(key)) {
    const r = rect.value
    const c = document.createElement('canvas')
    c.width = r.w
    c.height = r.h
    const ctx = c.getContext('2d')
    if (!ctx) return ''
    paint(ctx, 0)
    cache.set(key, c.toDataURL())
  }
  return cache.get(key)
})

// 움직이는 그림: 서기 두 장을 번갈아 그린다
const canvas = ref(null)
let timer = null
let tick = 0
function step () {
  const ctx = canvas.value && canvas.value.getContext('2d')
  if (!ctx) return
  const frames = ANIM.idle
  ctx.clearRect(0, 0, SIZE, SIZE)
  paint(ctx, frames[tick % frames.length])
  tick += 1
}
function start () {
  stop()
  if (!animated.value) return
  step()
  timer = setInterval(step, 450)
}
function stop () {
  clearInterval(timer)
  timer = null
}
onMounted(start)
onBeforeUnmount(stop)
watch(() => [props.username, eqKey(wear.value), props.mode, animated.value], () => {
  // canvas 가 새로 생기는 경우를 위해 다음 틱에 시작
  setTimeout(start)
})
</script>

<script>
// 같은 모습은 컴포넌트끼리도 한 번만 그리도록 캐시를 모듈 단위로 둔다
const cache = new Map()
</script>

<style scoped>
.character {
  display: block;
  flex: none;
}
</style>
