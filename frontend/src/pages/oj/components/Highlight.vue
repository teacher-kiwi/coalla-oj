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
    code {
      padding: 20px;
      font-size: 1.1em;
    }
  }
</style>
