<template>
  <pre v-highlight="code"><code :class="hljsName" :style="styleObject"></code></pre>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { hljsLanguage } from '@/plugins/highlight'

const props = defineProps({
  language: { type: String, default: '' },
  code: { type: String, required: true },
  borderColor: { type: String, default: 'green' }
})

// 채점 언어 이름(C, Python3, ...)이 그대로 오므로 hljs 의 이름으로 바꿔 준다.
// 모르는 이름을 주면 hljs 가 색을 입히지 않고 콘솔에 경고만 남긴다.
const hljsName = computed(() => hljsLanguage(props.language))

const styleObject = reactive({
  'border-left': `2px solid ${props.borderColor}`
})

watch(() => props.borderColor, (newVal) => {
  styleObject['border-left'] = `2.5px solid ${newVal}`
})
</script>

<style scoped lang="less">
  pre {
    padding: 0;
    display: block;
    // hljs 가 칠하기 전(또는 모르는 언어)에도 상자 모양을 유지한다. code 는 원래 줄 안
    // 요소라, 그대로 두면 왼쪽 선과 여백이 첫 줄에만 붙었다.
    code {
      display: block;
      overflow-x: auto;
      padding: 20px;
      font-size: 1.1em;
      background: #fafafa;
      border-radius: 4px;
    }
  }
</style>
