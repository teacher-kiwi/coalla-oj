import { ref, onMounted, onBeforeUnmount } from 'vue'

// 창 폭이 px 이하인지. 태블릿 세로(768~1000px)에서 표의 덜 중요한 열을 숨길 때 쓴다.
// CSS 만으로는 el-table 의 열을 뺄 수 없어(폭 계산이 자바스크립트에서 이뤄진다) 열에 v-if 를 건다.
export function useMaxWidth (px) {
  const mql = typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia(`(max-width: ${px}px)`)
    : null
  const matches = ref(mql ? mql.matches : false)
  const update = (event) => { matches.value = event.matches }
  onMounted(() => mql?.addEventListener('change', update))
  onBeforeUnmount(() => mql?.removeEventListener('change', update))
  return matches
}
